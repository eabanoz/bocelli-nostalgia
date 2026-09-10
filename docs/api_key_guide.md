# Getting a YouTube Data API v3 key

Free. No billing card. 10 minutes. 10,000 quota units per day.

## Steps

1. **Create a project.** Go to <https://console.cloud.google.com>, sign in with any
   Google account. Project dropdown (top bar) → **New Project** → name it
   `nextup-yt` → **Create**. Make sure it is selected afterwards.

2. **Enable the API.** Left menu → **APIs & Services → Library**. Search
   *YouTube Data API v3* → click the result → **Enable**.
   *(Enabling can take 1–2 minutes to propagate. A `403 accessNotConfigured`
   right after enabling usually just means "wait".)*

3. **Create the key.** **APIs & Services → Credentials** →
   **+ Create Credentials → API key**. Copy it.

4. **Restrict it** (recommended). **Edit API key** → *API restrictions* →
   **Restrict key** → tick only *YouTube Data API v3* → **Save**. A leaked
   restricted key can do nothing else.

## You do NOT need OAuth

OAuth is only for *private* data — your own uploads, your subscriptions, posting
comments. Reading public videos and public comments needs a plain API key.
If a tutorial tells you to download `client_secret.json`, it is solving a
different problem.

## Storing the key in Colab

Never paste the key into a cell — it gets saved into the .ipynb and pushed to
GitHub.

1. Click the **🔑 key icon** in the Colab left sidebar
2. **+ Add new secret**
3. Name: `YOUTUBE_API_KEY` · Value: your key
4. Toggle **Notebook access** on

Then:

```python
from google.colab import userdata
API_KEY = userdata.get("YOUTUBE_API_KEY")
```

Add a second secret `HASH_SALT` (any 32 random hex characters) for notebook 02.

## Quota

| Endpoint | Units | Returns |
|---|---|---|
| `search.list` | **100** | ≤50 videos (same cost for 1 or 50 — always request 50) |
| `videos.list` | 1 | ≤50 videos, full statistics |
| `channels.list` | 1 | ≤50 channels |
| `commentThreads.list` | 1 | 100 comments |

10,000 units = 100 searches, **or** a million comments. Resets at **midnight
Pacific Time**.

Need more? Create additional Cloud projects (each gets its own 10,000), or apply
for a quota extension — the latter takes weeks and needs a described use case.

## Errors

| Error | Meaning | Fix |
|---|---|---|
| `403 accessNotConfigured` | API not enabled on this project | Enable it, wait 2 min |
| `403 quotaExceeded` | Daily budget spent | Wait for midnight PT, or new project |
| `400 API key not valid` | Wrong key or wrong restriction | Check Credentials page |
| `403 commentsDisabled` | Uploader turned comments off | Normal — skip, don't retry |
| `404 videoNotFound` | Deleted or private since collection | Normal — skip |
