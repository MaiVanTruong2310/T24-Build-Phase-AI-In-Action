import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import { PatientLayout, RootLayout, StaffLayout, AuthLayout } from './layouts'
import { Landing } from './pages/Landing'
import { Login } from './pages/Login'
import { Register } from './pages/Register'
import { ForgotPassword } from './pages/ForgotPassword'
import EmergencyCoordinator from './pages/EmergencyCoordinator'
import AppointmentBooking from './pages/AppointmentBooking'
import DoctorManagement from './pages/DoctorManagement'
import CreateDoctor from './pages/DoctorManagement/Create'
import ServiceManagement from './pages/ServiceManagement'
import CreateService from './pages/ServiceManagement/Create'
import ScheduleApprove from './pages/ScheduleApprove'
import DoctorSchedule from './pages/DoctorSchedule'
import PatientProfile from './pages/PatientProfile'
import PatientDepartments from './pages/PatientDepartments'

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
  {
    element: <RootLayout />,
    children: [
      {
        path: 'patient',
        element: <PatientLayout />,
        children: [
          { index: true, element: <Placeholder title="Khu bệnh nhân" description="Khu vực dành cho bệnh nhân và người nhà." /> },
          { path: 'profile', element: <PatientProfile /> },
          { path: 'departments', element: <PatientDepartments /> },
          { path: 'appointments', element: <AppointmentBooking /> }
        ]
      }
    ]
  },
  {
    path: 'staff',
    element: <StaffLayout />,
    children: [
      { index: true, element: <Navigate to="queue" replace /> },
      { path: 'queue', element: <EmergencyCoordinator /> },
      { path: 'doctors', element: <DoctorManagement /> },
      { path: 'doctors/create', element: <CreateDoctor /> },
      { path: 'services', element: <ServiceManagement /> },
      { path: 'services/create', element: <CreateService /> },
      { path: 'appointments/approve/:id', element: <ScheduleApprove /> },
      { path: 'doctor-schedule', element: <DoctorSchedule /> },
      { path: 'patients', element: <Placeholder title="Quản lý bệnh nhân" description="Page quản lý bệnh nhân sẽ được bổ sung sau." /> },
      { path: 'monitoring', element: <Placeholder title="Giám sát hệ thống" description="Page giám sát hệ thống sẽ được bổ sung sau." /> }
    ]
  }
])

export function App() {
  return <RouterProvider router={router} />
}
