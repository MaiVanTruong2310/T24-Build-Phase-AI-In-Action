import { Outlet } from 'react-router-dom'

export function PatientLayout() {
  return (
    <div className="patient-theme w-full">
      <Outlet />
    </div>
  )
}
