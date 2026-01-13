from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import Base, engine, get_db
from app.services.context_store import context_store
from app.services.rag_store import rag_store
from app.models import Chat, Message


router = APIRouter(prefix="/api/chats", tags=["chats"])


class ChatOut(BaseModel):
    id: int
    session_id: str
    title: str

    class Config:
        from_attributes = True


class ChatCreate(BaseModel):
    session_id: str = Field(min_length=1)
    title: str = Field(default="New chat", min_length=1)


class MessageOut(BaseModel):
    id: int
    chat_id: int
    role: str
    content: str
    created_at: str

    class Config:
        from_attributes = True


@router.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


@router.get("/", response_model=list[ChatOut])
def list_chats(session_id: str = Query(...), db: Session = Depends(get_db)) -> list[ChatOut]:
    rows = db.query(Chat).filter(Chat.session_id == session_id).order_by(Chat.id.desc()).all()
    return [ChatOut.model_validate(r) for r in rows]


@router.post("/", response_model=ChatOut)
def create_chat(body: ChatCreate, db: Session = Depends(get_db)) -> ChatOut:
    chat = Chat(session_id=body.session_id, title=body.title)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    # Clear any uploaded file context and vector index for this session
    context_store.set_text(body.session_id, "")
    rag_store.clear(body.session_id)
    return ChatOut.model_validate(chat)


@router.delete("/{chat_id}", response_model=ChatOut)
def delete_chat(chat_id: int, db: Session = Depends(get_db)) -> ChatOut:
    chat = db.get(Chat, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    db.delete(chat)
    db.commit()
    return ChatOut.model_validate(chat)


@router.get("/{chat_id}/messages", response_model=list[MessageOut])
def list_messages(chat_id: int, db: Session = Depends(get_db)) -> list[MessageOut]:
    msgs = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )
    return [MessageOut.model_validate({
        "id": m.id,
        "chat_id": m.chat_id,
        "role": m.role,
        "content": m.content,
        "created_at": m.created_at.isoformat(),
    }) for m in msgs]
