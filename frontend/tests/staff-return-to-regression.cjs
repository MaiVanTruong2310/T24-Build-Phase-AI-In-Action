const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const ts = require('../node_modules/typescript')

const source = fs.readFileSync(path.join(__dirname, '../src/features/auth/staffReturnTo.ts'), 'utf8')
const code = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText
const compiledExports = {}
vm.runInNewContext(code, { exports: compiledExports, window: { location: { origin: 'https://app.example' } }, URL })
const { staffReturnTo } = compiledExports

assert.equal(staffReturnTo('/staff'), '/staff')
assert.equal(staffReturnTo('/staff/queue?mine=true'), '/staff/queue?mine=true')
for (const target of [null, '', '/staffing', '/staff/../patient', '/login', '/patient', '//evil.example/staff', 'https://evil.example/staff', '/\\evil.example/staff']) {
  assert.equal(staffReturnTo(target), '/staff/coordination', String(target))
}

console.log('Staff return targets preserve valid staff routes and reject unsafe or non-staff destinations.')
