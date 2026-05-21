# Deploying to Vercel

Steps to deploy this Flask app on Vercel:

- Push your repository to GitHub (or connect your Git provider).
- In the Vercel dashboard click **New Project** → Import Git Repository.
- For Project Settings leave the Root Directory empty (project root).
- Vercel will use the `vercel.json` file to build: it routes all requests to `campus_lf/app.py` which exports the Flask `app` WSGI object.
- Ensure environment variables are set in Vercel: at minimum set `SECRET_KEY` (don't use the default in code) and set `DATABASE_URL` or `SQLALCHEMY_DATABASE_URI` to a Postgres connection string from Supabase or another external database provider.

Notes & caveats:
- This project currently uses SQLite (`campus_lf.db`) by default. SQLite is not persistent on Vercel serverless instances — use an external DB such as Supabase Postgres or Vercel Postgres for production.
- The app now reads `DATABASE_URL` first, then `SQLALCHEMY_DATABASE_URI`, so Vercel can securely configure the database connection string.
- If you use Supabase, copy the Postgres connection string from the project's Settings → Database → Connection string.
- Large packages like `ultralytics` and `opencv-python` may exceed Vercel serverless size limits. If your deployment fails with size errors, consider one of:
  - Removing heavy deps or lazy-loading them only where needed.
  - Building a Docker image and deploying to a platform that supports containers (e.g., Vercel with a custom builder, Render, or Railway).

Troubleshooting:
- If Vercel fails to install dependencies, check the build logs for which package caused the issue.
- To test locally, create a virtualenv and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python campus_lf/app.py
```

If you want, I can:
- Push these Vercel-ready files to your Git remote and trigger a Vercel import (requires push access).
- Help you set up an external database such as Vercel Postgres.
