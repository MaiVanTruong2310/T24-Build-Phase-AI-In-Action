const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ts = require(path.resolve(__dirname, '../node_modules/typescript'));

const helperPath = path.resolve(__dirname, '../src/pages/DoctorSchedule/filterDoctors.ts');
const compiled = ts.transpileModule(fs.readFileSync(helperPath, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const moduleExports = {};
vm.runInNewContext(compiled, { exports: moduleExports });

const doctors = [
  { id: '1', full_name: 'Dr. Linh Nguyen', code: 'DOC-01', facilities: [{ department: 'Cardiology', facility: { name: 'Central Clinic', code: 'CC' } }] },
  { id: '2', full_name: 'Dr. An Tran', code: 'DOC-02', facilities: [{ room: 'B12', facility: { name: 'West Clinic', code: 'WC' } }] },
];
assert.deepEqual(Array.from(moduleExports.filterDoctors(doctors, '  LINH '), doctor => doctor.id), ['1']);
assert.deepEqual(Array.from(moduleExports.filterDoctors(doctors, 'doc-02'), doctor => doctor.id), ['2']);
assert.deepEqual(Array.from(moduleExports.filterDoctors(doctors, 'central clinic'), doctor => doctor.id), ['1']);
assert.equal(moduleExports.filterDoctors(doctors, '').length, 2, 'Reset query must show all doctors');

const sidebar = fs.readFileSync(path.resolve(__dirname, '../src/pages/DoctorSchedule/components/Sidebar.tsx'), 'utf8');
assert.match(sidebar, /to="\/staff\/doctors\/create"/, 'Add-doctor action must open the registered create route');
assert.match(sidebar, /onClick=\{\(\) => setSearch\(''\)\}/, 'Reset control must clear the query');
console.log('Doctor schedule: name, code, facility search, reset, and add-doctor route passed.');
