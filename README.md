# GraceLife London sermon archive

A rate-limited, static Markdown archive for the 20 most recent **sermon videos** on [GraceLife London](https://www.youtube.com/channel/UCxTu88in5i5NsZzX-w-z0qQ). Metadata and transcript records live in Turso SQLite; the static build exports them to HTML.

> **Status:** the repository is a reproducible pipeline and catalog. Run the worker to download audio and transcribe locally/under your own rights. It never claims that an unreviewed transcript is a theological endorsement.

## Quick start

```bash
# Python 3.11+
python scripts/collect.py --limit 20
python scripts/build.py
python -m http.server 8000 -d dist
```

Punctuation restoration uses `fullstop-punctuation-multilang-large` when Whisper output lacks sentence punctuation; it is optional at runtime and falls back safely if unavailable.

Install transcription support (`faster-whisper` is preferred over the original Whisper CLI for lower memory use):

```bash
uv pip install -r requirements.txt
python scripts/worker.py --limit 1
```

Set `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` to persist records in Turso. Without them, `data/sermons.sqlite3` is used locally. Audio is stored in `var/audio/` and ignored by git.

## Queue and worker operation

The `transcription_queue` table in `db/schema.sql` is durable job state: `pending`, `downloaded`, `processing`, `completed`, or `failed`, with attempts, locks, and a six-hour retry delay. One worker claims one job transactionally, downloads at most one item at a time, and sleeps between YouTube requests. Use:

```bash
python scripts/job_queue.py enqueue --limit 20
python scripts/job_queue.py show
python scripts/worker.py --limit 1 --download-only  # optional staged audio download
python scripts/worker.py --limit 1                 # transcribe the next queued item
```

For Turso persistence, set `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN`; `scripts/turso_sync.py` uploads both sermon records and queue state, while `--pull` restores the durable queue before a fresh worker starts. The GitHub worker pulls before collection and syncs after each run. No Turso credentials are exposed in the static site.

## Safe YouTube access

The collector uses `yt-dlp` for channel metadata and falls back to the channel RSS feed when YouTube serves a consent/lockup response. It asks for at most 20 entries, sleeps between requests, uses one worker, and never loops aggressively. The scheduled worker runs every six hours and processes at most one new sermon per run. Respect YouTube's terms, copyright, and the church's permission before publishing full transcripts.

Classification is conservative: `is_sermon_video()` excludes obvious shorts, announcements, music, livestreams, and podcasts, and requires sermon-like title/description signals or a Scripture reference. Review `data/sermons.json` before transcription.

## LLM summaries

Summaries are generated only from completed transcripts by `scripts/summarize.py`. Biblical strengths and weaknesses are generated separately by `scripts/review.py` with an explicit orthodox-theology rubric. OpenRouter is supported by setting `OPENROUTER_API_KEY` (and optionally `OPENROUTER_MODEL`, default `openai/gpt-4o-mini`); the prompt excludes greetings and requires the biblical text, central claim, and application in two sentences. The GitHub worker runs it only when the secret is configured.

## Biblical review

Every generated transcript includes **Strengths** and **Weaknesses / questions for review** sections. These are intentionally marked pending until a Christian reviewer checks the transcript and the sermon against Scripture. The rubric asks whether the sermon handles its context faithfully, explains the gospel (God's holiness, human sin, Christ's incarnation/atonement/resurrection, repentance and faith), distinguishes commands from applications, and avoids speculative claims. It does not score denominational distinctives.

## Free hosting

GitHub Pages is the simplest free host for this static output (public repository on GitHub Free). The included Actions workflow builds `dist/` and deploys it. In repository Settings → Pages choose **GitHub Actions**. The workflow publishes at `https://OWNER.github.io/REPOSITORY/`. Cloudflare Pages is a good free alternative, especially for a private source repository.

## Containers
The periodic fetcher is `scripts/fetcher.py`; it safely refreshes the channel catalog, enqueues new sermon jobs, and pushes queue/metadata state to Turso. Run it continuously with a six-hour interval:

```bash
docker compose --profile worker up fetcher
# or run one cycle
python scripts/fetcher.py --once --limit 20
```


The static site and processing pipeline are separated. `Dockerfile.worker` contains ffmpeg, yt-dlp, faster-whisper, punctuation restoration, Turso sync, and the queue worker. `Dockerfile.site` produces deploy-ready static HTML and serves it with nginx; it does not run an SSR server.

```bash
# Build and serve static pages at http://localhost:4173
docker compose build site
docker compose up site

# Run one queued download/transcription job with .env credentials
docker compose --profile worker run --rm worker

# Rebuild static pages after worker updates data/content
docker compose build site && docker compose up site
```

Mount `./data`, `./content`, and `./var` keep queue/transcript state outside the worker container. For production, deploy `dist/` directly to GitHub Pages/Cloudflare Pages, or deploy the `site` image to any container host.

## Turso

Create a database, then apply `db/schema.sql` with `turso db shell`. Add the URL/token as GitHub Actions secrets if you want the scheduled worker to persist remotely. The Pages build exports the latest records to static pages; no database credentials are shipped to browsers.
