import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { PatientLayout, RootLayout, StaffLayout, AuthLayout } from './layouts'
import { Landing } from './pages/Landing'
import { Login } from './pages/Login'
import { Register } from './pages/Register'
import { ForgotPassword } from './pages/ForgotPassword'

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
          { path: 'departments', element: <Placeholder title="Tìm khoa khám" description="Page tìm kiếm và điều hướng khoa khám sẽ được bổ sung sau." /> },
          { path: 'appointments', element: <Placeholder title="Lịch hẹn" description="Page lịch hẹn sẽ được bổ sung sau." /> }
        ]
      },
      {
        path: 'staff',
        element: <StaffLayout />,
        children: [
          { index: true, element: <Placeholder title="Khu nhân viên" description="Khu vực dành cho nhân viên tiếp đón và y tế." /> },
          { path: 'queue', element: <Placeholder title="Điều phối hàng đợi" description="Page điều phối hàng đợi sẽ được bổ sung sau." /> },
          { path: 'patients', element: <Placeholder title="Quản lý bệnh nhân" description="Page quản lý bệnh nhân sẽ được bổ sung sau." /> },
          { path: 'monitoring', element: <Placeholder title="Giám sát hệ thống" description="Page giám sát hệ thống sẽ được bổ sung sau." /> }
        ]
      }
    ]
  }
])

export function App() {
  return <RouterProvider router={router} />
}
