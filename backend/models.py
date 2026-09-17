from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from config import moscow_now
import enum
from database import Base


class UserRole(str, enum.Enum):
    WORKER = "worker"
    MANAGER = "manager"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    password_plain = Column(String(100), nullable=True)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), default=UserRole.WORKER)
    block = Column(String(30), nullable=True)
    created_at = Column(DateTime, default=moscow_now)

    works = relationship("Work", back_populates="worker")


class Work(Base):
    __tablename__ = "works"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    part_number = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    note = Column(String(500), default="")
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=moscow_now)
    synced = Column(Integer, default=1)  # 1=server, 0=needs sync

    worker = relationship("User", back_populates="works")


class SpecOrder(Base):
    __tablename__ = "spec_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    source_file = Column(String(255), default="")
    status = Column(String(20), default="open")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=moscow_now)
    ready_at = Column(DateTime, nullable=True)  # время перевода в архив «готов»

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("spec_orders.id"), nullable=False, index=True)
    part_number = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    thickness = Column(Float, nullable=True)
    steel_grade = Column(String(100), default="")
    route = Column(String(200), default="")
    needs_bending = Column(Integer, default=1)

    order = relationship("SpecOrder", back_populates="items")
    completions = relationship(
        "OrderItemCompletion", back_populates="item", cascade="all, delete-orphan"
    )
    claims = relationship(
        "OrderItemClaim", back_populates="item", cascade="all, delete-orphan"
    )


class OrderItemClaim(Base):
    """Гибщик «взял деталь в работу»: кто, когда взял и когда завершил исполнение."""

    __tablename__ = "order_item_claims"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    claimed_at = Column(DateTime, default=moscow_now)
    completed_at = Column(DateTime, nullable=True)

    item = relationship("OrderItem", back_populates="claims")
    worker = relationship("User")
    participants = relationship("OrderItemClaimWorker", back_populates="claim",
                                cascade="all, delete-orphan")


class OrderItemClaimWorker(Base):
    """Соисполнители бригады по заявке: основной гибщик + добавленные гибщики.

    status: pending — приглашение отправлено, accepted — согласился, declined — отказался.
    """

    __tablename__ = "order_item_claim_workers"
    __table_args__ = (UniqueConstraint("claim_id", "worker_id", name="uq_claim_worker"),)

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("order_item_claims.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    invited_at = Column(DateTime, default=moscow_now)
    responded_at = Column(DateTime, nullable=True)

    claim = relationship("OrderItemClaim", back_populates="participants")
    worker = relationship("User", foreign_keys=[worker_id])


class OrderItemCompletion(Base):
    __tablename__ = "order_item_completions"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False, index=True)
    executor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    marked_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    note = Column(String(500), default="")
    completed_at = Column(DateTime, default=moscow_now)
    stage = Column(String(20), default="bender", nullable=False)

    item = relationship("OrderItem", back_populates="completions")


class Chat(Base):
    """Чат: канал (channel), личка (dm) или свой групповой (group)."""

    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(20), default="group", nullable=False)
    name = Column(String(100), nullable=True)
    block = Column(String(30), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=moscow_now)

    members = relationship("ChatMember", back_populates="chat",
                           cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="chat",
                            cascade="all, delete-orphan")


class ChatMember(Base):
    """Участник чата. role: member / creator (создатель своего чата)."""

    __tablename__ = "chat_members"
    __table_args__ = (UniqueConstraint("chat_id", "user_id", name="uq_chat_member"),)

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(20), default="member", nullable=False)
    joined_at = Column(DateTime, default=moscow_now)

    chat = relationship("Chat", back_populates="members")
    user = relationship("User")


class ChatMessage(Base):
    """Сообщение в чате."""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(String(4000), nullable=False)
    created_at = Column(DateTime, default=moscow_now)
    edited_at = Column(DateTime, nullable=True)
    deleted = Column(Integer, default=0)

    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User")


class ChatRead(Base):
    """Последнее прочитанное сообщение по чату для подсчёта непрочитанных."""

    __tablename__ = "chat_reads"
    __table_args__ = (UniqueConstraint("chat_id", "user_id", name="uq_chat_read"),)

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    last_message_id = Column(Integer, default=0, nullable=False)
