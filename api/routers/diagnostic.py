import uuid
import random
from typing import Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from asgiref.sync import sync_to_async

from api.deps import get_current_user
from api.schemas.diagnostic import (
    DiagnosticStartResponse,
    ProfileInfo,
    ChapterSuggestion,
    QuestionsRequest,
    QuestionsResponse,
    QuestionOut,
    QuestionOption,
    SubmitRequest,
    SubmitResponse,
)
from api.services.diagnostic.chapter_suggestions import (
    JEE_CHAPTERS,
    get_suggested_strong_chapter,
    get_suggested_weak_chapter,
)
from api.services.diagnostic.mastery_calculator import AttemptSummary, calculate_mastery_score, PRIOR_MASTERY
from api.services.gamification.xp_engine import award_xp
from apps.users.models import User

router = APIRouter()


# ─── START ─────────────────────────────────────────────────────────────────────

@sync_to_async
def _start_diagnostic(user: User) -> dict:
    from apps.diagnostic.models import DiagnosticSession, DiagnosticStatus
    from apps.users.models import UserProfile

    existing = DiagnosticSession.objects.filter(user=user).first()
    if existing and existing.status in (DiagnosticStatus.COMPLETED, DiagnosticStatus.SKIPPED):
        return {"already_done": True}

    profile = UserProfile.objects.filter(user=user).first()
    strong_subjects = list(profile.strong_subjects) if profile else []
    weak_subjects = list(profile.weak_subjects) if profile else []

    if not existing:
        DiagnosticSession.objects.create(
            id=uuid.uuid4().hex[:24],
            user=user,
        )

    return {
        "already_done": False,
        "name": user.name,
        "exam_attempt_date": profile.exam_attempt_date if profile else None,
        "strong_subjects": strong_subjects,
        "weak_subjects": weak_subjects,
        "previous_score": profile.previous_score if profile else None,
        "daily_study_hours": profile.daily_study_hours if profile else None,
    }


@router.post("/start", response_model=DiagnosticStartResponse)
async def start_diagnostic(user: Annotated[User, Depends(get_current_user)]):
    data = await _start_diagnostic(user)

    if data["already_done"]:
        return DiagnosticStartResponse(already_done=True)

    strong_suggestion = get_suggested_strong_chapter(data["strong_subjects"])
    weak_suggestion = get_suggested_weak_chapter(data["weak_subjects"])

    return DiagnosticStartResponse(
        already_done=False,
        profile=ProfileInfo(
            name=data["name"],
            exam_attempt_date=data["exam_attempt_date"],
            strong_subjects=data["strong_subjects"],
            weak_subjects=data["weak_subjects"],
            previous_score=data["previous_score"],
            daily_study_hours=data["daily_study_hours"],
        ),
        strong_suggestion=ChapterSuggestion(**strong_suggestion) if strong_suggestion else None,
        weak_suggestion=ChapterSuggestion(**weak_suggestion) if weak_suggestion else None,
        chapters_by_subject={k: v for k, v in JEE_CHAPTERS.items()},
    )


# ─── QUESTIONS ──────────────────────────────────────────────────────────────────

@sync_to_async
def _fetch_questions(subject: str, chapter: str, count: int) -> list:
    from apps.questions.models import Question
    qs = list(Question.objects.filter(subject=subject, chapter=chapter))
    if not qs:
        return []
    random.shuffle(qs)
    selected = qs[:count]
    # Also shuffle options for each MCQ
    for q in selected:
        if isinstance(q.options, list) and q.options:
            random.shuffle(q.options)
    return selected


@router.post("/questions", response_model=QuestionsResponse)
async def get_questions(
    request: QuestionsRequest,
    user: Annotated[User, Depends(get_current_user)],
):
    valid_subjects = list(JEE_CHAPTERS.keys())
    if request.subject not in valid_subjects:
        raise HTTPException(status_code=400, detail="Invalid subject")

    questions = await _fetch_questions(request.subject, request.chapter, request.count)
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found for this chapter")

    return QuestionsResponse(
        questions=[
            QuestionOut(
                id=q.id,
                subject=q.subject,
                chapter=q.chapter,
                topic=q.topic,
                content=q.content,
                question_type=q.question_type,
                options=[QuestionOption(**o) for o in (q.options or [])],
                difficulty=q.difficulty,
            )
            for q in questions
        ]
    )


# ─── SUBMIT ─────────────────────────────────────────────────────────────────────

@sync_to_async
def _submit_diagnostic(user_id: str, req: SubmitRequest) -> dict:
    from apps.questions.models import Question
    from apps.practice.models import PracticeSession
    from apps.questions.models import QuestionAttempt
    from apps.analytics.models import TopicProgress
    from apps.diagnostic.models import DiagnosticSession, DiagnosticStatus

    question_ids = [a.question_id for a in req.attempts]
    questions = {
        q.id: q
        for q in Question.objects.filter(id__in=question_ids).only(
            "id", "topic", "correct_option", "difficulty"
        )
    }

    graded = []
    for attempt in req.attempts:
        q = questions.get(attempt.question_id)
        is_correct = (
            attempt.selected_option is not None
            and q is not None
            and q.correct_option == attempt.selected_option
        )
        graded.append({
            "question_id": attempt.question_id,
            "selected_option": attempt.selected_option,
            "is_correct": is_correct,
            "time_taken_secs": attempt.time_taken_secs,
            "topic": q.topic if q else "Unknown",
            "difficulty": q.difficulty if q else "MEDIUM",
        })

    correct_count = sum(1 for g in graded if g["is_correct"])
    total_duration = sum(g["time_taken_secs"] for g in graded)

    session = PracticeSession.objects.create(
        id=uuid.uuid4().hex[:24],
        user_id=user_id,
        subject=req.subject,
        chapter=req.chapter,
        mode="ADAPTIVE",
        total_questions=len(req.attempts),
        completed_at=datetime.now(tz=timezone.utc),
        duration_secs=total_duration,
        xp_earned=50 + correct_count * 3,
    )

    QuestionAttempt.objects.bulk_create([
        QuestionAttempt(
            id=uuid.uuid4().hex[:24],
            user_id=user_id,
            session=session,
            question_id=g["question_id"],
            selected_option=g["selected_option"],
            is_correct=g["is_correct"],
            time_taken_secs=g["time_taken_secs"],
        )
        for g in graded
    ])

    # Calculate mastery for the tested chapter
    attempt_summaries = [
        AttemptSummary(
            is_correct=g["is_correct"],
            time_taken_secs=g["time_taken_secs"],
            difficulty=g["difficulty"],
        )
        for g in graded
        if g["selected_option"] is not None
    ]

    mastery_score = calculate_mastery_score(attempt_summaries) if attempt_summaries else 0.0
    total_attempted = len(attempt_summaries)
    avg_time = (
        sum(a.time_taken_secs for a in attempt_summaries) / total_attempted
        if total_attempted else 0
    )

    # Upsert TopicProgress for tested chapter
    try:
        tp = TopicProgress.objects.get(
            user_id=user_id,
            subject=req.subject,
            chapter=req.chapter,
            topic=req.chapter,
        )
        tp.mastery_score = mastery_score
        tp.total_attempted = total_attempted
        tp.total_correct = correct_count
        tp.avg_time_secs = avg_time
        tp.last_attempted = datetime.now(tz=timezone.utc)
        tp.is_unlocked = True
        tp.save()
    except TopicProgress.DoesNotExist:
        TopicProgress.objects.create(
            id=uuid.uuid4().hex[:24],
            user_id=user_id,
            subject=req.subject,
            chapter=req.chapter,
            topic=req.chapter,
            mastery_score=mastery_score,
            total_attempted=total_attempted,
            total_correct=correct_count,
            avg_time_secs=avg_time,
            last_attempted=datetime.now(tz=timezone.utc),
            is_unlocked=True,
        )

    # Update DiagnosticSession
    diag = DiagnosticSession.objects.filter(user_id=user_id).first()
    if diag:
        if req.test_number == 1:
            diag.test1_session_id = session.id
            diag.test1_subject = req.subject
            diag.test1_chapter = req.chapter
            diag.status = DiagnosticStatus.TEST1_COMPLETE
        else:
            diag.test2_session_id = session.id
            diag.test2_subject = req.subject
            diag.test2_chapter = req.chapter
            diag.status = DiagnosticStatus.COMPLETED
            diag.completed_at = datetime.now(tz=timezone.utc)
        diag.save()

    # If test 2 complete, write prior estimates for untested chapters
    if req.test_number == 2:
        from apps.users.models import UserProfile
        profile = UserProfile.objects.filter(user_id=user_id).first()
        strong_subjects = list(profile.strong_subjects) if profile else []
        weak_subjects = list(profile.weak_subjects) if profile else []

        tested_chapters = {diag.test1_chapter, req.chapter} if diag and diag.test1_chapter else {req.chapter}

        for subj, chapters in JEE_CHAPTERS.items():
            for ch in chapters:
                if ch in tested_chapters:
                    continue
                if subj in strong_subjects:
                    prior = PRIOR_MASTERY["STRONG_SUBJECT"]
                elif subj in weak_subjects:
                    prior = PRIOR_MASTERY["WEAK_SUBJECT"]
                else:
                    prior = PRIOR_MASTERY["UNKNOWN"]

                TopicProgress.objects.get_or_create(
                    user_id=user_id,
                    subject=subj,
                    chapter=ch,
                    topic=ch,
                    defaults={
                        "id": uuid.uuid4().hex[:24],
                        "mastery_score": prior,
                        "total_attempted": 0,
                        "total_correct": 0,
                        "avg_time_secs": 0,
                        "is_unlocked": False,
                    },
                )

    return {
        "correct_count": correct_count,
        "total": len(req.attempts),
        "mastery_score": mastery_score,
        "session_id": session.id,
        "xp_override": 50 + correct_count * 3,
    }


@router.post("/submit", response_model=SubmitResponse)
async def submit_diagnostic(
    request: SubmitRequest,
    user: Annotated[User, Depends(get_current_user)],
):
    if request.test_number not in (1, 2):
        raise HTTPException(status_code=400, detail="test_number must be 1 or 2")
    if not request.attempts:
        raise HTTPException(status_code=400, detail="attempts cannot be empty")

    result = await _submit_diagnostic(user.id, request)
    xp_result = await award_xp(
        user.id,
        "DIAGNOSTIC_COMPLETE",
        xp_override=result["xp_override"],
        reference_id=result["session_id"],
    )

    return SubmitResponse(
        score={"correct": result["correct_count"], "total": result["total"]},
        mastery_score=result["mastery_score"],
        session_id=result["session_id"],
        xp_result=xp_result,
    )


# ─── SKIP ───────────────────────────────────────────────────────────────────────

@sync_to_async
def _skip_diagnostic(user_id: str) -> None:
    from apps.diagnostic.models import DiagnosticSession, DiagnosticStatus
    from apps.analytics.models import TopicProgress
    from apps.users.models import UserProfile

    DiagnosticSession.objects.update_or_create(
        user_id=user_id,
        defaults={
            "id": uuid.uuid4().hex[:24],
            "status": DiagnosticStatus.SKIPPED,
            "skipped": True,
        },
    )

    profile = UserProfile.objects.filter(user_id=user_id).first()
    strong_subjects = list(profile.strong_subjects) if profile else []
    weak_subjects = list(profile.weak_subjects) if profile else []

    for subj, chapters in JEE_CHAPTERS.items():
        if subj in strong_subjects:
            prior = PRIOR_MASTERY["STRONG_SUBJECT"]
        elif subj in weak_subjects:
            prior = PRIOR_MASTERY["WEAK_SUBJECT"]
        else:
            prior = PRIOR_MASTERY["UNKNOWN"]

        for ch in chapters:
            TopicProgress.objects.get_or_create(
                user_id=user_id,
                subject=subj,
                chapter=ch,
                topic=ch,
                defaults={
                    "id": uuid.uuid4().hex[:24],
                    "mastery_score": prior,
                    "total_attempted": 0,
                    "total_correct": 0,
                    "avg_time_secs": 0,
                    "is_unlocked": False,
                },
            )


@router.post("/skip")
async def skip_diagnostic(user: Annotated[User, Depends(get_current_user)]):
    await _skip_diagnostic(user.id)
    return {"ok": True}
