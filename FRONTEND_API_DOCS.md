# TripleScore — Frontend Integration Guide

> Complete API reference for building the TripleScore frontend. This document covers every endpoint, data model, TypeScript type, and integration detail a frontend developer needs.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Authentication](#2-authentication)
3. [API Endpoints](#3-api-endpoints)
4. [Data Models](#4-data-models)
5. [WebSocket / Real-time](#5-websocket--real-time)
6. [Error Handling](#6-error-handling)
7. [Environment Setup](#7-environment-setup)
8. [TypeScript Types](#8-typescript-types)

---

## 1. Overview

### What is TripleScore?

TripleScore is an AI-powered JEE (Joint Entrance Examination) preparation platform. It provides:

- **Nova** — an AI study companion that onboards students through a conversational flow, then acts as an ongoing study buddy
- **Diagnostic tests** — initial skill assessment across Physics, Chemistry, and Math with Bayesian mastery scoring
- **Dashboard** — readiness score, XP/level gamification, streaks, daily stats, and missions
- **Gamification** — XP engine, streak tracking, missions, badges, and leveling

### Tech Stack

| Layer | Technology |
|---|---|
| HTTP Framework | **FastAPI** (all API routes) |
| ORM & Migrations | **Django 5+** (models, admin panel) |
| Database | **PostgreSQL** |
| Auth | **Firebase Auth** (Google sign-in on frontend, token verification on backend) |
| AI Providers | Anthropic Claude / Google Gemini (configurable) |
| Server | Uvicorn |

### Base URL

- **Local development:** `http://localhost:8000`
- **Interactive API docs:** `GET /docs` (Swagger UI) or `GET /redoc` (ReDoc)

### How to Run Locally

```bash
cd TripleScore-Backend
pip install -r requirements.txt
cp .env.example .env   # then fill in values
python manage.py migrate
uvicorn api.main:app --reload --port 8000
```

---

## 2. Authentication

### How Auth Works

TripleScore uses **Firebase Authentication** with Google sign-in. The flow is:

1. **Frontend:** User signs in with Google via Firebase SDK. Firebase returns an **ID token**.
2. **Frontend:** Sends the ID token to the backend in every request via the `Authorization` header.
3. **Backend:** Verifies the token using the Firebase Admin SDK. On first request, automatically creates a `User` record and a `Gamification` record in the database.
4. There is **no session**, **no refresh token endpoint**, and **no backend-issued JWT**. The Firebase ID token IS the auth token.

### Sending the Auth Token

Every request (except `GET /health`) must include:

```
Authorization: Bearer <firebase_id_token>
```

### Token Refresh

Firebase ID tokens expire after **1 hour**. The frontend must refresh them using the Firebase SDK:

```typescript
const token = await firebase.auth().currentUser?.getIdToken(/* forceRefresh */ true);
```

If the token is expired, the backend returns `401 Unauthorized`.

### Login Endpoint

After Firebase Google sign-in, call `POST /auth/login` once to upsert the user in the database and get back the user record. This is the only "login" — there is no signup vs login distinction.

---

## 3. API Endpoints

### Health Check

#### `GET /health`

No authentication required.

**Response `200`**
```json
{ "status": "ok" }
```

---

### Auth — `/auth`

#### `POST /auth/login`

Verifies the Firebase ID token, upserts the user in the database, and returns user info. Call this once after Google sign-in.

- **Auth required:** Yes
- **Request body:** None

**Response `200`**
```json
{
  "id": "a1b2c3d4e5f6a1b2c3d4e5f6",
  "email": "student@example.com",
  "name": "Rahul Sharma",
  "avatar_url": "https://lh3.googleusercontent.com/...",
  "onboarding_completed": false,
  "created_at": "2026-01-15T10:30:00Z"
}
```

**TypeScript interface:** [`UserResponse`](#userresponse)

---

### Dashboard — `/dashboard`

#### `GET /dashboard`

Returns the full dashboard payload: readiness score, gamification data, today's stats, active missions, and profile info.

- **Auth required:** Yes
- **Request body:** None

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
      "id": "abc123",
      "title": "Daily Grind",
      "description": "Solve 10 questions today",
      "xp_reward": 50,
      "progress": 3,
      "target": 10,
      "completed": false,
      "type": "DAILY"
    }
  ],
  "profile": {
    "onboarding_completed": true,
    "strong_subjects": ["MATH"],
    "weak_subjects": ["PHYSICS"]
  }
}
```

**Notes:**
- `readiness_score` is calculated on-the-fly if not cached for today. Formula: 35% accuracy + 20% speed + 30% syllabus coverage + 15% consistency.
- `days_until_exam` is `null` if no exam date is set.
- `missions` contains up to 5 non-expired missions, most recently assigned first.
- All fields default to `0` / `false` / `[]` / `null` when no underlying data exists.

**TypeScript interface:** [`DashboardResponse`](#dashboardresponse)

---

### Nova (AI Chat) — `/nova`

#### `POST /nova/chat`

Sends a message to Nova and streams the AI response as plain text chunks.

- **Auth required:** Yes
- **Content-Type (request):** `application/json`
- **Content-Type (response):** `text/plain; charset=utf-8`
- **Transfer-Encoding:** `chunked` (streaming)

**Request body**
```json
{
  "message": "How should I approach Electrostatics?",
  "mode": "COMPANION"
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `message` | `string` | Yes | — | The user's message. Cannot be empty. |
| `mode` | `string` | No | `"COMPANION"` | One of `"ONBOARDING"`, `"COMPANION"`, `"MOCK_ANALYSIS"` |

**Response `200`** — Streamed plain text

The response is streamed as raw text chunks. Read it with a streaming fetch:

```typescript
const response = await fetch('/nova/chat', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ message: "Hello", mode: "ONBOARDING" }),
});

const reader = response.body!.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const text = decoder.decode(value, { stream: true });
  // Append `text` to the chat UI
}
```

**Response headers:**
- `X-Nova-Mode: <mode>` — echoes the mode used

**Onboarding sentinel:**
In `ONBOARDING` mode, the final onboarding message may contain `__NOVA_ONBOARDING_COMPLETE__` on its own line. The frontend **must strip this** from display. When this appears, onboarding is complete — redirect the user to the diagnostic or dashboard.

**Modes explained:**

| Mode | When to use |
|---|---|
| `ONBOARDING` | First-time user. Nova asks questions to understand the student (exam date, strengths, weaknesses, struggles). Automatically triggers profile extraction and study workflow generation on completion. |
| `COMPANION` | Regular study companion chat. Nova has full context of the student's profile and performance. |
| `MOCK_ANALYSIS` | When analyzing a mock test upload. Nova identifies patterns and gives actionable feedback. |

**Error `400`** — message is empty

**TypeScript interface:** [`ChatRequest`](#chatrequest)

---

#### `GET /nova/history`

Returns the last 50 chat messages for the user, oldest first.

- **Auth required:** Yes

**Response `200`**
```json
{
  "messages": [
    {
      "id": "msg_abc123",
      "role": "USER",
      "content": "How do I study for JEE?",
      "metadata": { "mode": "COMPANION" },
      "created_at": "2026-01-15T10:30:00Z"
    },
    {
      "id": "msg_def456",
      "role": "ASSISTANT",
      "content": "Great question! Let's start with...",
      "metadata": { "mode": "COMPANION" },
      "created_at": "2026-01-15T10:30:05Z"
    }
  ]
}
```

**TypeScript interface:** [`HistoryResponse`](#historyresponse)

---

#### `GET /nova/onboarding-status`

Returns whether onboarding is complete and the current step.

- **Auth required:** Yes

**Response `200`**
```json
{
  "onboarding_completed": false,
  "onboarding_step": 0
}
```

**TypeScript interface:** [`OnboardingStatusResponse`](#onboardingstatusresponse)

---

### Diagnostic — `/diagnostic`

The diagnostic flow is a two-test skill assessment:
1. **Test 1:** A mini-test on a chapter from the student's strong subject
2. **Test 2:** A mini-test on a chapter from the student's weak subject

After both tests, prior mastery estimates are seeded for all untested chapters. The student can also skip the entire diagnostic.

#### `POST /diagnostic/start`

Initializes a diagnostic session and returns profile info plus suggested chapters.

- **Auth required:** Yes
- **Request body:** None

**Response `200` (not yet done)**
```json
{
  "already_done": false,
  "profile": {
    "name": "Rahul",
    "exam_attempt_date": "2026-04-01T00:00:00Z",
    "strong_subjects": ["MATH"],
    "weak_subjects": ["PHYSICS"],
    "previous_score": 180,
    "daily_study_hours": 4.0
  },
  "strong_suggestion": {
    "subject": "MATH",
    "chapter": "Applications of Derivatives"
  },
  "weak_suggestion": {
    "subject": "PHYSICS",
    "chapter": "Modern Physics"
  },
  "chapters_by_subject": {
    "PHYSICS": ["Kinematics", "Laws of Motion", "..."],
    "CHEMISTRY": ["Mole Concept", "Atomic Structure", "..."],
    "MATH": ["Sets and Relations", "Complex Numbers", "..."]
  }
}
```

**Response `200` (already completed or skipped)**
```json
{
  "already_done": true
}
```

When `already_done` is `true`, all other fields are `null`. Redirect to the dashboard.

**TypeScript interface:** [`DiagnosticStartResponse`](#diagnosticstartresponse)

---

#### `POST /diagnostic/questions`

Fetches random questions for a given subject and chapter. Options are shuffled.

- **Auth required:** Yes

**Request body**
```json
{
  "subject": "PHYSICS",
  "chapter": "Electrostatics",
  "count": 12
}
```

| Field | Type | Required | Default |
|---|---|---|---|
| `subject` | `string` | Yes | — |
| `chapter` | `string` | Yes | — |
| `count` | `number` | No | `10` |

**Response `200`**
```json
{
  "questions": [
    {
      "id": "q_abc123",
      "subject": "PHYSICS",
      "chapter": "Electrostatics",
      "topic": "Coulomb's Law",
      "content": "Two point charges of 3μC and -4μC are placed...",
      "question_type": "MCQ",
      "options": [
        { "label": "A", "text": "2.5 N" },
        { "label": "B", "text": "3.6 N" },
        { "label": "C", "text": "5.4 N" },
        { "label": "D", "text": "7.2 N" }
      ],
      "difficulty": "MEDIUM"
    }
  ]
}
```

**Important:** The `correct_option` and `explanation` fields are intentionally NOT returned to the frontend. Grading happens server-side on submit.

**Error `400`** — invalid subject (must be `PHYSICS`, `CHEMISTRY`, or `MATH`)
**Error `404`** — no questions found for that chapter

**TypeScript interfaces:** [`QuestionsRequest`](#questionsrequest), [`QuestionsResponse`](#questionsresponse)

---

#### `POST /diagnostic/submit`

Submits answers for a diagnostic test. Grades them, records a practice session, calculates mastery, and awards XP.

- **Auth required:** Yes

**Request body**
```json
{
  "test_number": 1,
  "subject": "PHYSICS",
  "chapter": "Electrostatics",
  "attempts": [
    {
      "question_id": "q_abc123",
      "selected_option": "B",
      "time_taken_secs": 45
    },
    {
      "question_id": "q_def456",
      "selected_option": null,
      "time_taken_secs": 120
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `test_number` | `1 \| 2` | Which diagnostic test this is |
| `subject` | `string` | Subject tested |
| `chapter` | `string` | Chapter tested |
| `attempts` | `SubmitAttempt[]` | One entry per question |
| `attempts[].question_id` | `string` | The question ID from `/diagnostic/questions` |
| `attempts[].selected_option` | `string \| null` | The selected option label (e.g. `"A"`), or `null` if skipped |
| `attempts[].time_taken_secs` | `number` | Seconds spent on this question |

**Response `200`**
```json
{
  "score": { "correct": 8, "total": 12 },
  "mastery_score": 0.73,
  "session_id": "sess_abc123",
  "xp_result": {
    "xp_gained": 74,
    "new_xp": 1524,
    "old_level": 3,
    "new_level": 3,
    "level_up": false
  }
}
```

**XP formula:** `50 + (correct_count * 3)` base XP.

**Mastery formula (Bayesian IRT):**
- `base = correct / attempted` (skipped questions excluded)
- `speed_factor = clamp(90 / avg_time_secs, 0.5, 1.5)` — benchmark 90 seconds/question
- `difficulty_multiplier = average(EASY=0.8, MEDIUM=1.0, HARD=1.3)`
- `mastery = clamp(base * speed_factor * difficulty_multiplier, 0, 1)`

**Side effects of `test_number: 2`:** Seeds prior mastery estimates for ALL untested JEE chapters based on subject strength:
- Strong subject chapters: `0.55`
- Weak subject chapters: `0.25`
- Unknown subject chapters: `0.30`

**Error `400`** — `test_number` not 1 or 2, or `attempts` is empty

**TypeScript interfaces:** [`SubmitRequest`](#submitrequest), [`SubmitResponse`](#submitresponse)

---

#### `POST /diagnostic/skip`

Skips the diagnostic entirely. Seeds prior mastery estimates for all chapters and unblocks the rest of the app.

- **Auth required:** Yes
- **Request body:** None

**Response `200`**
```json
{ "ok": true }
```

---

## 4. Data Models

### Entity Relationship Diagram (text)

```
User (1) ──── (1) UserProfile
  │
  ├── (1) ──── (1) Gamification ──── (*) XPEvent
  │
  ├── (*) ChatMessage
  │
  ├── (*) PracticeSession ──── (*) QuestionAttempt ──── (1) Question
  │
  ├── (*) MockTest
  │
  ├── (1) DiagnosticSession
  │
  ├── (*) DailyStats
  │
  ├── (*) TopicProgress ──── (*) RevisionItem
  │
  ├── (*) UserMission ──── (1) Mission
  │
  └── (*) UserBadge ──── (1) Badge
```

### User

| Field | Type | Description |
|---|---|---|
| `id` | `string` (24 char) | Primary key, UUID-based |
| `firebase_uid` | `string` | Firebase UID, unique |
| `email` | `string` | Unique email |
| `name` | `string \| null` | Display name from Google |
| `avatar_url` | `string \| null` | Google profile picture URL |
| `created_at` | `datetime` | Auto-set on creation |
| `updated_at` | `datetime` | Auto-updated |

### UserProfile

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Primary key |
| `user` | `FK → User` | One-to-one |
| `exam_attempt_date` | `datetime \| null` | Target JEE exam date |
| `daily_study_hours` | `float \| null` | Hours per day |
| `target_score` | `int \| null` | Target JEE score |
| `previous_score` | `int \| null` | Previous JEE score (0-300) |
| `confidence_level` | `int \| null` | Self-rated 1-10 |
| `strong_subjects` | `string[]` | e.g. `["PHYSICS", "MATH"]` |
| `weak_subjects` | `string[]` | e.g. `["CHEMISTRY"]` |
| `study_struggles` | `string[]` | e.g. `["exam panic", "forgetting concepts"]` |
| `motivational_state` | `string \| null` | e.g. `"Anxious but motivated"` |
| `onboarding_completed` | `boolean` | Whether Nova onboarding is done |
| `onboarding_step` | `int` | Current step (0-6) |
| `study_workflow` | `JSON \| null` | AI-generated study plan |
| `created_at` | `datetime` | |
| `updated_at` | `datetime` | |

### ChatMessage

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Primary key |
| `user` | `FK → User` | |
| `role` | `"USER" \| "ASSISTANT"` | |
| `content` | `string` | Message text |
| `metadata` | `JSON \| null` | e.g. `{ "mode": "COMPANION" }` |
| `created_at` | `datetime` | |

### Question

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Primary key |
| `subject` | `"PHYSICS" \| "CHEMISTRY" \| "MATH"` | |
| `chapter` | `string` | e.g. `"Electrostatics"` |
| `topic` | `string` | e.g. `"Coulomb's Law"` |
| `content` | `string` | Question text |
| `question_type` | `"MCQ" \| "INTEGER"` | |
| `options` | `{ label: string, text: string }[]` | MCQ options |
| `correct_option` | `string` | Correct answer label (not exposed to frontend) |
| `explanation` | `string` | Solution explanation (not exposed to frontend) |
| `difficulty` | `"EASY" \| "MEDIUM" \| "HARD"` | |
| `tags` | `string[]` | |
| `source` | `string \| null` | e.g. `"JEE Mains 2025"` |
| `created_at` | `datetime` | |

### QuestionAttempt

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Primary key |
| `user` | `FK → User` | |
| `session` | `FK → PracticeSession` | |
| `question` | `FK → Question` | |
| `selected_option` | `string \| null` | `null` = skipped |
| `is_correct` | `boolean` | |
| `time_taken_secs` | `int` | |
| `attempted_at` | `datetime` | |

### PracticeSession

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Primary key |
| `user` | `FK → User` | |
| `subject` | `"PHYSICS" \| "CHEMISTRY" \| "MATH" \| null` | |
| `chapter` | `string \| null` | |
| `topic` | `string \| null` | |
| `mode` | `"TOPIC" \| "TIMED" \| "ADAPTIVE" \| "MOCK_REVIEW"` | |
| `total_questions` | `int` | |
| `started_at` | `datetime` | |
| `completed_at` | `datetime \| null` | |
| `duration_secs` | `int \| null` | |
| `xp_earned` | `int` | |

### MockTest

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Primary key |
| `user` | `FK → User` | |
| `test_name` | `string` | |
| `attempt_date` | `datetime` | |
| `total_questions` | `int` | Default 90 |
| `attempted` | `int` | |
| `correct` | `int` | |
| `incorrect` | `int` | |
| `skipped` | `int` | |
| `physics_score` | `int \| null` | |
| `chemistry_score` | `int \| null` | |
| `math_score` | `int \| null` | |
| `total_marks` | `int \| null` | |
| `max_marks` | `int` | Default 300 |
| `time_taken_mins` | `int \| null` | |
| `raw_data` | `JSON \| null` | |
| `ai_analysis` | `JSON \| null` | |
| `analysis_status` | `"PENDING" \| "PROCESSING" \| "COMPLETED" \| "FAILED"` | |
| `created_at` | `datetime` | |

### Gamification

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Primary key |
| `user` | `FK → User` | One-to-one |
| `xp` | `int` | Total XP, default 0 |
| `level` | `int` | Current level, default 1 |
| `current_streak` | `int` | Consecutive active days |
| `longest_streak` | `int` | All-time longest streak |
| `last_active_date` | `datetime \| null` | |
| `total_study_mins` | `int` | |
| `season_rank` | `int \| null` | |

**Leveling formula:** `level = floor(xp / 500) + 1`

### XPEvent

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Primary key |
| `gamification` | `FK → Gamification` | |
| `amount` | `int` | XP gained |
| `reason` | `XPReason` | See enum below |
| `reference_id` | `string \| null` | Related entity ID |
| `created_at` | `datetime` | |

**XP Reasons:** `PRACTICE_SESSION`, `CORRECT_ANSWER`, `MOCK_COMPLETED`, `MISSION_COMPLETED`, `STREAK_BONUS`, `ONBOARDING_COMPLETE`, `DAILY_LOGIN`, `DIAGNOSTIC_COMPLETE`

**XP amounts:**

| Reason | Base XP |
|---|---|
| `CORRECT_EASY` | 5 |
| `CORRECT_MEDIUM` | 10 |
| `CORRECT_HARD` | 15 |
| `PRACTICE_SESSION` | 20 (+ up to 30 accuracy bonus) |
| `MOCK_COMPLETED` | 50 |
| `STREAK_BONUS` | 10 (x2 at 7-day, x3 at 14-day, x4 at 30-day streak) |
| `ONBOARDING_COMPLETE` | 100 |
| `DAILY_LOGIN` | 5 |
| `DIAGNOSTIC_COMPLETE` | 50 base + 3 per correct answer |

### Mission

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Primary key |
| `title` | `string` | e.g. `"Daily Grind"` |
| `description` | `string` | |
| `type` | `"DAILY" \| "WEEKLY"` | |
| `xp_reward` | `int` | |
| `target` | `int` | e.g. `10` (questions to solve) |
| `metric` | `string` | e.g. `"questions_correct"`, `"mock_completed"` |
| `subject` | `string \| null` | Scoped to a subject, or null for any |
| `difficulty` | `string \| null` | |
| `is_active` | `boolean` | |

### UserMission

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Primary key |
| `user` | `FK → User` | |
| `mission` | `FK → Mission` | |
| `progress` | `int` | Current progress toward target |
| `completed` | `boolean` | |
| `completed_at` | `datetime \| null` | |
| `assigned_at` | `datetime` | |
| `expires_at` | `datetime` | |

### Badge

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Primary key |
| `name` | `string` | |
| `description` | `string` | |
| `icon_url` | `string` | |
| `condition` | `JSON` | e.g. `{ "type": "streak", "value": 7 }` |
| `xp_reward` | `int` | |
| `rarity` | `"COMMON" \| "RARE" \| "EPIC" \| "LEGENDARY"` | |

### UserBadge

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Primary key |
| `user` | `FK → User` | |
| `badge` | `FK → Badge` | |
| `earned_at` | `datetime` | |

Unique constraint: one badge per user.

### TopicProgress

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Primary key |
| `user` | `FK → User` | |
| `subject` | `string` | |
| `chapter` | `string` | |
| `topic` | `string` | |
| `total_attempted` | `int` | |
| `total_correct` | `int` | |
| `avg_time_secs` | `float` | |
| `mastery_score` | `float` | 0.0 to 1.0 |
| `last_attempted` | `datetime \| null` | |
| `is_unlocked` | `boolean` | |
| `updated_at` | `datetime` | |

Unique constraint: `(user, subject, chapter, topic)`.

### DailyStats

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Primary key |
| `user` | `FK → User` | |
| `date` | `date` | |
| `readiness_score` | `int \| null` | |
| `questions_attempted` | `int` | |
| `questions_correct` | `int` | |
| `study_minutes` | `int` | |
| `xp_earned` | `int` | |
| `missions_completed` | `int` | |

Unique constraint: `(user, date)`.

### DiagnosticSession

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Primary key |
| `user` | `FK → User` | One-to-one |
| `status` | `"IN_PROGRESS" \| "TEST1_COMPLETE" \| "COMPLETED" \| "SKIPPED"` | |
| `test1_session_id` | `string \| null` | FK reference to PracticeSession |
| `test2_session_id` | `string \| null` | |
| `test1_subject` | `string \| null` | |
| `test1_chapter` | `string \| null` | |
| `test2_subject` | `string \| null` | |
| `test2_chapter` | `string \| null` | |
| `skipped` | `boolean` | |
| `completed_at` | `datetime \| null` | |
| `created_at` | `datetime` | |

### RevisionItem (Spaced Repetition)

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Primary key |
| `user` | `FK → User` | |
| `topic_progress` | `FK → TopicProgress` | |
| `next_review_at` | `datetime` | |
| `interval_days` | `int` | Default 1 |
| `ease_factor` | `float` | SM-2 algorithm, default 2.5 |
| `repetitions` | `int` | Default 0 |
| `created_at` | `datetime` | |
| `updated_at` | `datetime` | |

---

## 5. WebSocket / Real-time

There are **no WebSocket endpoints**. All real-time functionality uses HTTP streaming:

- `POST /nova/chat` uses `Transfer-Encoding: chunked` to stream AI responses as plain text. Use the Fetch API with `ReadableStream` to consume it (see the [example above](#post-novachat)).

---

## 6. Error Handling

### Error Response Format

All errors follow FastAPI's standard format:

```json
{
  "detail": "Error message here"
}
```

For Pydantic validation errors (422):

```json
{
  "detail": [
    {
      "loc": ["body", "message"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

### Common Error Codes

| Status | Meaning | Common Causes |
|---|---|---|
| `400` | Bad Request | Empty message, invalid subject, test_number not 1/2, empty attempts |
| `401` | Unauthorized | Missing `Authorization` header, invalid token, expired token, token has no email |
| `404` | Not Found | No questions found for the given chapter |
| `422` | Validation Error | Request body doesn't match expected schema (wrong types, missing required fields) |
| `500` | Internal Server Error | Server-side error |

### Handling 401 in the Frontend

When you receive a 401:
1. Try refreshing the Firebase token with `getIdToken(true)`
2. Retry the request once
3. If still 401, sign the user out and redirect to login

---

## 7. Environment Setup

### Required Environment Variables

Create a `.env` file in the backend root:

```env
# Django
SECRET_KEY=your-secret-key-min-50-chars
DEBUG=True

# PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/triplescore

# Firebase Admin SDK (service account credentials)
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxx@your-project.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"

# AI provider — "anthropic" or "gemini"
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...          # only needed if AI_PROVIDER=gemini

# CORS — comma-separated list of allowed frontend origins
ALLOWED_ORIGINS=http://localhost:3000
```

### Frontend Environment Variables

The frontend needs:
- Firebase config (project ID, API key, auth domain) — same Firebase project as the backend
- Backend API base URL (e.g. `http://localhost:8000`)

### Local Development Steps

```bash
# 1. Backend
cd TripleScore-Backend
pip install -r requirements.txt
cp .env.example .env
# Fill in .env values

# 2. Database
createdb triplescore   # or use your preferred method
python manage.py migrate

# 3. Start API server
uvicorn api.main:app --reload --port 8000

# 4. (Optional) Django admin on a separate port
python manage.py createsuperuser
python manage.py runserver 8001
# Visit http://localhost:8001/admin
```

### Database

PostgreSQL is required. The Django ORM manages all migrations. Run `python manage.py migrate` after any model changes.

---

## 8. TypeScript Types

Copy these interfaces directly into your frontend project.

```typescript
// ============================================================================
// Enums / Literal Types
// ============================================================================

type Subject = "PHYSICS" | "CHEMISTRY" | "MATH";

type Difficulty = "EASY" | "MEDIUM" | "HARD";

type QuestionType = "MCQ" | "INTEGER";

type NovaMode = "ONBOARDING" | "COMPANION" | "MOCK_ANALYSIS";

type MessageRole = "USER" | "ASSISTANT";

type MissionType = "DAILY" | "WEEKLY";

type DiagnosticStatus = "IN_PROGRESS" | "TEST1_COMPLETE" | "COMPLETED" | "SKIPPED";

type SessionMode = "TOPIC" | "TIMED" | "ADAPTIVE" | "MOCK_REVIEW";

type AnalysisStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";

type BadgeRarity = "COMMON" | "RARE" | "EPIC" | "LEGENDARY";

type XPReason =
  | "PRACTICE_SESSION"
  | "CORRECT_ANSWER"
  | "MOCK_COMPLETED"
  | "MISSION_COMPLETED"
  | "STREAK_BONUS"
  | "ONBOARDING_COMPLETE"
  | "DAILY_LOGIN"
  | "DIAGNOSTIC_COMPLETE";

// ============================================================================
// Auth
// ============================================================================

/** POST /auth/login — Response */
interface UserResponse {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
  onboarding_completed: boolean;
  created_at: string; // ISO 8601
}

// ============================================================================
// Dashboard
// ============================================================================

interface GamificationData {
  xp: number;
  level: number;
  current_streak: number;
  longest_streak: number;
}

interface TodayStats {
  questions_attempted: number;
  questions_correct: number;
  study_minutes: number;
  xp_earned: number;
}

interface MissionData {
  id: string;
  title: string;
  description: string;
  xp_reward: number;
  progress: number;
  target: number;
  completed: boolean;
  type: MissionType;
}

interface ProfileData {
  onboarding_completed: boolean;
  strong_subjects: Subject[];
  weak_subjects: Subject[];
}

/** GET /dashboard — Response */
interface DashboardResponse {
  readiness_score: number | null;
  days_until_exam: number | null;
  gamification: GamificationData;
  today_stats: TodayStats;
  missions: MissionData[];
  profile: ProfileData;
}

// ============================================================================
// Nova (AI Chat)
// ============================================================================

/** POST /nova/chat — Request */
interface ChatRequest {
  message: string;
  mode?: NovaMode; // defaults to "COMPANION"
}

// POST /nova/chat — Response is streamed plain text, not JSON.

interface MessageResponse {
  id: string;
  role: MessageRole;
  content: string;
  metadata: Record<string, unknown> | null;
  created_at: string; // ISO 8601
}

/** GET /nova/history — Response */
interface HistoryResponse {
  messages: MessageResponse[];
}

/** GET /nova/onboarding-status — Response */
interface OnboardingStatusResponse {
  onboarding_completed: boolean;
  onboarding_step: number;
}

// ============================================================================
// Diagnostic
// ============================================================================

interface ChapterSuggestion {
  subject: Subject;
  chapter: string;
}

interface DiagnosticProfileInfo {
  name: string | null;
  exam_attempt_date: string | null; // ISO 8601
  strong_subjects: Subject[];
  weak_subjects: Subject[];
  previous_score: number | null;
  daily_study_hours: number | null;
}

/** POST /diagnostic/start — Response */
interface DiagnosticStartResponse {
  already_done: boolean;
  profile: DiagnosticProfileInfo | null;
  strong_suggestion: ChapterSuggestion | null;
  weak_suggestion: ChapterSuggestion | null;
  chapters_by_subject: Record<Subject, string[]> | null;
}

interface QuestionOption {
  label: string;
  text: string;
}

interface QuestionOut {
  id: string;
  subject: Subject;
  chapter: string;
  topic: string;
  content: string;
  question_type: QuestionType;
  options: QuestionOption[];
  difficulty: Difficulty;
}

/** POST /diagnostic/questions — Request */
interface QuestionsRequest {
  subject: Subject;
  chapter: string;
  count?: number; // defaults to 10
}

/** POST /diagnostic/questions — Response */
interface QuestionsResponse {
  questions: QuestionOut[];
}

interface SubmitAttempt {
  question_id: string;
  selected_option: string | null; // null = skipped
  time_taken_secs: number;
}

/** POST /diagnostic/submit — Request */
interface SubmitRequest {
  test_number: 1 | 2;
  subject: Subject;
  chapter: string;
  attempts: SubmitAttempt[];
}

interface ScoreBreakdown {
  correct: number;
  total: number;
}

interface XPResult {
  xp_gained: number;
  new_xp: number;
  old_level: number;
  new_level: number;
  level_up: boolean;
}

/** POST /diagnostic/submit — Response */
interface SubmitResponse {
  score: ScoreBreakdown;
  mastery_score: number; // 0.0 - 1.0
  session_id: string;
  xp_result: XPResult;
}

// ============================================================================
// Common
// ============================================================================

/** Standard error response */
interface ErrorResponse {
  detail: string | ValidationError[];
}

interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

/** GET /health — Response */
interface HealthResponse {
  status: "ok";
}

/** POST /diagnostic/skip — Response */
interface SkipResponse {
  ok: true;
}
```

---

## Quick Reference: All Endpoints

| Method | Path | Auth | Request Body | Response Type |
|---|---|---|---|---|
| `GET` | `/health` | No | — | `HealthResponse` |
| `POST` | `/auth/login` | Yes | — | `UserResponse` |
| `GET` | `/dashboard` | Yes | — | `DashboardResponse` |
| `POST` | `/nova/chat` | Yes | `ChatRequest` | Streamed text |
| `GET` | `/nova/history` | Yes | — | `HistoryResponse` |
| `GET` | `/nova/onboarding-status` | Yes | — | `OnboardingStatusResponse` |
| `POST` | `/diagnostic/start` | Yes | — | `DiagnosticStartResponse` |
| `POST` | `/diagnostic/questions` | Yes | `QuestionsRequest` | `QuestionsResponse` |
| `POST` | `/diagnostic/submit` | Yes | `SubmitRequest` | `SubmitResponse` |
| `POST` | `/diagnostic/skip` | Yes | — | `SkipResponse` |

---

## Typical Frontend User Flow

```
1. Google sign-in via Firebase SDK
2. POST /auth/login → get user info
3. GET /nova/onboarding-status
   ├── Not completed → POST /nova/chat (mode: "ONBOARDING") — conversational onboarding
   │   └── Watch for __NOVA_ONBOARDING_COMPLETE__ sentinel in stream
   └── Completed → continue
4. POST /diagnostic/start
   ├── already_done: true → skip to dashboard
   ├── User chooses to skip → POST /diagnostic/skip
   └── User takes tests:
       ├── POST /diagnostic/questions (strong chapter)
       ├── POST /diagnostic/submit (test_number: 1)
       ├── POST /diagnostic/questions (weak chapter)
       └── POST /diagnostic/submit (test_number: 2)
5. GET /dashboard — main app screen
6. POST /nova/chat (mode: "COMPANION") — ongoing study companion
```
