# AI Health Scanner deployment notes

## Services

- Frontend: https://ai-health-scanner-web.onrender.com
- Primary API used by the frontend: https://ai-health-backend-g329.onrender.com
- API health endpoint: https://ai-health-backend-g329.onrender.com/health
- API docs: https://ai-health-backend-g329.onrender.com/docs

The Render static site publishes only `index.html`, `script.js`, and `style.css` from the repository root. It does not publish the backend source tree.

## Required backend environment

Configure these in Render for every backend service running `backend/main.py`:

- `SECRET_KEY`: a unique, random, high-entropy secret. Never commit it to Git.
- `ALLOWED_ORIGINS`: comma-separated exact origins allowed to call the API from a browser.
- `DATABASE_URL`: recommended for persistent PostgreSQL storage. Without it, the app falls back to SQLite at `backend/users.db`; on ephemeral hosting that file may not survive a replacement/redeploy.
- `OPENAI_API_KEY`: optional; without it, the chatbot uses its safe local fallback.
- `OPENAI_MODEL`: optional; defaults to `gpt-4o-mini`.

Never place credentials in this file, frontend JavaScript, or any public repository file.

## API smoke tests

After a deploy, check:

1. `GET /health` returns HTTP 200.
2. `POST /register` accepts a valid email and password (at least 8 characters).
3. `POST /login` returns an access token.
4. Authenticated `GET /profile` returns the current account.
5. Authenticated `POST /predict-simple`, `POST /heart-risk`, and `POST /diabetes-risk` return a bounded screening score.
6. Authenticated `GET /history` contains saved results.

The automated backend regression suite runs in GitHub Actions on pushes to `main` and pull requests.

## Clinical limitation

Outputs are screening estimates for educational purposes, not a diagnosis or a substitute for professional medical care. Do not use the model as the sole basis for treatment decisions.
