# NEK CHECKER — Vercel + GitHub ready

Animated multi-platform checker dashboard by **@samvir1**.

## What’s inside

- `public/` — Home + Checkers matrix + Run panel (full CSS animations)
- `api/` — Python serverless endpoints (`health`, `checkers`, `check`)
- `checkers_ext/` — full checker modules
- `vercel.json` + `requirements.txt`

## Deploy on Vercel

1. Push this folder to a GitHub repo
2. Vercel → **Add New Project** → import that repo
3. Framework: Other · Root: project root
4. Deploy

Or CLI:

```bash
npm i -g vercel
cd vercel_checker
vercel
```

## Local test

```bash
# option A — Vercel dev
vercel dev

# option B — simple static + note APIs need vercel/python runtime
python -m http.server 8080 --directory public
```

## GitHub push (your account)

```bash
cd vercel_checker
git init
git add .
git commit -m "NEK CHECKER vercel site"
git branch -M main
git remote add origin https://github.com/<YOUR_USER>/<YOUR_REPO>.git
git push -u origin main
```

Then connect the repo in Vercel dashboard.

## Notes

- Serverless `POST /api/check` batches up to 5 combos per request (timeout-safe).
- Heavy multi-thousand combo jobs → use `FULL_CHECKERS_ALL_IN_ONE.py` on Termux/VPS.
- Proxies optional; paste in Run panel.

by @samvir1
