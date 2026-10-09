const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ts = require(path.resolve(__dirname, '../node_modules/typescript'));

const source = fs.readFileSync(path.resolve(__dirname, '../src/App.tsx'), 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
    jsx: ts.JsxEmit.ReactJSX,
  },
}).outputText;

let routes;
let query = '';
let user = null;
let location = { pathname: '/patient/appointments', search: '' };
const jsx = (type, props) => ({ type, props });
const lazy = (load) => ({ load });
const mocks = {
  react: { lazy, Suspense: 'Suspense', useEffect() {} },
  'react/jsx-runtime': { jsx, jsxs: jsx },
  'react-router-dom': {
    createBrowserRouter(value) { routes = value; return {}; },
    RouterProvider: 'RouterProvider',
    Navigate: 'Navigate',
    useSearchParams: () => [new URLSearchParams(query)],
    useLocation: () => location,
  },
  'react-redux': { useDispatch: () => () => {}, useSelector: (select) => select({ auth: { user } }) },
  './pages/FamilyProfiles': { default: 'FamilyProfiles' },
  './features/coordinator/StaffAdminGate': { StaffAdminGate: 'StaffAdminGate' },
  './components/TypewriterLoader': { TypewriterLoader: 'TypewriterLoader' },
  './app/store': {},
  './features/auth/authSlice': { initializeAuth() {}, logout() {}, sessionChanged() {} },
  './features/auth/staffReturnTo': { staffReturnTo: value => value || '/staff/coordination' },
  './features/auth/session': {
    ACCESS_TOKEN_KEY: 'access', AUTH_SESSION_KEY: 'session',
    AUTH_TOKENS_UPDATED_EVENT: 'updated', REFRESH_TOKEN_KEY: 'refresh',
    readPublishedSession() {},
  },
  './layouts/PatientLayout': { PatientLayout: 'PatientLayout' },
  './layouts/RootLayout': { RootLayout: 'RootLayout' },
};

const appExports = {};
vm.runInNewContext(compiled, {
  exports: appExports,
  require(name) {
    assert(name in mocks, `Unexpected App dependency: ${name}`);
    return mocks[name];
  },
});

function findRoute(items, routePath) {
  for (const route of items) {
    if (route.path === routePath) return route;
    const child = route.children && findRoute(route.children, routePath);
    if (child) return child;
  }
  return undefined;
}

const appointmentRoute = findRoute(routes, 'appointments');
assert(appointmentRoute, 'Patient appointment route must be registered');
const renderAppointment = appointmentRoute.element.type;

query = '';
assert.match(renderAppointment().type.load.toString(), /pages\/ConsultationBooking/);
query = 'reschedule=booking-123';
const rescheduleRoute = renderAppointment();
assert.equal(rescheduleRoute.type.name, 'PatientAuthGate', 'Rescheduling must require a patient session');
assert.match(rescheduleRoute.props.children.type.load.toString(), /pages\/AppointmentBooking/);
location = { pathname: '/patient/appointments', search: '?reschedule=booking-123' };
const loginRedirect = rescheduleRoute.type(rescheduleRoute.props);
assert.equal(loginRedirect.props.to, '/login?returnTo=%2Fpatient%2Fappointments%3Freschedule%3Dbooking-123');

const staffCoordinationRoute = findRoute(routes, 'coordination');
assert(staffCoordinationRoute, 'English staff coordination route must be registered');
assert.match(staffCoordinationRoute.element.type.load.toString(), /pages\/CoordinatorWorkbench/);
const legacyCoordinationRoute = findRoute(routes, 'dieu-phoi');
assert.equal(legacyCoordinationRoute.element.type, 'Navigate');
assert.equal(legacyCoordinationRoute.element.props.to, '/staff/coordination');
const loginPage = fs.readFileSync(path.resolve(__dirname, '../src/pages/Login.tsx'), 'utf8');
assert(loginPage.includes('navigate(staffReturnTo(new URLSearchParams(location.search).get(\'returnTo\')))'), 'Staff login must validate and restore its return target');
const staffRoute = findRoute(routes, 'staff');
assert(staffRoute, 'Staff route guard must be registered');
assert.match(staffRoute.children[0].element.type.load.toString(), /pages\/StaffDashboard/, 'The staff landing route must use the live dashboard');
for (const pathname of ['/staff', '/staff/queue']) {
  location = { pathname, search: '?mine=true' };
  user = null;
  assert.equal(staffRoute.element.type().props.to, '/', `Signed-out visit to ${pathname} returns to landing`);
  user = { role: 'patient' };
  assert.equal(staffRoute.element.type().props.to, '/', `Patient visit to ${pathname} returns to landing`);
}
user = { role: 'staff' };
assert.match(staffRoute.element.type().type.load.toString(), /layouts\/StaffLayout/);
const notFoundRoute = findRoute(routes, '*');
assert(notFoundRoute, 'Unknown URLs must match the not-found route');
assert.match(notFoundRoute.element.type.load.toString(), /pages\/NotFound/);
const notFoundPage = fs.readFileSync(path.resolve(__dirname, '../src/pages/NotFound.tsx'), 'utf8');
assert.match(notFoundPage, /<Link to="\/"/, 'The 404 page must link back to home');

const approvalRoute = findRoute(routes, 'appointments/approve/:id');
assert(approvalRoute, 'Staff booking approval detail route must be registered');
assert.match(approvalRoute.element.type.load.toString(), /pages\/ScheduleApprove/);
const approvalQueueRoute = findRoute(routes, 'booking-approvals');
assert(approvalQueueRoute, 'Staff booking approval queue route must be registered');
assert.match(approvalQueueRoute.element.type.load.toString(), /pages\/AppointmentApproval/);
const staffLayout = fs.readFileSync(path.resolve(__dirname, '../src/layouts/StaffLayout.tsx'), 'utf8');
assert(staffLayout.includes("'/staff/booking-approvals'"), 'Staff navigation must expose the booking approval queue');
const approvalQueue = fs.readFileSync(path.resolve(__dirname, '../src/pages/AppointmentApproval/index.tsx'), 'utf8');
assert(approvalQueue.includes('/staff/appointments/approve/${id}'), 'Approval queue must open the selected booking detail');
const approvalPage = fs.readFileSync(path.resolve(__dirname, '../src/pages/ScheduleApprove/index.tsx'), 'utf8');
assert(approvalPage.includes("navigate('/staff/booking-approvals')"), 'Approval detail must return to its queue');
assert.equal(findRoute(routes, 'appointments/history').element.type.name, 'PatientAuthGate');
assert.equal(findRoute(routes, 'appointments/:id').element.type.name, 'PatientAuthGate');

console.log('Routes: booking/reschedule, patient auth gates, English staff coordination, and approval queue/detail resolve correctly.');
