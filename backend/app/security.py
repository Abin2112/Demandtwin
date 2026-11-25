import hashlib
import secrets
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Annotated

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pwdlib import PasswordHash
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import RESEARCH_CODE, SECURE_COOKIES, jwt_secret
from .db import Login, User, session
from .schemas import Credentials, Registration

router = APIRouter(prefix="/auth", tags=["auth"])
DB = Annotated[Session, Depends(session)]
ACCESS = 900
REFRESH = 7 * 24 * 3600
PASSWORD = PasswordHash.recommended()
DUMMY = PASSWORD.hash(secrets.token_urlsafe(32))
SECRET = jwt_secret()
AUTH_ATTEMPTS = defaultdict(deque)
RATE_LOCK = Lock()


def rate_limit(request: Request):
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with RATE_LOCK:
        if len(AUTH_ATTEMPTS) >= 10000:
            for address in list(AUTH_ATTEMPTS):
                if AUTH_ATTEMPTS[address][-1] < now - 60:
                    del AUTH_ATTEMPTS[address]
        if key not in AUTH_ATTEMPTS and len(AUTH_ATTEMPTS) >= 10000:
            raise HTTPException(429, "Try again in one minute")
        times = AUTH_ATTEMPTS[key]
        while times and times[0] < now - 60:
            times.popleft()
        if len(times) >= 30:
            raise HTTPException(429, "Try again in one minute")
        times.append(now)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def identity(user):
    return {"id": user.id, "email": user.email, "role": user.role}


def issue(db, user, response):
    now = int(time.time())
    refresh = secrets.token_urlsafe(48)
    login = Login(user_id=user.id, digest=digest(refresh), expires=now + REFRESH)
    db.add(login)
    db.flush()
    access = jwt.encode({"sub": user.id, "sid": login.id, "exp": now + ACCESS, "iss": "demandtwin"}, SECRET, algorithm="HS256")
    db.commit()
    response.set_cookie("dt_access", access, max_age=ACCESS, httponly=True, secure=SECURE_COOKIES, samesite="strict", path="/api/v1")
    response.set_cookie("dt_refresh", refresh, max_age=REFRESH, httponly=True, secure=SECURE_COOKIES, samesite="strict", path="/api/v1/auth")
    return identity(user)


def current(db: DB, dt_access: Annotated[str | None, Cookie()] = None):
    try:
        claims = jwt.decode(dt_access or "", SECRET, algorithms=["HS256"], issuer="demandtwin", options={"require": ["exp", "sub", "sid"]})
    except jwt.PyJWTError:
        raise HTTPException(401, "Sign in to continue") from None
    login = db.get(Login, claims["sid"])
    if not login or login.user_id != claims["sub"] or login.expires <= time.time():
        raise HTTPException(401, "Session expired")
    return db.get(User, login.user_id)


Actor = Annotated[User, Depends(current)]


def researcher(user: Actor):
    if user.role != "researcher":
        raise HTTPException(403, "Researcher access required")
    return user


Researcher = Annotated[User, Depends(researcher)]


@router.post("/register", status_code=201, dependencies=[Depends(rate_limit)])
def register(body: Registration, response: Response, db: DB):
    role = "founder"
    if body.research_code:
        if not RESEARCH_CODE or not secrets.compare_digest(digest(RESEARCH_CODE), digest(body.research_code)):
            raise HTTPException(403, "Invalid research registration code")
        role = "researcher"
    user = User(email=body.email, password_hash=PASSWORD.hash(body.password), role=role)
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Account already exists") from None
    return issue(db, user, response)


@router.post("/login", dependencies=[Depends(rate_limit)])
def login(body: Credentials, response: Response, db: DB):
    user = db.scalar(select(User).where(User.email == body.email))
    if not PASSWORD.verify(body.password, user.password_hash if user else DUMMY) or user is None:
        raise HTTPException(401, "Invalid credentials")
    return issue(db, user, response)


@router.post("/refresh")
def refresh(response: Response, db: DB, dt_refresh: Annotated[str | None, Cookie()] = None):
    if not dt_refresh:
        raise HTTPException(401, "Session expired")
    user_id = db.scalar(delete(Login).where(Login.digest == digest(dt_refresh), Login.expires > int(time.time())).returning(Login.user_id))
    if user_id is None:
        raise HTTPException(401, "Session expired")
    return issue(db, db.get(User, user_id), response)


@router.post("/logout", status_code=204)
def logout(response: Response, db: DB, dt_refresh: Annotated[str | None, Cookie()] = None):
    if dt_refresh:
        db.execute(delete(Login).where(Login.digest == digest(dt_refresh)))
        db.commit()
    response.delete_cookie("dt_access", path="/api/v1", secure=SECURE_COOKIES, httponly=True, samesite="strict")
    response.delete_cookie("dt_refresh", path="/api/v1/auth", secure=SECURE_COOKIES, httponly=True, samesite="strict")


@router.get("/me")
def me(user: Actor):
    return identity(user)
