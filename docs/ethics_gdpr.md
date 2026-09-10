# Ethics, GDPR and what you may put on GitHub

Read this before the first `git push`. A public repository is a **publication**,
not a backup, and that distinction carries legal weight for this kind of data.

---

## 1. YouTube comments are personal data

"Publicly available" is not a GDPR category. A comment is personal data because it
is linked to an `authorChannelId` that identifies a natural person, and often
contains further identifying content ("sono una ragazza madre di 27 anni, vivo in
Calabria"). Under GDPR the relevant questions are:

- **Lawful basis.** For academic work this is normally Art. 6(1)(e) public interest
  or 6(1)(f) legitimate interests, combined with the Art. 89 research derogations.
  Your university has a template — use it, do not improvise.
- **Data minimisation** (Art. 5). Collect only what the research question needs.
  We drop display names and profile images at the first opportunity because they
  add nothing to a sentiment analysis and multiply the risk.
- **Special categories** (Art. 9). Comments about health, ethnicity, political
  opinion or sexuality attract stricter protection. Our intersectionality flags
  deliberately surface exactly this kind of content — handle the flagged subset
  with more care, not less.

**Consult the University of Trento ethics committee** before any collection that
goes beyond classroom demonstration. NEXT-UP is Horizon-funded, so this also feeds
your Data Management Plan obligations.

---

## 2. What this repo does about it

| Layer | Measure |
|---|---|
| `data/raw/` | **gitignored** — this is the only place `author_channel_id` exists |
| Notebook 02 | salted SHA-256 pseudonymisation; display names dropped entirely |
| Salt | stored as a Colab secret, never committed |
| `data/processed/` | pseudonymised, but still contains verbatim comment text |

### Why the salt matters

An unsalted SHA-256 of a channel ID is **not** pseudonymisation. Channel IDs come
from a known, enumerable space; anyone with the same hash function can build a
rainbow table and invert your "anonymised" identifiers in an afternoon. The salt
is the entire security property. Keep it out of the repo, and keep it *stable*
across runs or your pseudonyms stop being linkable.

---

## 3. The decision you have to make: verbatim text

`data/processed/` is pseudonymised but contains full comment text. Publishing it
means a comment written by an identifiable young person about their unemployment,
their family's finances or their mental health becomes permanently searchable,
attached to your institution's name, outside the platform where they chose to
post it.

**Three defensible options:**

1. **Commit nothing.** Ship only `data/sample/` (synthetic) and the code. Students
   collect their own. Safest; least convenient.
2. **Commit aggregates only.** Model scores, counts, features — no `text` column.
   Reproducible analysis, no republication. *Recommended default.*
3. **Commit full text.** Only with an ethics approval that explicitly covers
   republication, and a documented takedown route.

To drop text before committing:

```python
df.drop(columns=["text", "text_clean"]).to_csv(
    "data/processed/comments_features_only.csv", index=False)
```

---

## 4. YouTube Terms of Service

Separate from GDPR, and easy to forget. The API Services Terms restrict storing
and redistributing API data. Two consequences that bite in practice:

- **Do not redistribute raw comment dumps**, including on GitHub — irrespective of
  the privacy question above.
- **Refresh or delete stored data periodically.** If a user deletes their comment,
  your copy should not outlive it indefinitely.

Sharing *derived* data — model scores, aggregate counts, coded categories — is the
normal academic workaround and is what option 2 above implements.

---

## 5. In publications

- **Never quote a comment verbatim.** A verbatim string is searchable and leads
  straight back to the author. Paraphrase, or translate-and-paraphrase.
- Report the pseudonymisation method and that the salt is not shared.
- Report attrition: how many comments were collected, filtered, and why.
- Report Cohen's κ from notebook 04 next to every model-derived figure.
- State clearly that the corpus is not a sample of any population.

---

## 6. Pre-push checklist

```bash
# 1. Any API keys?
grep -rE "AIza[0-9A-Za-z_-]{35}" . --exclude-dir=.git

# 2. Any raw data staged?
git status --short | grep "data/raw" && echo "STOP — raw data staged"

# 3. Any author identifiers in processed files?
head -1 data/processed/*.csv | grep -i "author_channel_id" && echo "STOP"

# 4. Clear notebook outputs if they display comment text
jupyter nbconvert --clear-output --inplace notebooks/*.ipynb
```

If a key does get committed: revoking it in the Google Cloud console is necessary
and sufficient — rewriting git history is not enough on its own, because the key
may already have been scraped. Revoke first, then clean history.
