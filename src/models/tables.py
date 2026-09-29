from datetime import date, datetime, time
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Table,
    Text,
    Time,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship as orm_relationship

from src.database import Base

# ==========================================
# 0. Enums & Bảng trung gian (Association)
# ==========================================


class AppointmentStatus(str, Enum):  # noqa: UP042
    PENDING_PAYMENT = "pending_payment"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):  # noqa: UP042
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


# Bảng trung gian n-n: facility_services
facility_services = Table(
    "facility_services",
    Base.metadata,
    Column(
        "facility_id",
        ForeignKey("facilities.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "service_id",
        ForeignKey("services.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


# ==========================================
# 1. Nhóm Tài khoản & Hồ sơ
# ==========================================


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    patient_profiles: Mapped[list["PatientProfile"]] = orm_relationship(
        "PatientProfile", back_populates="user", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["Appointment"]] = orm_relationship("Appointment", back_populates="user")


class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    relationship: Mapped[str | None] = mapped_column(String(50), nullable=True)
    medical_history: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = orm_relationship("User", back_populates="patient_profiles")
    appointments: Mapped[list["Appointment"]] = orm_relationship("Appointment", back_populates="patient_profile")


# ==========================================
# 2. Nhóm Cơ sở & Nhân sự
# ==========================================


class Facility(Base):
    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    hotline: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    doctors: Mapped[list["Doctor"]] = orm_relationship(
        "Doctor", back_populates="facility", cascade="all, delete-orphan"
    )
    services: Mapped[list["Service"]] = orm_relationship(
        "Service", secondary=facility_services, back_populates="facilities"
    )
    appointments: Mapped[list["Appointment"]] = orm_relationship("Appointment", back_populates="facility")


class Specialty(Base):
    __tablename__ = "specialties"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    doctors: Mapped[list["Doctor"]] = orm_relationship("Doctor", back_populates="specialty")


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    facility_id: Mapped[int] = mapped_column(
        ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    specialty_id: Mapped[int] = mapped_column(
        ForeignKey("specialties.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    facility: Mapped["Facility"] = orm_relationship("Facility", back_populates="doctors")
    specialty: Mapped["Specialty"] = orm_relationship("Specialty", back_populates="doctors")
    schedules: Mapped[list["DoctorSchedule"]] = orm_relationship(
        "DoctorSchedule", back_populates="doctor", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["Appointment"]] = orm_relationship("Appointment", back_populates="doctor")


# ==========================================
# 3. Nhóm Dịch vụ
# ==========================================


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    facilities: Mapped[list["Facility"]] = orm_relationship(
        "Facility", secondary=facility_services, back_populates="services"
    )
    appointments: Mapped[list["Appointment"]] = orm_relationship("Appointment", back_populates="service")


# ==========================================
# 4. Nhóm Lịch hẹn & Giao dịch
# ==========================================


class DoctorSchedule(Base):
    __tablename__ = "doctor_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_booked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    doctor: Mapped["Doctor"] = orm_relationship("Doctor", back_populates="schedules")
    appointments: Mapped[list["Appointment"]] = orm_relationship("Appointment", back_populates="schedule")


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_profile_id: Mapped[int] = mapped_column(
        ForeignKey("patient_profiles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    facility_id: Mapped[int] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    doctor_id: Mapped[int | None] = mapped_column(
        ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True, index=True
    )
    schedule_id: Mapped[int | None] = mapped_column(
        ForeignKey("doctor_schedules.id", ondelete="SET NULL"), nullable=True, index=True
    )
    service_id: Mapped[int | None] = mapped_column(
        ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True
    )
    appointment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    time_slot: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        SQLEnum(AppointmentStatus, name="appointment_status_enum", native_enum=False),
        default=AppointmentStatus.PENDING_PAYMENT,
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = orm_relationship("User", back_populates="appointments")
    patient_profile: Mapped["PatientProfile"] = orm_relationship("PatientProfile", back_populates="appointments")
    facility: Mapped["Facility"] = orm_relationship("Facility", back_populates="appointments")
    doctor: Mapped[Optional["Doctor"]] = orm_relationship("Doctor", back_populates="appointments")
    schedule: Mapped[Optional["DoctorSchedule"]] = orm_relationship("DoctorSchedule", back_populates="appointments")
    service: Mapped[Optional["Service"]] = orm_relationship("Service", back_populates="appointments")
    payments: Mapped[list["Payment"]] = orm_relationship(
        "Payment", back_populates="appointment", cascade="all, delete-orphan"
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    payment_status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus, name="payment_status_enum", native_enum=False),
        default=PaymentStatus.PENDING,
        nullable=False,
    )
    transaction_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)

    # Relationships
    appointment: Mapped["Appointment"] = orm_relationship("Appointment", back_populates="payments")
