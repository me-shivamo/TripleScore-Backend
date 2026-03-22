# TripleScore Backend API

Base URL: `http://localhost:8000` (dev) | configured via `ALLOWED_ORIGINS`

Interactive docs: `GET /docs` (Swagger UI) · `GET /redoc` (ReDoc)

---

## Authentication

All routes (except `/health`) require a Firebase ID token in the `Authorization` header:

```
Authorization: Bearer <firebase_id_token>
```

The token is verified by the Firebase Admin SDK (`api/deps.py`). On first request the user is automatically created in the database along with a `Gamification` record.

---

## Health Check

### `GET /health`

Returns server status. No authentication required.

**Response**
```json
{ "status": "ok" }
```

---

## Auth — `/auth`

### `POST /auth/login`

Verifies the Firebase ID token, upserts the user record in the database, and returns user info. The frontend calls this once after Google sign-in.

**Request body:** none

**Response `200`**
```json
{
  "id": "string",
  "email": "user@example.com",
  "name": "string | null",
  "avatar_url": "string | null",
  "onboarding_completed": false,
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

## Dashboard — `/dashboard`

### `GET /dashboard`

Returns the full dashboard payload for the authenticated user: readiness score, gamification data, today's stats, active missions, and profile info.

Missions are filtered to non-expired ones, most recently assigned first (max 5).

**Response `200`**
```json
{
  "readiness_score": 72,
  "days_until_exam": 120,
  "gamification": {
    "xp": 1450,
    "level": 3,
    "current_streak": 5,
    "longest_streak": 12
  },
  "today_stats": {
    "questions_attempted": 20,
    "questions_correct": 14,
    "study_minutes": 45,
    "xp_earned": 110
  },
  "missions": [
    {
      "id": "string",
      "title": "string",
      "description": "string",
      "xp_reward": 50,
      "progress": 3,
      "target": 10,
      "completed": false,
      "type": "DAILY"
    }
  ],
  "profile": {
    "onboarding_completed": true,
    "strong_subjects": ["Mathematics"],
    "weak_subjects": ["Physics"]
  }
}
```

Fields default to `0` / `false` / `[]` when the underlying records don't exist yet.

---

## Nova (AI Chat) — `/nova`

### `POST /nova/chat`

Streams Nova's AI response as plain text chunks (`Transfer-Encoding: chunked`).

Saves the user message before streaming, then saves the full assistant response as a background task after the stream ends. In `ONBOARDING` mode, also monitors for completion signals and auto-runs the holistic onboarding data extraction when done.

**Request body**
```json
{
  "message": "string",
  "mode": "ONBOARDING | COMPANION | MOCK_ANALYSIS"
}
```

| Mode | Description |
|------|-------------|
| `ONBOARDING` | Used during the initial onboarding conversation. Triggers profile extraction on completion. |
| `COMPANION` | Regular study companion mode. |
| `MOCK_ANALYSIS` | Used when analysing a mock test upload. |

**Response `200`** — `Content-Type: text/plain; charset=utf-8`

Streamed text chunks. The internal sentinel `__NOVA_ONBOARDING_COMPLETE__` may appear at the end of onboarding responses; the frontend should strip it from display.

**Headers on response**
- `X-Nova-Mode: <mode>`

**Error `400`** — message is empty

---

### `GET /nova/history`

Returns the last 50 chat messages for the user, ordered oldest → newest.

**Response `200`**
```json
{
  "messages": [
    {
      "id": "string",
      "role": "USER | ASSISTANT",
      "content": "string",
      "metadata": { "mode": "COMPANION" },
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

### `GET /nova/onboarding-status`

Returns whether the user has completed onboarding and their current onboarding step.

**Response `200`**
```json
{
  "onboarding_completed": false,
  "onboarding_step": 0
}
```

---

## Diagnostic — `/diagnostic`

The diagnostic flow consists of two mini-tests (one on a strong subject chapter, one on a weak subject chapter). After both tests, prior mastery estimates are seeded for all untested chapters.

### `POST /diagnostic/start`

Initialises a diagnostic session for the user and returns profile info plus suggested chapters.

If the user has already completed or skipped the diagnostic, returns `{ "already_done": true }` and the frontend should redirect to `/dashboard`.

**Request body:** none

**Response `200`**
```json
{
  "already_done": false,
  "profile": {
    "name": "string | null",
    "exam_attempt_date": "2025-04-01T00:00:00Z | null",
    "strong_subjects": ["Mathematics"],
    "weak_subjects": ["Physics"],
    "previous_score": 180,
    "daily_study_hours": 4.0
  },
  "strong_suggestion": {
    "subject": "Mathematics",
    "chapter": "Integral Calculus"
  },
  "weak_suggestion": {
    "subject": "Physics",
    "chapter": "Electrostatics"
  },
  "chapters_by_subject": {
    "Physics": ["Mechanics", "Electrostatics", "Optics"],
    "Chemistry": ["Organic Chemistry", "Electrochemistry"],
    "Mathematics": ["Integral Calculus", "Algebra", "Coordinate Geometry"]
  }
}
```

---

### `POST /diagnostic/questions`

Fetches a random set of questions for the given subject and chapter, with options shuffled.

**Request body**
```json
{
  "subject": "Physics",
  "chapter": "Electrostatics",
  "count": 12
}
```

**Response `200`**
```json
{
  "questions": [
    {
      "id": "string",
      "subject": "Physics",
      "chapter": "Electrostatics",
      "topic": "Coulomb's Law",
      "content": "Question text...",
      "question_type": "MCQ",
      "options": [
        { "label": "A", "text": "Option A text" },
        { "label": "B", "text": "Option B text" },
        { "label": "C", "text": "Option C text" },
        { "label": "D", "text": "Option D text" }
      ],
      "difficulty": "MEDIUM"
    }
  ]
}
```

**Error `400`** — invalid subject
**Error `404`** — no questions found for that chapter

---

### `POST /diagnostic/submit`

Grades a completed test, records a `PracticeSession` + `QuestionAttempt` records, calculates a mastery score for the tested chapter (Bayesian IRT), and upserts `TopicProgress`.

On `test_number: 2`, also seeds prior mastery estimates for all untested chapters based on the user's stated strong/weak subjects.

Awards XP via the gamification engine (`50 + correct_count × 3` base XP).

**Request body**
```json
{
  "test_number": 1,
  "subject": "Physics",
  "chapter": "Electrostatics",
  "attempts": [
    {
      "question_id": "string",
      "selected_option": "A | null",
      "time_taken_secs": 45
    }
  ]
}
```

`selected_option: null` means the question was skipped (not counted toward mastery).

**Response `200`**
```json
{
  "score": { "correct": 8, "total": 12 },
  "mastery_score": 0.73,
  "session_id": "string",
  "xp_result": {
    "xp_awarded": 74,
    "new_total_xp": 1524,
    "level_up": false
  }
}
```

**Error `400`** — `test_number` not 1 or 2, or `attempts` is empty

---

### `POST /diagnostic/skip`

Marks the diagnostic as skipped and seeds prior mastery estimates for all chapters based on the user's stated subjects. This unblocks access to the rest of the app.

**Request body:** none

**Response `200`**
```json
{ "ok": true }
```

---

## Error Responses

All errors follow FastAPI's default format:

```json
{
  "detail": "Error message"
}
```

| Status | Meaning |
|--------|---------|
| `400` | Bad request (validation error or invalid input) |
| `401` | Missing, invalid, or expired Firebase token |
| `404` | Resource not found |
| `422` | Pydantic validation error (wrong body shape) |
| `500` | Internal server error |

---

## Data Models Reference

### Question difficulty levels
`EASY` · `MEDIUM` · `HARD`

### Question types
`MCQ` (multiple choice with 4 options)

### Mission types
`DAILY` · `WEEKLY`

### Nova modes
`ONBOARDING` · `COMPANION` · `MOCK_ANALYSIS`

### Diagnostic session statuses
`PENDING` · `TEST1_COMPLETE` · `COMPLETED` · `SKIPPED`
