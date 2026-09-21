# Nostalgia on YouTube

**A computational social science tutorial**
University of Trento — Department of Sociology and Social Research

YouTube Data API v3 · Google Colab · RoBERTa / mDeBERTa · Hugging Face

---

## What this is

Three notebooks that take you from *"I have no API key"* to a multilingual,
theory-driven analysis of how people talk about the past in the comments of a
single video: Andrea Bocelli's **Con Te Partirò / Time To Say Goodbye**,
performed in 1997 and uploaded to YouTube in 2015.

Everything runs in Colab. Click a badge and go — the notebooks clone this repo
themselves and the data is already here, so **you do not need an API key to
follow along.**

| # | Notebook | API key | GPU | Runtime | |
|---|---|---|---|---|---|
| 01 | Channel performance | yes* | no | ~10 min | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eabanoz/bocelli-nostalgia/blob/main/notebooks/01_channel_performance.ipynb) |
| 02 | Harvest & prepare | optional | no | ~5 min | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eabanoz/bocelli-nostalgia/blob/main/notebooks/02_harvest_and_prepare.ipynb) |
| 03 | Nostalgia analysis | no | **no** | ~15 min | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eabanoz/bocelli-nostalgia/blob/main/notebooks/03_nostalgia_analysis.ipynb) |

\* Notebook 01 collects live data. Notebooks 02 and 03 have switches
(`HARVEST`, `SCORE`) that load the committed datasets instead.

---

## The research design

The video is an **archival re-release**, and that is the analytic centre
rather than a footnote. Every comment carries three timestamps:

1. **Performance** — 1997, fixed
2. **Upload** — October 2015, fixed
3. **Comment** — 2015 to now, and it varies

Nostalgia is a claim about distance from a past. Here that distance is
measurable for every utterance.

### Constructs

From Boym's *The Future of Nostalgia* (2001):

| Construct | Definition |
|---|---|
| Personal memory | Autobiographical recall, usually family |
| Mortality / grief | Remembrance of the dead; funerals, memorials |
| Restorative | The past was better; a wish to return |
| Reflective | Bittersweet longing without a wish to restore |
| Collective | Shared generational or national memory |
| Anemoia | Longing for a time never personally lived |

---

## What's in the data

| File | Rows | Contents |
|---|---|---|
| `data/processed/channel_videos.csv` | 596 | Full channel census with derived features |
| `data/processed/channel_info.csv` | 1 | Channel-level metadata |
| `data/processed/comments_clean.csv` | 21,469 | Pseudonymised, language-tagged, three temporal clocks |
| `data/processed/comments_scored.csv` | 8,391 | Analysis set with dictionary and zero-shot scores |

`data/raw/` is **gitignored**: it holds `author_channel_id`, which is personal
data under GDPR. Pseudonymisation happens before anything leaves that folder.

---

## Findings worth teaching

**The API's own metadata disagrees with itself.** `statistics.videoCount`
reports 284 videos; the uploads playlist enumerates 596. The playlist is
correct.

**The audience is not who you would guess.** English and Portuguese are
co-dominant at roughly 35% each. Italian — the language of the song — is 8.5%.

**Language shares depend on your filter.** Which language "leads" moves by ten
percentage points across entirely reasonable threshold choices. Notebook 02
reports the full sensitivity table rather than a point estimate.

**Dictionaries are biased toward the languages their author reads.** The first
probe list returned *zero* personal-memory hits across 3,585 Portuguese
comments. Not rarity — absence of Portuguese words in the list. Russian is
still deliberately unfixed as an exercise.

**Not everything in a comment field is a comment.** About 21% of Italian
comments are the song's lyrics, pasted repeatedly. Since the song is about
departure, an NLI classifier reads them as grief — correctly. Leaving them in
produces a large, plausible, entirely artefactual finding that Italian
listeners are far more nostalgic than everyone else. Notebook 03 filters them.

**NLI scores are not probabilities.** The model assigns near-certainty to most
inputs, so absolute thresholds are meaningless. The *ranking* is sound
(AUC ≈ 0.91), so we flag top deciles instead.

**Sentiment is orthogonal to nostalgia.** Comments about dead parents classify
as *positive* — they are affectionate in tone. Choosing the familiar tool
would have measured the wrong construct.

---

## Repository layout

```
├── notebooks/          the three tutorial notebooks
├── src/
│   └── channel_client.py    API wrapper with quota accounting
├── data/
│   ├── processed/      committed datasets — notebooks load these
│   └── raw/            gitignored (contains author identifiers)
├── docs/
│   ├── api_key_guide.md
│   └── ethics_gdpr.md
└── outputs/figures/
```

---

## Getting an API key

Free, no billing card, 10,000 units per day. See
[`docs/api_key_guide.md`](docs/api_key_guide.md).

Store it as a **Colab secret** named `YOUTUBE_API_KEY` (key icon in the left
sidebar) — never typed into a cell, because anything in a cell is saved into
the `.ipynb` and pushed here.

### Quota, the one fact that governs everything

| Endpoint | Units | Returns |
|---|---|---|
| `search.list` | **100** | ≤50 results — same cost for 1 or 50 |
| `videos.list` | 1 | ≤50 videos with full statistics |
| `channels.list` | 1 | ≤50 channels |
| `playlistItems.list` | 1 | 50 playlist entries |
| `commentThreads.list` | 1 | 100 comments |

10,000 units = 100 searches **or** a million comments. Enumerating this entire
channel cost under 100 units, because it never touches `search.list`.

Quota resets at **midnight Pacific Time**.

---

## Limitations

- **Not a sample of any population.** No age, gender or location is observed
  for any commenter. Findings describe discourse on one video.
- **Unvalidated.** The zero-shot model has never seen a labelled example of
  "reflective nostalgia". These are hypothesis-generating numbers; a published
  study would hand-code a stratified sample and report Cohen's κ.
- **`restorative` fails its AUC check** (below 0.5) and should not be reported.
- **Length drives entailment scores**, so groups that write longer comments
  look more nostalgic. Report stratified by length.
- **70.3% retrieval.** The API caps pagination below the displayed comment
  count; this is a large sample, not a census.

## Ethics

Comments are pseudonymised with a salted hash before analysis; the salt is not
in this repo. See [`docs/ethics_gdpr.md`](docs/ethics_gdpr.md) before reusing
the data or publishing anything derived from it.

## Citation

Please cite this repository and, for the models used, the FEEL-IT paper
(Bianchi, Nozza & Hovy, WASSA 2021) and Laurer et al. for mDeBERTa-XNLI.

## License

Code: MIT. Data collected via the YouTube Data API remains subject to
YouTube's Terms of Service and is not redistributable as raw dumps.
