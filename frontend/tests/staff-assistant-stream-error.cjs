const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const ts = require('../node_modules/typescript')

const source = fs.readFileSync(path.join(__dirname, '../src/features/staff-assistant/api.ts'), 'utf8')
const code = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText
const compiledExports = {}
const safeEvent = 'event: error\ndata: {"message":"Không thể xử lý yêu cầu lúc này."}\n\n'
vm.runInNewContext(code, {
  exports: compiledExports,
  require: () => ({ fetchWithAuth: async () => new Response(safeEvent) }),
  TextDecoder,
})

compiledExports.sendStaffMessageStream('Xin chào', undefined, () => {}).then(
  () => assert.fail('Expected an SSE error event to reject'),
  (error) => assert.equal(error.message, 'Không thể xử lý yêu cầu lúc này.'),
)
