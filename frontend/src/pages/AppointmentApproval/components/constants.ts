import { AlertTriangle, ShieldCheck, Flame } from 'lucide-react';
import type { ApprovalStatus } from '../api';

/* ───────────────── Status config ────────────────── */

export const STATUS_CONFIG: Record<
  ApprovalStatus,
  { label: string; dot: string; bg: string; text: string; border: string }
> = {
  pending_approval: {
    label: 'Chờ duyệt',
    dot: 'bg-amber-500',
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    border: 'border-amber-200',
  },
  confirmed: {
    label: 'Đã duyệt',
    dot: 'bg-emerald-500',
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
  },
  rejected: {
    label: 'Đã từ chối',
    dot: 'bg-rose-500',
    bg: 'bg-rose-50',
    text: 'text-rose-700',
    border: 'border-rose-200',
  },
  cancelled: {
    label: 'ÄÃ£ há»§y',
    dot: 'bg-slate-500',
    bg: 'bg-slate-50',
    text: 'text-slate-700',
    border: 'border-slate-200',
  },
  expired: {
    label: 'ÄÃ£ háº¿t háº¡n',
    dot: 'bg-orange-500',
    bg: 'bg-orange-50',
    text: 'text-orange-700',
    border: 'border-orange-200',
  },
};

/* ───────────────── Risk config ────────────────── */

export const RISK_CONFIG: Record<
  string,
  { label: string; bg: string; text: string; icon: typeof Flame }
> = {
  critical: { label: 'Cấp cứu', bg: 'bg-rose-100', text: 'text-rose-700', icon: Flame },
  high:     { label: 'Cao',     bg: 'bg-amber-100', text: 'text-amber-700', icon: AlertTriangle },
  medium:   { label: 'Trung bình', bg: 'bg-sky-100',    text: 'text-sky-700',    icon: AlertTriangle },
  low:      { label: 'Thấp',       bg: 'bg-slate-100',  text: 'text-slate-600',  icon: ShieldCheck },
};

/* ───────────────── Types ────────────────── */

export type TabFilter = 'all' | ApprovalStatus;

export interface BookingCounts {
  all: number;
  pending_approval: number;
  confirmed: number;
  rejected: number;
  cancelled: number;
  expired: number;
}

/* ───────────────── Format helpers ────────────────── */

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('vi-VN', {
    weekday: 'long',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

export function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return 'Vừa xong';
  if (minutes < 60) return `${minutes} phút trước`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} giờ trước`;
  return `${Math.floor(hours / 24)} ngày trước`;
}
