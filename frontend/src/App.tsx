import { TypewriterLoader } from './components/TypewriterLoader';
import { lazy, Suspense, useEffect, type ReactNode } from 'react'
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import type { AppDispatch, RootState } from './app/store'
import { initializeAuth, logout, sessionChanged } from './features/auth/authSlice'
import {
  ACCESS_TOKEN_KEY,
  AUTH_SESSION_KEY,
  AUTH_TOKENS_UPDATED_EVENT,
  REFRESH_TOKEN_KEY,
  readPublishedSession,
} from './features/auth/session'
import { PatientLayout } from './layouts/PatientLayout'
import { RootLayout } from './layouts/RootLayout'

const AuthLayout = lazy(() => import('./layouts/AuthLayout').then((module) => ({ default: module.AuthLayout })))
const StaffLayout = lazy(() => import('./layouts/StaffLayout').then((module) => ({ default: module.StaffLayout })))
const Landing = lazy(() => import('./pages/Landing').then((module) => ({ default: module.Landing })))
const Login = lazy(() => import('./pages/Login').then((module) => ({ default: module.Login })))
const Register = lazy(() => import('./pages/Register').then((module) => ({ default: module.Register })))
const ForgotPassword = lazy(() => import('./pages/ForgotPassword').then((module) => ({ default: module.ForgotPassword })))
const CoordinatorWorkbench = lazy(() => import('./pages/CoordinatorWorkbench'))
const PatientCoordinationRequests = lazy(() => import('./pages/PatientCoordinationRequests'))
const ConsultationBooking = lazy(() => import('./pages/ConsultationBooking'))
const DoctorDirectory = lazy(() => import('./pages/DoctorDirectory'))
const DoctorProfile = lazy(() => import('./pages/DoctorProfile'))
const CoordinatorSchedule = lazy(() => import('./pages/CoordinatorSchedule'))
const AppointmentHistory = lazy(() => import('./pages/AppointmentHistory'))
const AppointmentProgress = lazy(() => import('./pages/AppointmentProgress'))
const AppointmentDetail = lazy(() => import('./pages/AppointmentDetail'))
const DoctorManagement = lazy(() => import('./pages/DoctorManagement'))
const CreateDoctor = lazy(() => import('./pages/DoctorManagement/Create'))
const ServiceManagement = lazy(() => import('./pages/ServiceManagement'))
const CreateService = lazy(() => import('./pages/ServiceManagement/Create'))


const DoctorSchedule = lazy(() => import('./pages/DoctorSchedule'))
const PatientProfile = lazy(() => import('./pages/PatientProfile'))
const PatientDepartments = lazy(() => import('./pages/PatientDepartments'))
const PatientConsultation = lazy(() => import('./pages/PatientConsultation'))



function Placeholder({ title, description }: { title: string; description: string }) {
  return (
    <section className="rounded-2xl border border-dashed border-slate-300 light:border-app-border bg-white light:bg-app-surface p-8 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wider text-sky-600 light:text-app-primary">VCare+</p>
      <h1 className="mt-2 text-2xl font-bold text-slate-900 light:text-app-text">{title}</h1>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 light:text-app-secondary">{description}</p>
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
  { path: '/patient/profile', element: <PatientAuthGate><PatientProfile /></PatientAuthGate> },
  { path: '/patient/records', element: <Navigate to="/patient/profile" replace /> },
  {
    element: <RootLayout />,
    children: [
      {
        path: 'patient',
        element: <PatientLayout />,
        children: [
          { index: true, element: <PatientConsultation /> },
          { path: 'profile', element: <PatientAuthGate><PatientProfile /></PatientAuthGate> },
          { path: 'records', element: <Navigate to="/patient/profile" replace /> },
          { path: 'departments', element: <PatientDepartments /> },
          { path: 'appointments', element: <ConsultationBooking /> },
          { path: 'requests', element: <PatientCoordinationRequests /> },
          { path: 'doctors', element: <DoctorDirectory /> },
          { path: 'doctors/:id', element: <DoctorProfile /> },
          { path: 'appointments/history', element: <AppointmentHistory /> },
          { path: 'progress', element: <PatientAuthGate><AppointmentProgress /></PatientAuthGate> },
          { path: 'appointments/:id', element: <AppointmentDetail /> }
        ]
      }
    ]
  },
  {
    path: 'staff',
    element: <StaffGate />,
    children: [
      { index: true, element: <CoordinatorWorkbench mode="dashboard" /> },
      { path: 'overview', element: <CoordinatorWorkbench mode="dashboard" /> },
      { path: 'dieu-phoi', element: <CoordinatorWorkbench /> },
      { path: 'shifts', element: <CoordinatorSchedule /> },
      { path: 'settings', element: <CoordinatorWorkbench mode="settings" /> },
      { path: 'queue', element: <CoordinatorWorkbench /> },
      { path: 'emergency', element: <CoordinatorWorkbench mode="emergency" /> },
      { path: 'chat', element: <CoordinatorWorkbench mode="chat" /> },
      { path: 'doctors', element: <DoctorManagement /> },
      { path: 'doctors/create', element: <CreateDoctor /> },
      { path: 'doctors/:id/edit', element: <CreateDoctor /> },
      { path: 'services', element: <ServiceManagement /> },
      { path: 'services/create', element: <CreateService /> },
      { path: 'appointments', element: <CoordinatorWorkbench /> },
      { path: 'appointments/approve/:id', element: <Navigate to="/staff/queue" replace /> },
      { path: 'doctor-schedule', element: <DoctorSchedule /> },
      { path: 'patients', element: <Placeholder title="Quản lý bệnh nhân" description="Page quản lý bệnh nhân sẽ được bổ sung sau." /> },
      { path: 'monitoring', element: <CoordinatorWorkbench mode="emergency" /> }
    ]
  }
])

function PatientAuthGate({ children }: { children: ReactNode }) {
  const user = useSelector((state: RootState) => state.auth.user)
  return user ? <>{children}</> : <Navigate to="/login" replace />
}

function StaffGate() {
  const user = useSelector((state: RootState) => state.auth.user)
  return user?.role === 'staff' ? <StaffLayout /> : <Navigate to="/login" replace />
}

export function App() {
  const dispatch = useDispatch<AppDispatch>()
  const { initialized, restoreError, loading } = useSelector((state: RootState) => state.auth)

  useEffect(() => {
    const handleStorageChange = (event: StorageEvent) => {
      if (event.key && [AUTH_SESSION_KEY, ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY].includes(event.key)) {
        dispatch(sessionChanged(readPublishedSession()))
      }
    }
    const handleTokensUpdated = () => dispatch(sessionChanged(readPublishedSession()))
    const handleUnauthorized = () => dispatch(logout())

    window.addEventListener('storage', handleStorageChange)
    window.addEventListener(AUTH_TOKENS_UPDATED_EVENT, handleTokensUpdated)
    window.addEventListener('auth:unauthorized', handleUnauthorized)
    void dispatch(initializeAuth())

    return () => {
      window.removeEventListener('storage', handleStorageChange)
      window.removeEventListener(AUTH_TOKENS_UPDATED_EVENT, handleTokensUpdated)
      window.removeEventListener('auth:unauthorized', handleUnauthorized)
    }
  }, [dispatch])

  if (!initialized) return <main className="flex min-h-screen items-center justify-center bg-slate-50 light:bg-app-page text-slate-600 light:text-app-secondary" role="status">Đang khôi phục phiên đăng nhập…</main>

  return <>
    <Suspense fallback={<main className="flex min-h-screen items-center justify-center flex-col gap-5 bg-slate-50 light:bg-app-page text-slate-600 light:text-app-secondary dark:bg-[#0B1329] dark:text-slate-300" role="status"><TypewriterLoader size="lg" /><span>Đang tải trang…</span></main>}>
      <RouterProvider router={router} />
    </Suspense>
    {restoreError && <div role="status" className="fixed bottom-4 left-1/2 z-[100] flex max-w-[90vw] -translate-x-1/2 items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 shadow-lg">
      <span>{restoreError}</span>
      <button type="button" disabled={loading} onClick={() => void dispatch(initializeAuth())} className="shrink-0 font-semibold underline disabled:opacity-50">Thử lại</button>
    </div>}
  </>
}
