const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const source = fs.readFileSync(path.resolve(__dirname, '../src/pages/DoctorDirectory.tsx'), 'utf8');
assert.match(source, /fetchSpecialties\(\{ facilityId \}\)\.then\(s => \{\s*if \(!active\) return/,
  'Stale specialty options must not replace options for the current facility');
assert.match(source, /fetchFacilities\(\{ specialtyId \}\)\.then\(f => \{ if \(active\) setFacilities\(f\) \}\)/,
  'Stale facility options must not replace options for the current specialty');
assert.match(source, /else if \(!specialtyId && allFacilities\.length > 0\)\s*\{\s*setFacilities\(allFacilities\)/,
  'Clearing specialty must restore all facilities even if a facility remains selected');
assert((source.match(/return \(\) => \{ active = false \}/g) || []).length >= 3,
  'Catalog/dependent option effects must ignore responses after unmount');
console.log('Doctor directory: dependent filter requests are guarded and facilities restore correctly.');
