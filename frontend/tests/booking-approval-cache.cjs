const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const page = fs.readFileSync(path.resolve(__dirname, '../src/pages/AppointmentApproval/index.tsx'), 'utf8');
const slice = fs.readFileSync(path.resolve(__dirname, '../src/features/booking-approvals/bookingApprovalsSlice.ts'), 'utf8');
assert.match(page, /state\.bookingApprovals/, 'Queue data must come from Redux');
assert.match(slice, /APPROVAL_TABS\.some\(tab => !state\.pages\[approvalPageKey\(filters, tab\)\]\)/,
  'Missing tab pages must trigger one prefetch of the queue views');
assert.match(slice, /fetchPendingBookings\(\{ \.\.\.filters, status: 'pending_approval' \}\)/,
  'Pending view is part of the initial tab prefetch');
assert.match(slice, /fetchPendingBookings\(\{ \.\.\.filters, status: 'confirmed' \}\)/,
  'Confirmed view is part of the initial tab prefetch');
assert.match(slice, /fetchPendingBookings\(\{ \.\.\.filters, status: 'rejected' \}\)/,
  'Rejected view is part of the initial tab prefetch');
assert.equal((page.match(/dispatch\(clearBookingApprovalPages\(\)\)/g) || []).length, 2,
  'Approve and reject must each invalidate Redux queue pages');

console.log('Booking approval queue cache is filter-scoped and invalidated after review.');
