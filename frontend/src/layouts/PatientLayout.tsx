import { Outlet } from 'react-router-dom'

export function PatientLayout() {
  return (
    <div className="w-full">
      <Outlet />
    </div>
  )
}
