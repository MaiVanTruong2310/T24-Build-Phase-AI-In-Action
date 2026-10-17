const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const ts = require('../frontend/node_modules/typescript')
const source = fs.readFileSync(path.join(__dirname, '../frontend/src/features/coordinator/mutations.ts'), 'utf8')
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
const exported = {}
new Function('exports', js)(exported)
const { saveAndRefresh } = exported

test('save survives a failed refresh and publishes authoritative version first', async () => {
  const events = []
  const detail = { id: 'case', version: 4 }
  const outcome = await saveAndRefresh(async () => { events.push('save'); return detail }, result => {
    events.push('saved'); assert.equal(result.version, 4)
  }, async () => { events.push('refresh'); throw new Error('unavailable') })
  assert.equal(outcome.result, detail)
  assert.equal(outcome.refreshed, false)
  assert.deepEqual(events, ['save', 'saved', 'refresh'])
})

test('failed write never reports success or invokes refresh', async () => {
  let saved = false
  let refreshed = false
  await assert.rejects(saveAndRefresh(async () => { throw new Error('conflict') }, () => { saved = true }, async () => { refreshed = true }), /conflict/)
  assert.equal(saved, false)
  assert.equal(refreshed, false)
})

test('successful write and refresh return the committed result', async () => {
  const outcome = await saveAndRefresh(async () => ({ on_duty: true }), () => {}, async () => {})
  assert.equal(outcome.refreshed, true)
  assert.equal(outcome.result.on_duty, true)
})
