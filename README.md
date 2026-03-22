# TripleScore — Backend

AI-powered JEE prep platform backend. Built with **FastAPI** (HTTP/streaming routes) + **Django ORM** (models, migrations, admin) + **PostgreSQL**.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| HTTP framework | FastAPI 0.115+ |
| ORM & migrations | Django 5+ |
| Database | PostgreSQL |
| Auth | Firebase Admin SDK (token verification) |
| AI providers | Anthropic Claude · Google Gemini |
| Server | Uvicorn |

---

## Project Structure

```
TripleScore-Backend/
├── api/
│   ├── main.py            # FastAPI app, CORS, router registration
│   ├── deps.py            # Firebase token verification, get_current_user
│   ├── routers/           # Route handlers
│   │   ├── auth.py        # POST /auth/login
│   │   ├── dashboard.py   # GET /dashboard
│   │   ├── nova.py        # POST /nova/chat  GET /nova/history  GET /nova/onboarding-status
│   │   └── diagnostic.py  # POST /diagnostic/start|questions|submit|skip
│   ├── schemas/           # Pydantic request/response models
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   ├── nova.py
│   │   └── diagnostic.py
│   └── services/          # Business logic
│       ├── ai/            # AI provider abstraction (Anthropic / Gemini)
│       ├── nova/          # Prompts, context builder, onboarding parser
│       ├── gamification/  # XP engine, streak tracker
│       ├── analytics/     # Readiness score calculator
│       └── diagnostic/    # Mastery calculator, chapter suggestions
├── apps/                  # Django apps (ORM models + admin)
│   ├── users/             # User, UserProfile
│   ├── nova/              # ChatMessage
│   ├── questions/         # Question, QuestionAttempt
│   ├── practice/          # PracticeSession
│   ├── gamification/      # Gamification, Mission, UserMission
│   ├── analytics/         # DailyStats, TopicProgress
│   └── diagnostic/        # DiagnosticSession
├── config/
│   ├── settings.py        # Django settings (reads from .env)
│   └── urls.py            # Django URL conf (admin panel)
├── scripts/
│   └── pdf-extractor/     # Utility: converts JEE PDFs to markdown (datalab_sdk)
├── manage.py
└── requirements.txt
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL running locally (or a remote connection string)
- Firebase project with a service account key
- Anthropic or Gemini API key

### Setup

```bash
cd TripleScore-Backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and fill in all required values (see Environment Variables below)

# Run database migrations
python manage.py migrate

# Start the API server
uvicorn api.main:app --reload --port 8000
```

The API is now running at `http://localhost:8000`.

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Django admin: run `python manage.py runserver 8001` in a second terminal → `http://localhost:8001/admin`

---

## Environment Variables

Create a `.env` file in the repo root (copy from `.env.example`):

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True

# PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/triplescore

# Firebase Admin SDK (service account)
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxx@your-project.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"

# AI provider — set to "anthropic" or "gemini"
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...          # only needed if AI_PROVIDER=gemini

# CORS — comma-separated list of allowed frontend origins
ALLOWED_ORIGINS=http://localhost:3000
```

---

## API Overview

See [API.md](API.md) for the full endpoint reference.

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/health` | Server health check |
| `POST` | `/auth/login` | Verify Firebase token, upsert user |
| `GET` | `/dashboard` | Readiness score, XP, streak, missions |
| `POST` | `/nova/chat` | Streaming AI chat (Nova) |
| `GET` | `/nova/history` | Last 50 chat messages |
| `GET` | `/nova/onboarding-status` | Check if onboarding is complete |
| `POST` | `/diagnostic/start` | Initialise diagnostic session |
| `POST` | `/diagnostic/questions` | Fetch questions for a chapter |
| `POST` | `/diagnostic/submit` | Grade test, record mastery, award XP |
| `POST` | `/diagnostic/skip` | Skip diagnostic, seed prior estimates |
