# FragTrace — CS2 Demo Stats

Upload a CS2 `.dem` file, get back a full Leetify-style scoreboard: per-round
history, rating, KAST, ADR, headshot %, entry duels, clutches, and utility
damage — all computed directly from the replay file.

## How it works

There's no public Valve API for match stats. This tool gets real numbers the
same way Leetify and similar tools do: by parsing the demo file itself with
[awpy](https://awpy.readthedocs.io) (built on the open-source `demoparser2`
Rust parser).

```
backend/   FastAPI server. POST a .dem file, get back JSON stats.
frontend/  React (Vite) UI: upload screen + scoreboard.
```

## Running it

### 1. Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Check it's alive: `curl http://localhost:8000/api/health`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the URL it prints (usually `http://localhost:5173`).

By default the frontend calls the backend at `http://localhost:8000`. To
point it elsewhere (e.g. once deployed), set `VITE_API_BASE` in a `.env`
file inside `frontend/`:

```
VITE_API_BASE=https://your-backend-domain.com
```

## Getting a demo file to test with

- In-game: **Watch → Your Matches**, download a recent match, the `.dem`
  file lands in your CS2 `csgo` folder.
- FACEIT/ESEA matches: download from the match room, then upload here
  directly (you don't need to put it back in your CS2 folder for this tool).

## Deploying it for real

This project deploys as two separate services:

- **Backend → [Render](https://render.com)** (free, no credit card)
- **Frontend → [Vercel](https://vercel.com)** (free, no credit card)

### Step 1 — Push this to GitHub

```bash
cd cs2stats
git init
git add .
git commit -m "Initial commit"
gh repo create fragtrace --public --source=. --push
```
(No `gh` CLI? Create an empty repo on github.com instead, then:)
```bash
git remote add origin https://github.com/YOUR_USERNAME/fragtrace.git
git branch -M main
git push -u origin main
```

### Step 2 — Deploy the backend on Render

1. Go to [render.com](https://render.com) → sign up with GitHub.
2. **New +** → **Web Service** → pick your `fragtrace` repo.
3. Set:
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free
4. Click **Create Web Service**. First deploy takes a few minutes (it's
   installing `awpy`, which is a sizeable package).
5. Once it's live, copy the URL Render gives you — something like
   `https://fragtrace-backend.onrender.com`.

Render's free tier spins your service down after 15 minutes with no
traffic, so the first request after a quiet period takes 30-60 seconds to
wake up. That's normal — it'll speed back up after that.

### Step 3 — Deploy the frontend on Vercel

1. Go to [vercel.com](https://vercel.com) → sign up with GitHub.
2. **Add New** → **Project** → pick the same `fragtrace` repo.
3. Set:
   - **Root Directory**: `frontend`
   - Framework Preset: Vite (should auto-detect)
4. Under **Environment Variables**, add:
   - `VITE_API_BASE` = the Render URL from Step 2 (no trailing slash)
5. Click **Deploy**. You'll get a URL like `fragtrace.vercel.app`.

### Step 4 — Connect the two

Go back to Render → your backend service → **Environment** → add:
- `FRONTEND_ORIGIN` = your Vercel URL (e.g. `https://fragtrace.vercel.app`)

This tells the backend to accept requests from your live frontend (it
already allows `localhost` for local dev — see `main.py`). Render
redeploys automatically when you save an env var.

That's it — visit your Vercel URL and upload a demo.

### Updating the live site later

Just push to your `main` branch on GitHub — both Render and Vercel watch
the repo and redeploy automatically.



- **Rating, KAST, ADR** come straight from `awpy`'s built-in stat functions
  — these mirror HLTV's published methodology closely.
- **Clutch detection** is a v1 heuristic: it reconstructs who was alive in a
  round from the kill log alone (not full per-tick health data), so it can
  occasionally miss or misattribute a clutch in unusual rounds (e.g. a
  player who neither kills nor dies that round). Good enough to highlight
  clutch performances, not pixel-perfect.
- **Team labels** (T/CT) reflect whichever side a player played *more often*
  across the whole demo, since sides swap at halftime — so the table groups
  by "primary side," not a fixed team name.
- **Enemies-flashed** isn't included yet — it needs per-tick visibility
  calculation that the engine doesn't compute in v1. Flash *assists* (kills
  that followed your flash) are tracked and accurate.

## Extending this

The most natural next steps, in rough order of effort:
1. **Per-player pages** — click a name in the scoreboard, see their full
   round-by-round log, weapon breakdown, positioning.
2. **Persistent match history** — store parsed results (e.g. in a database)
   so people can revisit old uploads instead of re-uploading each time.
3. **Steam OpenID login** — if you want a "connect your account" flow like
   Leetify's, the demo itself still has to be supplied (uploaded, or fetched
   via a bot account through Valve's Game Coordinator) — there's no
   shortcut around that.
4. **Tick-accurate clutch/trade detection** — swap the kill-log heuristic
   for a full per-tick alive-state walk using `demo.ticks`.
