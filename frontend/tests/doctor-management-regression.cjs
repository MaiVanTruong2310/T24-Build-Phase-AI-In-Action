const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const page = fs.readFileSync(path.resolve(__dirname, '../src/pages/DoctorManagement/index.tsx'), 'utf8');
assert.match(page, /E\.isRight\(specialtyResult\.value\)[\s\S]*?setSpecialties\(specialtyResult\.value\.right\)[\s\S]*?specialtyResult\.value\.left\.message/,
  'specialty TaskEither Left must be surfaced');
assert.match(page, /Promise\.allSettled\(\[fetchSpecialties\(\)\(\), fetchFacilities\(\)\]\)/,
  'specialty and facility requests must settle independently');
assert.match(page, /setCatalogErrors\(failures\)/, 'catalog failures must use their own state');
assert.match(page, /\[\.\.\.catalogErrors, error\]\.filter\(Boolean\)/,
  'catalog and doctor-list errors must both remain visible');
assert.match(page, /setDoctors\(values\); setError\(''\)/,
  'successful doctor list requests may clear doctor errors without clearing catalog errors');
console.log('Doctor management: catalog requests fail independently and errors survive successful doctor loads.');
