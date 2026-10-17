import { Outlet } from 'react-router-dom'

export function PatientLayout() {
  return (
    <div className="patient-theme h-full w-full">
      <Outlet />
    </div>
  )
}
