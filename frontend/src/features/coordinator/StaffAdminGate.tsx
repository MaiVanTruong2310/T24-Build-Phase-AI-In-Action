import type { ReactNode } from 'react'
import { Navigate, useOutletContext } from 'react-router-dom'
import { canAdminister, type Member } from './api'

export function StaffAdminGate({ children }: { children: ReactNode }) {
  const { member } = useOutletContext<{ member: Member }>()
  return canAdminister(member) ? <>{children}</> : <Navigate to="/staff/queue" replace />
}
