const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const ts = require('../frontend/node_modules/typescript')
const root = path.join(__dirname, '..')
function loadLogic() {
  const source = fs.readFileSync(path.join(root, 'frontend/src/features/coordinator/uiLogic.ts'), 'utf8')
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  const exported = {}; new Function('exports', code)(exported); return exported
}
const logic = loadLogic()
function effect(file, dependencies, env) {
  const source = fs.readFileSync(path.join(root, file), 'utf8')
  const tree = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
  let callback
  function walk(node) {
    if (ts.isCallExpression(node) && node.expression.getText(tree) === 'useEffect' && node.arguments[1]?.getText(tree) === dependencies) callback = node.arguments[0].getText(tree)
    ts.forEachChild(node, walk)
  }
  walk(tree); assert.ok(callback, 'Effect not found: ' + dependencies)
  const code = ts.transpileModule(`const callback = ${callback}; callback();`, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  return vm.runInNewContext(code, env)
}
const workbench = 'frontend/src/pages/CoordinatorWorkbench.tsx'
const tick = () => new Promise(setImmediate)
function caseEnvironment() {
  const state = { amount: '500000', handover: 'previous', followUp: '2030-10-10T10:00', error: 'previous error', selected: null }
  let resolve
  const env = { selectedId: 'B', selectedRef: { current: 'B' }, detailGeneration: { current: 0 }, acceptCaseDetail: logic.acceptCaseDetail, api: () => new Promise(done => { resolve = done }) }
  for (const field of ['selected', 'note', 'message', 'reference', 'evidence', 'agreed', 'doctor', 'specialty', 'service', 'schedule', 'amount', 'handover', 'followUp', 'error', 'notice']) env['set' + field[0].toUpperCase() + field.slice(1)] = value => { state[field] = typeof value === 'function' ? value(state[field]) : value }
  return { state, env, resolve: value => resolve(value) }
}

test('switching patient clears financial and handover drafts', () => {
  const { state, env } = caseEnvironment(); effect(workbench, '[selectedId]', env)
  for (const field of ['amount', 'handover', 'followUp', 'reference', 'evidence', 'note', 'message']) assert.equal(state[field], '', field)
})
test('late detail cannot overwrite a committed newer version', async () => {
  const scenario = caseEnvironment(); effect(workbench, '[selectedId]', scenario.env)
  scenario.state.selected = { id: 'B', version: 2 }
  scenario.resolve({ id: 'B', version: 1 }); await tick()
  assert.equal(scenario.state.selected.version, 2)
})
test('request from a previous selection is ignored after cleanup', async () => {
  const scenario = caseEnvironment(); const cleanup = effect(workbench, '[selectedId]', scenario.env)
  cleanup(); scenario.state.selected = { id: 'C', version: 3 }; scenario.env.selectedRef.current = 'C'
  scenario.resolve({ id: 'B', version: 1 }); await tick()
  assert.equal(scenario.state.selected.id, 'C')
})
test('mutation invalidates the detail request already in flight', async () => {
  const scenario = caseEnvironment(); effect(workbench, '[selectedId]', scenario.env)
  scenario.env.detailGeneration.current += 1
  scenario.state.selected = { id: 'B', version: 5 }
  scenario.resolve({ id: 'B', version: 1 }); await tick()
  assert.equal(scenario.state.selected.version, 5)
})
test('workbench refresh uses staff events and reconnect, not timed polling', () => {
  const source = fs.readFileSync(path.join(root, workbench), 'utf8')
  assert.match(source, /payload\.type === 'takeover\.case_updated' \|\| payload\.type === 'takeover\.message_created'/)
  assert.match(source, /currentSocket\.addEventListener\('close', scheduleReconnect\)/)
  assert.match(source, /if \(connected\) refresh\(\)/)
  assert.doesNotMatch(source, /setInterval\s*\(/)
})
test('user and staff identities reload after auth token refresh', () => {
  const app = fs.readFileSync(path.join(root, 'frontend/src/App.tsx'), 'utf8')
  const layout = fs.readFileSync(path.join(root, 'frontend/src/layouts/StaffLayout.tsx'), 'utf8')
  assert.match(app, /addEventListener\('auth:refreshed', handleTokenRefreshed\)/)
  assert.match(app, /handleTokenRefreshed = \(\) => \{ void dispatch\(initializeAuth\(\)\) \}/)
  assert.match(layout, /addEventListener\('auth:refreshed', refreshOnTokenRenewal\)/)
  assert.match(layout, /api<Member>\('\/me'\)/)
})
const member = { user_id: 'staff' }
const case_ = { id: 'B', assigned_to: 'staff', status: 'contacting', control: 'ai', session_id: 'session', priority: 3, deposits: [] }
test('complete only enabled for confirmed or transferred emergency', () => {
  for (const status of ['new', 'planned', 'waiting_deposit', 'cancelled', 'completed']) assert.equal(logic.canCaseAction({ ...case_, status }, member, 'complete'), false, status)
  for (const status of ['confirmed', 'emergency_transferred']) assert.equal(logic.canCaseAction({ ...case_, status }, member, 'complete'), true, status)
})
test('closed case blocks chat, contact and follow-up but permits owed refund', () => {
  for (const status of ['cancelled', 'completed']) {
    for (const action of ['takeover', 'message', 'resume', 'contact', 'follow_up', 'cancel']) assert.equal(logic.canCaseAction({ ...case_, status, control: 'human' }, member, action), false)
    assert.equal(logic.canCaseAction({ ...case_, status, deposits: [{ status: 'refund_pending' }] }, member, 'refund_confirm'), true)
  }
})
test('another employee cannot act on an assigned case', () => {
  assert.equal(logic.canCaseAction(case_, { user_id: 'other' }, 'contact'), false)
})
test('emergency transfer requires an acknowledged active emergency', () => {
  assert.equal(logic.canCaseAction({ ...case_, priority: 0 }, member, 'emergency_transfer'), false)
  assert.equal(logic.canCaseAction({ ...case_, priority: 0, status: 'emergency_active' }, member, 'emergency_transfer'), true)
})
test('doctor schedule response is discarded when doctor or week changes', async () => {
  let resolve; const updates = []
  const env = { selectedDoctorId: 'old', weekInfo: { from: '2026-10-05', to: '2026-10-12' }, setSchedules: value => updates.push(value), setModalDate: () => {}, setSelectedSchedule: () => {}, setLoadingSchedules: () => {}, setPageError: () => {}, sortSchedules: value => value, fetchDoctorSchedules: () => new Promise(done => { resolve = done }) }
  const cleanup = effect('frontend/src/pages/DoctorSchedule/index.tsx', '[selectedDoctorId, weekInfo.from, weekInfo.to]', env)
  cleanup(); resolve([{ id: 'old-doctor-slot' }]); await tick()
  assert.equal(updates.length, 1); assert.equal(updates[0].length, 0)
})
test('shift validation rejects missing date and morning overflow', () => {
  const form = { start_time: '11:30', period: 'morning', slot_minutes: '30', slot_count: '2', effective_from: '2026-10-05' }
  assert.notEqual(logic.shiftError(form), '')
  assert.notEqual(logic.shiftError({ ...form, effective_from: '' }), '')
  assert.equal(logic.shiftError({ ...form, slot_count: '1' }), '')
})
test('publication rejects reversed, past and excessive date ranges', () => {
  assert.notEqual(logic.publicationError('2026-10-06', '2026-10-05', '2026-10-05'), '')
  assert.notEqual(logic.publicationError('2026-10-04', '2026-10-06', '2026-10-05'), '')
  assert.notEqual(logic.publicationError('2026-10-05', '2026-12-05', '2026-10-05'), '')
  assert.equal(logic.publicationError('2026-10-05', '2026-10-12', '2026-10-05'), '')
})
test('statistics describe loaded schedules and exclude cancelled capacity', () => {
  assert.deepEqual(logic.scheduleStats([{ status: 'available', capacity: 2 }, { status: 'blocked', capacity: 1 }, { status: 'cancelled', capacity: 99 }]), { total: 3, available: 1, blocked: 1, capacity: 3 })
})
test('CSV exports actual records with escaping and safe free text', () => {
  const csv = logic.schedulesCsv([{ facility_id: 'facility', starts_at: '2026-10-05', ends_at: '2026-10-06', capacity: 2, status: 'available' }], '=example,"quoted"')
  assert.ok(csv.includes('"\'=example,""quoted"""')); assert.ok(csv.includes('"facility"')); assert.equal(csv.split('\r\n').length, 2)
})
