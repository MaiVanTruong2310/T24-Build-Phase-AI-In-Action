const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const source = fs.readFileSync(path.resolve(__dirname, '../src/pages/PatientDepartments.tsx'), 'utf8');
assert.match(source, /let active = true;[\s\S]*?\.then\(\(items\) => \{ if \(active\) setDoctors\(items\); \}\)/,
  'Superseded doctor-search responses must not replace the latest results');
assert.match(source, /\.finally\(\(\) => \{ if \(active\) setDoctorsLoading\(false\); \}\)/,
  'Only the active search request may end its loading state');
assert.match(source, /setDoctorError\(''\)/, 'A new search must clear its previous error');
assert.match(source, /setCatalogError\([\s\S]*?setDoctorError\([\s\S]*?catalogError \|\| doctorError/,
  'Catalog and search errors must remain independently represented');
assert.match(source, /name: name\.trim\(\) \|\| undefined/);
console.log('Patient directory: stale search responses and separated loading/error states passed.');
