# Personal Expense Tracker

A small per-user expense tracker:

- **backend/** - FastAPI + SQLAlchemy REST API (email/password + Google auth, expense CRUD, monthly summary)
- **frontend/** - React (Vite) single-page app
- **mcp-server/** - an MCP server that exposes the same expense operations as tools, so an AI agent (e.g. Claude Desktop) can manage a user's expenses on their behalf
- **Database** - PostgreSQL hosted on [Neon](https://neon.tech) (free tier, doesn't expire like Render's own free Postgres)

Every expense endpoint requires a valid login token and only ever reads/writes the logged-in user's own rows.

## Live deployment

- Frontend: https://expense-tracker-frontend-ae67.onrender.com
- Backend API: https://expense-tracker-ao1x.onrender.com (docs at `/docs`)
- Database: Neon project `expense-tracker` (Oregon/US West Render region, Ohio/US East Neon region)
- Google OAuth: consent screen is in **Testing** mode, so only accounts added under Google Cloud Console
  > Google Auth Platform > Audience > Test users can use "Sign in with Google" until the app is published.

Free-tier Render services spin down after inactivity, so the first request after a while may take ~50 seconds.

---

## 1. Set up the Neon database

1. Create a free account at [neon.tech](https://neon.tech) and create a new project.
2. Neon gives you a **connection string** that looks like:
   ```
   postgresql://user:password@ep-example-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
   Copy it - this is your `DATABASE_URL`. (You don't need to create any tables by hand;
   the backend creates the `users` and `expenses` tables automatically on startup.)

---

## 2. Set up Google OAuth (for "Sign in with Google")

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) > create (or pick) a project.
2. Go to **APIs & Services > OAuth consent screen** and configure it (External, add your email as a test user if it's still in testing mode).
3. Go to **APIs & Services > Credentials > Create Credentials > OAuth client ID**.
   - Application type: **Web application**
   - Authorized JavaScript origins: add `http://localhost:5173` (for local dev) and your deployed frontend URL (e.g. `https://expense-tracker-frontend.onrender.com`)
   - You don't need a redirect URI for this flow (Google Identity Services uses a JS popup, not a redirect).
4. Copy the generated **Client ID** (looks like `xxxx.apps.googleusercontent.com`).
   - This ID is used by **both** the frontend (`VITE_GOOGLE_CLIENT_ID`) and the backend (`GOOGLE_CLIENT_ID`) - they must match exactly.
   - There is no client *secret* to configure here, since the frontend only ever sends Google an ID token to verify, not a code exchange.

---

## 3. Run everything locally

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # on macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

copy .env.example .env       # on macOS/Linux: cp .env.example .env
# then edit .env and fill in DATABASE_URL, JWT_SECRET_KEY, GOOGLE_CLIENT_ID

uvicorn main:app --reload
```

The API is now running at `http://localhost:8000`. Visit `http://localhost:8000/docs` for the
interactive Swagger UI, and `http://localhost:8000/` for a basic health check.

### Frontend

```bash
cd frontend
npm install

copy .env.example .env       # on macOS/Linux: cp .env.example .env
# then edit .env and fill in VITE_API_URL=http://localhost:8000 and VITE_GOOGLE_CLIENT_ID

npm run dev
```

Visit the URL Vite prints (usually `http://localhost:5173`).

### MCP server (optional, for AI agent access)

```bash
cd mcp-server
python -m venv venv
venv\Scripts\activate        # on macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

copy .env.example .env       # on macOS/Linux: cp .env.example .env
# then edit .env: API_BASE_URL=http://localhost:8000 (or your deployed backend URL)

python server.py
```

To use it from Claude Desktop, add it to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "expense-tracker": {
      "command": "python",
      "args": ["C:/path/to/Expense Tracker/mcp-server/server.py"],
      "env": { "API_BASE_URL": "http://localhost:8000" }
    }
  }
}
```

Every tool call takes the user's own JWT `token` as an argument (get one by calling the
backend's `/auth/login` endpoint first, e.g. with `curl`), so the MCP server only ever
touches that one user's expenses.

---

## 4. Deploy to Render

### 4a. Backend - Render Web Service

1. Push this repo to GitHub.
2. In Render: **New > Web Service**, connect the repo, set **Root Directory** to `backend`.
3. Render should auto-detect `render.yaml`, or set these manually:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables (Render dashboard > Environment):
   - `DATABASE_URL` - your Neon connection string
   - `JWT_SECRET_KEY` - any long random string (Render can auto-generate one)
   - `GOOGLE_CLIENT_ID` - your Google OAuth client ID
   - `FRONTEND_ORIGIN` - your deployed frontend URL (set this after step 4b, e.g. `https://expense-tracker-frontend.onrender.com`)
5. Deploy. Your API will be live at something like `https://expense-tracker-api.onrender.com`.

### 4b. Frontend - Render Static Site

1. In Render: **New > Static Site**, connect the same repo, set **Root Directory** to `frontend`.
2. Build settings:
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
3. Add environment variables:
   - `VITE_API_URL` - your deployed backend URL from step 4a (e.g. `https://expense-tracker-api.onrender.com`)
   - `VITE_GOOGLE_CLIENT_ID` - your Google OAuth client ID
4. Deploy. Once it's live, go back to Google Cloud Console and add this static site's URL to
   **Authorized JavaScript origins** on your OAuth client, and set it as `FRONTEND_ORIGIN` on the backend service.

### 4c. MCP server

The MCP server is meant to run per-user (e.g. on your own machine via Claude Desktop, or
wherever the agent using it runs) rather than as a shared hosted service, since each tool
call acts on behalf of one specific user's token. Point its `API_BASE_URL` at your deployed
Render backend URL and run it locally as shown in step 3.

---

## Environment variables reference

| Variable | Used by | Description |
|---|---|---|
| `DATABASE_URL` | backend | Neon Postgres connection string |
| `JWT_SECRET_KEY` | backend | Random secret used to sign login tokens |
| `GOOGLE_CLIENT_ID` | backend | Google OAuth client ID, used to verify Google ID tokens |
| `FRONTEND_ORIGIN` | backend | Deployed frontend URL, used for CORS |
| `VITE_API_URL` | frontend | URL of the deployed (or local) backend |
| `VITE_GOOGLE_CLIENT_ID` | frontend | Same Google OAuth client ID as the backend |
| `API_BASE_URL` | mcp-server | URL of the deployed (or local) backend |

---

## Project structure

```
backend/
  main.py         - FastAPI app and all endpoints
  models.py        - SQLAlchemy tables (User, Expense)
  schemas.py        - Pydantic request/response models
  auth.py          - password hashing, JWT, Google token verification
  database.py       - DB engine/session setup
  requirements.txt
  render.yaml
  .env.example

frontend/
  src/
    api.js          - fetch wrapper that attaches the JWT
    App.jsx          - top-level login/dashboard switch
    pages/Login.jsx     - email/password + Google sign-in
    pages/Dashboard.jsx   - month selector, table, form, summary
    components/       - MonthSelector, ExpenseForm, ExpenseTable, SummaryPanel
  index.html
  .env.example

mcp-server/
  server.py         - MCP tools/resource, calls the backend REST API
  requirements.txt
  .env.example
```
