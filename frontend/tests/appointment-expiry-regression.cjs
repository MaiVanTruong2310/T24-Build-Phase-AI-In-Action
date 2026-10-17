const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ts = require(path.resolve(__dirname, '../node_modules/typescript'));

const read = (...parts) => fs.readFileSync(path.resolve(__dirname, '../src', ...parts), 'utf8');
const api = read('features/appointment-booking/api.ts');
assert.match(api, /BookingStatus\s*=\s*'pending_approval'\s*\|\s*'confirmed'\s*\|\s*'rejected'\s*\|\s*'cancelled'\s*\|\s*'expired'/);
assert.match(api, /BookingListStatus\s*=\s*Exclude<BookingStatus,\s*'expired'>/);
assert.match(api, /fetchBookings\(status\?: BookingListStatus\)/, 'List query type must exclude response-only expired status');

for (const file of ['pages/AppointmentHistory.tsx', 'pages/AppointmentDetail.tsx', 'features/appointment-progress/components/AppointmentCard.tsx']) {
  assert.match(read(file), /status === 'expired'\) return 'Đã hết hạn'/, `${file} must label expired bookings accurately`);
}

const detailPanel = read('features/appointment-progress/components/AppointmentDetailPanel.tsx');
assert.match(detailPanel, /booking\.status === 'expired'/, 'Progress detail must show an expired terminal state');
assert.match(detailPanel, /canModify = booking\.status === 'pending_approval' \|\| booking\.status === 'confirmed'/,
  'Expired bookings must not show cancel or reschedule actions');

const approvalApi = read('pages/AppointmentApproval/api.ts');
assert.equal((approvalApi.match(/status: BookingStatus;/g) || []).length, 2, 'Staff API response and rendered booking must accept expired status');
const constantsPath = path.resolve(__dirname, '../src/pages/AppointmentApproval/components/constants.ts');
const compiledConstants = ts.transpileModule(fs.readFileSync(constantsPath, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const configExports = {};
vm.runInNewContext(compiledConstants, {
  exports: configExports,
  require: () => ({ AlertTriangle: 'AlertTriangle', ShieldCheck: 'ShieldCheck', Flame: 'Flame' }),
});
assert.equal(configExports.STATUS_CONFIG.expired.label, 'Đã hết hạn', 'Staff approval cards must have a status entry for expired records');
console.log('Appointments: expired bookings are represented and not mislabeled as cancelled/rejected.');
