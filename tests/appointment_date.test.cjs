const { test } = require('node:test')
const assert = require('node:assert/strict')
const ts = require('../frontend/node_modules/typescript')
const fs = require('node:fs')
const source = fs.readFileSync(require('node:path').join(__dirname, '../frontend/src/features/appointment-booking/dateValidation.ts'), 'utf8')
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
const module_ = { exports: {} }
new Function('exports', compiled)(module_.exports)
const { appointmentDateError, vietnamToday } = module_.exports
test('rejects incomplete, nonexistent, and past appointment dates', () => {
  for (const date of ['', '2026-2-01', '1266-02-31', '2026-02-31', '2025-02-29', '2026-04-31', '0000-01-01', '2026-10-04']) {
    assert.ok(appointmentDateError(date, '2026-10-05'), date)
  }
})
test('accepts today and dates within the booking window', () => {
  for (const date of ['2026-10-05', '2026-10-06', '2027-01-03']) assert.equal(appointmentDateError(date, '2026-10-05'), '')
})
test('today uses Vietnam timezone across the UTC midnight boundary', () => {
  assert.equal(vietnamToday(new Date('2026-10-04T17:00:00Z')), '2026-10-05')
  assert.equal(vietnamToday(new Date('2026-10-04T16:59:59Z')), '2026-10-04')
})

test('rejects year 3000 and the first day beyond the 90-day window', () => {
  assert.ok(appointmentDateError('3000-01-01', '2026-10-05'))
  assert.ok(appointmentDateError('2027-01-04', '2026-10-05'))
  assert.equal(appointmentDateError('2024-02-29', '2023-12-01'), '')
  assert.ok(appointmentDateError('2024-03-01', '2023-12-01'))
})
