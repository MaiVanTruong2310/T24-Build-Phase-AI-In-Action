const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')

const source = fs.readFileSync(path.join(__dirname, '../src/features/staff-assistant/StaffAssistantWidget.tsx'), 'utf8')

assert.ok(source.includes("setOpen(true)"), 'An incoming/recovered alert must expand the assistant widget')
assert.ok(source.includes("alertType: alert.event_type"), 'The event type must reach alert rendering')
assert.ok(source.includes("message.alertType === 'emergency_detected'"), 'Emergency alerts must have a distinct rendering branch')
assert.ok(source.includes('role={message.alertType === \'emergency_detected\' ? \'alert\' : undefined}'), 'Emergency alert must be announced accessibly')
assert.ok(source.includes('/staff/emergency?case=${encodeURIComponent(message.caseId)}'), 'Emergency alert must link to its case')
assert.ok(source.includes('if (open && focusInputOnOpen.current)'), 'Realtime expansion must not steal focus from the active staff control')

console.log('Staff assistant alert UI regression checks passed.')
