"""Bật/tắt hiển thị từng thành phần giao diện người dùng (admin chỉnh trong /staff/ui-editor)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class UiVisibility(Base):
    """Chỉ lưu thành phần đã bị chỉnh; không có dòng = hiển thị (mặc định)."""

    __tablename__ = "ui_visibility"
    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
