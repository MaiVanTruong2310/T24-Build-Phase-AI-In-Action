import { useEffect } from 'react'
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import type { AppDispatch } from './app/store'
import { initializeAuth, logout, sessionChanged } from './features/auth/authSlice'
import { AUTH_SESSION_KEY, readPublishedSession } from './features/auth/session'
import { PatientLayout, RootLayout, StaffLayout, AuthLayout } from './layouts'
import { Landing } from './pages/Landing'
import { Login } from './pages/Login'
import { Register } from './pages/Register'
import { ForgotPassword } from './pages/ForgotPassword'
import EmergencyCoordinator from './pages/EmergencyCoordinator'
import AppointmentBooking from './pages/AppointmentBooking'
import AppointmentHistory from './pages/AppointmentHistory'
import AppointmentProgress from './pages/AppointmentProgress'
import AppointmentDetail from './pages/AppointmentDetail'
import DoctorManagement from './pages/DoctorManagement'
import CreateDoctor from './pages/DoctorManagement/Create'
import ServiceManagement from './pages/ServiceManagement'
import CreateService from './pages/ServiceManagement/Create'
import ScheduleApprove from './pages/ScheduleApprove'
import AppointmentApproval from './pages/AppointmentApproval'
import DoctorSchedule from './pages/DoctorSchedule'
import PatientProfile from './pages/PatientProfile'
import PatientDepartments from './pages/PatientDepartments'
import PatientConsultation from './pages/PatientConsultation'
import ChatTakeover from './pages/ChatTakeover'
import StaffDashboard from './pages/StaffDashboard'

function Placeholder({ title, description }: { title: string; description: string }) {
  return (
    <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wider text-sky-600">MediCare AI</p>
      <h1 className="mt-2 text-2xl font-bold text-slate-900">{title}</h1>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{description}</p>
    </section>
  )
}

const router = createBrowserRouter([
  { path: '/', element: <Landing /> },
  {
    element: <AuthLayout />,
    children: [
      { path: '/login', element: <Login /> },
      { path: '/register', element: <Register /> },
      { path: '/forgot-password', element: <ForgotPassword /> },
    ]
  },
  // Standalone Patient Profile Page (renders full-bleed layout with its own header & footer)
  { path: '/patient/profile', element: <PatientProfile /> },
  { path: '/patient/records', element: <Navigate to="/patient/profile" replace /> },
  {
    element: <RootLayout />,
    children: [
      {
        path: 'patient',
        element: <PatientLayout />,
        children: [
          { index: true, element: <PatientConsultation /> },
          { path: 'profile', element: <PatientProfile /> },
          { path: 'records', element: <PatientProfile /> },
          { path: 'departments', element: <PatientDepartments /> },
          { path: 'appointments', element: <AppointmentBooking /> },
          { path: 'appointments/history', element: <AppointmentHistory /> },
          { path: 'progress', element: <AppointmentProgress /> },
          { path: 'appointments/:id', element: <AppointmentDetail /> }
        ]
      }
    ]
  },
  {
    path: 'staff',
    element: <StaffLayout />,
    children: [
      { index: true, element: <StaffDashboard /> },
      { path: 'overview', element: <StaffDashboard /> },
      { path: 'queue', element: <EmergencyCoordinator /> },
      { path: 'chat', element: <ChatTakeover /> },
      { path: 'doctors', element: <DoctorManagement /> },
      { path: 'doctors/create', element: <CreateDoctor /> },
      { path: 'services', element: <ServiceManagement /> },
      { path: 'services/create', element: <CreateService /> },
      { path: 'appointments', element: <AppointmentApproval /> },
      { path: 'appointments/approve/:id', element: <ScheduleApprove /> },
      { path: 'doctor-schedule', element: <DoctorSchedule /> },
      { path: 'patients', element: <Placeholder title="Quản lý bệnh nhân" description="Page quản lý bệnh nhân sẽ được bổ sung sau." /> },
      { path: 'monitoring', element: <Placeholder title="Giám sát hệ thống" description="Page giám sát hệ thống sẽ được bổ sung sau." /> }
    ]
  }
])

export function App() {
  const dispatch = useDispatch<AppDispatch>()

  useEffect(() => {
    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === AUTH_SESSION_KEY) {
        dispatch(sessionChanged(readPublishedSession()))
      }
    }
    const handleUnauthorized = () => dispatch(logout())

    window.addEventListener('storage', handleStorageChange)
    window.addEventListener('auth:unauthorized', handleUnauthorized)
    void dispatch(initializeAuth())

    return () => {
      window.removeEventListener('storage', handleStorageChange)
      window.removeEventListener('auth:unauthorized', handleUnauthorized)
    }
  }, [dispatch])

  return <RouterProvider router={router} />
}
