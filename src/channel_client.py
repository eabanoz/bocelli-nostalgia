"""
Single-channel enumeration for the YouTube Data API v3.

Different cost profile from search-based collection. Enumerating an entire
channel never touches search.list:

    channels.list        1 unit   -> uploads playlist ID
    playlistItems.list   1 unit   -> 50 video IDs
    videos.list          1 unit   -> 50 videos' full statistics

A 2,000-video channel costs roughly 80 units of the daily 10,000. Channel
size is effectively not a constraint, which is why we can afford a full
census rather than a sample.
"""

from __future__ import annotations

import re
import time

import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

QUOTA_COSTS = {
    "channels.list": 1,
    "playlistItems.list": 1,
    "videos.list": 1,
    "commentThreads.list": 1,
    "search.list": 100,
}
DAILY_QUOTA = 10_000

# ISO-8601 duration, e.g. PT1H2M3S. The time part is optional because
# YouTube returns "P0D" for live and upcoming broadcasts.
ISO_DUR = re.compile(
    r"^P(?:(?P<d>\d+)D)?"
    r"(?:T(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?)?$")


def parse_duration(iso: str) -> float:
    """ISO-8601 duration -> seconds. NaN on anything unparseable.

    Live and upcoming streams report "P0D", which parses to 0. That is not
    the same as a 0-second video, so callers should filter on
    `live_status` rather than trusting duration alone.
    """
    if not isinstance(iso, str):
        return float("nan")
    m = ISO_DUR.match(iso.strip())
    if not m:
        return float("nan")
    p = {k: int(v) if v else 0 for k, v in m.groupdict().items()}
    return p["d"] * 86400 + p["h"] * 3600 + p["m"] * 60 + p["s"]


class ChannelCollector:
    def __init__(self, api_key: str, verbose: bool = True):
        self.yt = build("youtube", "v3", developerKey=api_key,
                        cache_discovery=False)
        self.spent = 0
        self.verbose = verbose
        self.errors: list[dict] = []

    # -- internals ---------------------------------------------------------

    def _say(self, m: str) -> None:
        if self.verbose:
            print(m)

    def _exec(self, req, endpoint: str):
        try:
            r = req.execute()
            self.spent += QUOTA_COSTS[endpoint]
            return r
        except HttpError as e:
            try:
                reason = e.error_details[0].get("reason", "")
            except Exception:
                reason = str(getattr(e, "status_code", "unknown"))
            self.errors.append({"endpoint": endpoint, "reason": reason})
            if reason in ("quotaExceeded", "dailyLimitExceeded"):
                raise RuntimeError(
                    "QUOTA EXHAUSTED — resets at midnight Pacific Time."
                ) from e
            self._say(f"   ! skipped ({reason})")
            return None

    def quota_report(self) -> str:
        return (f"Quota: {self.spent:,} / {DAILY_QUOTA:,} units "
                f"({100 * self.spent / DAILY_QUOTA:.1f}%)")

    # -- channel -----------------------------------------------------------

    def channel_info(self, channel_id: str) -> dict:
        """Metadata, statistics, and the uploads playlist ID. 1 unit.

        Always run this before anything else: it confirms the channel ID is
        the one you think it is. Channel IDs copied from third-party sites
        are wrong more often than you would expect.
        """
        r = self._exec(
            self.yt.channels().list(
                part="snippet,statistics,contentDetails,brandingSettings",
                id=channel_id),
            "channels.list")
        if not r or not r.get("items"):
            raise ValueError(
                f"No channel found for id={channel_id!r}. Check the ID: it "
                "should start with 'UC' and be 24 characters.")
        it = r["items"][0]
        st = it.get("statistics", {})
        return {
            "channel_id": it["id"],
            "title": it["snippet"]["title"],
            "description": it["snippet"].get("description", ""),
            "custom_url": it["snippet"].get("customUrl", ""),
            "published_at": it["snippet"]["publishedAt"],
            "country": it["snippet"].get("country", ""),
            "subscribers": int(st.get("subscriberCount", 0) or 0),
            "total_views": int(st.get("viewCount", 0) or 0),
            "video_count": int(st.get("videoCount", 0) or 0),
            "hidden_subs": st.get("hiddenSubscriberCount", False),
            "uploads_playlist": (it["contentDetails"]["relatedPlaylists"]
                                 ["uploads"]),
        }

    def list_uploads(self, uploads_playlist: str,
                     max_videos: int | None = None) -> pd.DataFrame:
        """Every video in the uploads playlist. 1 unit per 50 videos.

        Note this returns *public* uploads only. It will not match
        statistics.videoCount exactly if the channel has unlisted or
        members-only content — a discrepancy worth reporting, not hiding.
        """
        rows, token, page = [], None, 0
        while True:
            params = dict(part="snippet,contentDetails",
                          playlistId=uploads_playlist, maxResults=50)
            if token:
                params["pageToken"] = token
            r = self._exec(self.yt.playlistItems().list(**params),
                           "playlistItems.list")
            if not r:
                break
            for it in r.get("items", []):
                sn = it["snippet"]
                rows.append({
                    "video_id": it["contentDetails"]["videoId"],
                    "title": sn.get("title", ""),
                    "description": sn.get("description", ""),
                    "published_at": (it["contentDetails"]
                                     .get("videoPublishedAt")
                                     or sn.get("publishedAt")),
                    "position": sn.get("position"),
                })
            page += 1
            if page % 5 == 0:
                self._say(f"   {len(rows):,} videos listed...")
            if max_videos and len(rows) >= max_videos:
                rows = rows[:max_videos]
                break
            token = r.get("nextPageToken")
            if not token:
                break
            time.sleep(0.03)
        self._say(f"   {len(rows):,} videos total | {self.quota_report()}")
        return pd.DataFrame(rows)

    def video_stats(self, video_ids: list[str]) -> pd.DataFrame:
        """Statistics + duration + tags. 1 unit per 50 videos.

        Deleted or private videos silently drop out of the response, so the
        returned frame can be shorter than the input list.
        """
        rows = []
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i:i + 50]
            r = self._exec(
                self.yt.videos().list(
                    part="snippet,statistics,contentDetails,status",
                    id=",".join(chunk), maxResults=50),
                "videos.list")
            if not r:
                continue
            for it in r.get("items", []):
                sn, st = it["snippet"], it.get("statistics", {})
                cd = it.get("contentDetails", {})
                rows.append({
                    "video_id": it["id"],
                    "view_count": int(st.get("viewCount", 0) or 0),
                    "like_count": int(st.get("likeCount", 0) or 0),
                    "comment_count": int(st.get("commentCount", 0) or 0),
                    # commentCount absent == comments disabled, which is
                    # different from zero comments. Preserve the distinction.
                    "comments_disabled": "commentCount" not in st,
                    "duration_iso": cd.get("duration"),
                    "duration_sec": parse_duration(cd.get("duration")),
                    "definition": cd.get("definition"),
                    "caption": cd.get("caption"),
                    "licensed": cd.get("licensedContent"),
                    "tags": "|".join(sn.get("tags", []) or []),
                    "category_id": sn.get("categoryId"),
                    "audio_language": (sn.get("defaultAudioLanguage")
                                       or sn.get("defaultLanguage")),
                    "live_status": sn.get("liveBroadcastContent"),
                })
            if (i // 50) % 10 == 0 and i:
                self._say(f"   {i:,} enriched...")
        return pd.DataFrame(rows)

    # -- comments ----------------------------------------------------------

    def comments(self, video_id: str, max_pages: int = 200,
                 order: str = "relevance",
                 include_replies: bool = True) -> pd.DataFrame:
        """Harvest comments from one video. 1 unit per 100 top-level threads.

        The API caps pagination well below the displayed comment count on
        very large videos, so treat the result as a large sample rather than
        a census, and say so.
        """
        rows, token, page = [], None, 0
        while page < max_pages:
            params = dict(
                part="snippet,replies" if include_replies else "snippet",
                videoId=video_id, maxResults=100,
                textFormat="plainText", order=order)
            if token:
                params["pageToken"] = token
            r = self._exec(self.yt.commentThreads().list(**params),
                           "commentThreads.list")
            if not r:
                break
            for it in r.get("items", []):
                top = it["snippet"]["topLevelComment"]
                sn = top["snippet"]
                rows.append({
                    "comment_id": top["id"],
                    "video_id": video_id,
                    "text": sn.get("textOriginal", ""),
                    "author_channel_id": (sn.get("authorChannelId", {})
                                          .get("value", "")),
                    "like_count": int(sn.get("likeCount", 0) or 0),
                    "published_at": sn.get("publishedAt"),
                    "updated_at": sn.get("updatedAt"),
                    "reply_count": int(it["snippet"]
                                       .get("totalReplyCount", 0)),
                    "is_reply": False,
                    "parent_id": "",
                })
                if include_replies:
                    for rp in it.get("replies", {}).get("comments", []):
                        rs = rp["snippet"]
                        rows.append({
                            "comment_id": rp["id"],
                            "video_id": video_id,
                            "text": rs.get("textOriginal", ""),
                            "author_channel_id": (rs.get("authorChannelId", {})
                                                  .get("value", "")),
                            "like_count": int(rs.get("likeCount", 0) or 0),
                            "published_at": rs.get("publishedAt"),
                            "updated_at": rs.get("updatedAt"),
                            "reply_count": 0,
                            "is_reply": True,
                            "parent_id": top["id"],
                        })
            page += 1
            if page % 20 == 0:
                self._say(f"   {len(rows):,} comments | {self.quota_report()}")
            token = r.get("nextPageToken")
            if not token:
                break
            time.sleep(0.03)
        return pd.DataFrame(rows)
