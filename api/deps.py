import os
import uuid
from typing import Annotated

import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from fastapi import Header, HTTPException, status
from asgiref.sync import sync_to_async

from apps.users.models import User, UserProfile
from apps.gamification.models import Gamification

# Initialize Firebase Admin SDK (singleton)
if not firebase_admin._apps:
    _cred = credentials.Certificate(
        {
            "type": "service_account",
            "project_id": os.environ["FIREBASE_PROJECT_ID"],
            "private_key": os.environ["FIREBASE_PRIVATE_KEY"].replace("\\n", "\n"),
            "client_email": os.environ["FIREBASE_CLIENT_EMAIL"],
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )
    firebase_admin.initialize_app(_cred)


def _generate_id() -> str:
    return uuid.uuid4().hex[:24]


@sync_to_async
def _get_or_create_user(uid: str, email: str, name: str | None, picture: str | None) -> User:
    user, created = User.objects.get_or_create(
        firebase_uid=uid,
        defaults={
            "id": _generate_id(),
            "email": email,
            "name": name,
            "avatar_url": picture,
        },
    )
    if not created:
        user.updated_at  # touch (auto_now handles it on save)

    # Ensure Gamification record exists
    Gamification.objects.get_or_create(
        user=user,
        defaults={"id": _generate_id()},
    )
    return user


async def get_current_user(authorization: Annotated[str, Header()]) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth header")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        decoded = firebase_auth.verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    uid = decoded["uid"]
    email = decoded.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has no email")

    name = decoded.get("name")
    picture = decoded.get("picture")

    user = await _get_or_create_user(uid, email, name, picture)
    return user
