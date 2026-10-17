const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ts = require(path.resolve(__dirname, '../node_modules/typescript'));
const jsx = (type, props) => ({ type, props });
const textContent = (node) => {
  if (node == null || typeof node === 'boolean') return '';
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(textContent).join(' ');
  return textContent(node.props?.children);
};

const filterSource = fs.readFileSync(path.resolve(__dirname, '../src/pages/ServiceManagement/filterServices.ts'), 'utf8');
const filterCompiled = ts.transpileModule(filterSource, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const filterExports = {};
vm.runInNewContext(filterCompiled, { exports: filterExports });
const exportSource = fs.readFileSync(path.resolve(__dirname, '../src/pages/ServiceManagement/exportServicesCsv.ts'), 'utf8');
const exportCompiled = ts.transpileModule(exportSource, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const exportExports = {};
vm.runInNewContext(exportCompiled, { exports: exportExports });
const serviceRows = [
  { id: '1', name: 'General Checkup', code: 'GEN-1', category: 'Family', price: 900_000, status: 'active' },
  { id: '2', name: 'Business Screening', code: 'BIZ-1', category: 'Business', price: 2_000_000, status: 'inactive' },
  { id: '3', name: 'Unknown Price', code: 'UNK-1', category: 'Family', price: null, status: 'active', patient_count: 7, satisfaction_rate: 95 },
];
const filtered = filterExports.filterServices(serviceRows, {
  search: 'general', category: 'Family', priceRange: 'under-1m', status: 'active',
});
assert.deepEqual(Array.from(filtered, (service) => service.id), ['1'], 'Combined filters must match case-insensitively');
assert.equal(filterExports.filterServices(serviceRows, { search: '', category: '', priceRange: 'over-3m', status: '' }).length, 0, 'Unknown price must not match a bounded price filter');
assert.equal(filterExports.filterServices(serviceRows, { search: '', category: '', priceRange: '', status: '' }).length, 3, 'Empty filters must return every service');
const csv = exportExports.serializeServicesCsv([{
  code: '=SUM(1,1)', name: 'Clinic, "Plus"', description: null, category: null,
  price: 0, duration_minutes: 30, status: 'active',
}]);
assert.match(csv, /'=?SUM\(1,1\)/, 'Formula-like exported values must be neutralized');
assert.match(csv, /"Clinic, ""Plus"""/, 'CSV strings with delimiters/quotes must be escaped');
assert.match(csv, /"0"/, 'Zero-valued prices must not be treated as missing');
const statsSource = fs.readFileSync(path.resolve(__dirname, '../src/pages/ServiceManagement/Stats.tsx'), 'utf8');
assert(!statsSource.includes('2.840') && !statsSource.includes('4.2') && !statsSource.includes('842'), 'Operational KPI values must not be hard-coded');
const statsCompiled = ts.transpileModule(statsSource, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
}).outputText;
const statsExports = {};
vm.runInNewContext(statsCompiled, {
  exports: statsExports,
  require(name) {
    if (name === 'react') return { __esModule: true, default: {} };
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx };
    if (name === 'lucide-react') return { Package: 'Package', CalendarCheck: 'CalendarCheck', TrendingUp: 'TrendingUp', Settings: 'Settings' };
    throw new Error(`Unexpected dependency: ${name}`);
  },
});
const statsTree = statsExports.Stats({ services: serviceRows, loaded: true });
const statsText = textContent(statsTree);
assert(statsText.includes('3 dịch vụ') && /2\s+đang mở bán/.test(statsText) && /1\s+tạm ngưng/.test(statsText), 'Catalog totals must reflect returned services');
assert(statsText.includes('Unknown Price') && statsText.includes('7 lượt khám') && statsText.includes('95% hài lòng') && statsText.includes('chưa có dữ liệu'), 'Available popularity data must render, unavailable metrics must not be fabricated');

const pageSource = fs.readFileSync(path.resolve(__dirname, '../src/pages/ServiceManagement/index.tsx'), 'utf8');
assert(!pageSource.includes('Math.random'), 'Catalog refresh must not fabricate random usage metrics');
assert(pageSource.includes('success(enrichedServices)'), 'Successful API data must populate the catalog');
const createSource = fs.readFileSync(path.resolve(__dirname, '../src/pages/ServiceManagement/Create/index.tsx'), 'utf8');
const draftButton = createSource.match(/<button\b[^>]*>\s*Lưu nháp\s*<\/button>/)?.[0];
assert(draftButton, 'Service form must retain the draft action');
assert.match(draftButton, /\bdisabled\b/);
assert.match(draftButton, /aria-label="[^"]+"/);
assert.match(draftButton, /title="[^"]+"/);

const previewSource = fs.readFileSync(path.resolve(__dirname, '../src/pages/ServiceManagement/Create/PreviewSidebar.tsx'), 'utf8');
const previewButton = previewSource.match(/<button\b[^>]*>[\s\S]*?<\/button>/)?.[0];
assert(previewButton, 'Service preview must retain its eye control');
assert.match(previewButton, /\bdisabled\b/, 'Unavailable separate preview action must not appear interactive');
assert.match(previewButton, /aria-label="[^"]+"/, 'Disabled preview control must have an accessible label');
assert.match(previewButton, /title="[^"]+"/, 'Disabled preview control must explain why it is unavailable');

const source = fs.readFileSync(path.resolve(__dirname, '../src/pages/ServiceManagement/ServiceGrid.tsx'), 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
}).outputText;
const icons = Object.fromEntries(['Clock', 'CheckCircle2', 'Copy', 'FileEdit', 'UserCircle', 'Star'].map((name) => [name, name]));
const moduleExports = {};
vm.runInNewContext(compiled, {
  exports: moduleExports,
  require(name) {
    if (name === 'react') return { __esModule: true, default: {} };
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx };
    if (name === 'lucide-react') return icons;
    throw new Error(`Unexpected dependency: ${name}`);
  },
});

const tree = moduleExports.ServiceGrid({ services: [{
  id: 'service-1', code: 'S1', name: 'Service', status: 'inactive', updated_at: '2026-01-01',
  price: null, original_price: null, duration_minutes: null, features: null,
  patient_count: null, satisfaction_rate: null, category: null,
}] });
const renderedText = textContent(tree);
assert(!renderedText.includes('100%'), 'Missing satisfaction must not display a fabricated perfect score');
assert(!renderedText.includes('14 hạng mục'), 'Catalog must not claim a fixed number of unavailable features');
assert(renderedText.includes('Chưa có đánh giá'), 'Missing satisfaction must have an explicit empty state');
const findNodes = (node, type) => {
  if (Array.isArray(node)) return node.flatMap((item) => findNodes(item, type));
  if (!node || typeof node !== 'object') return [];
  return [...(node.type === type ? [node] : []), ...findNodes(node.props?.children, type)];
};
assert(findNodes(tree, 'button').every((button) => button.props.disabled), 'Unsupported catalog actions must be disabled');
assert(findNodes(tree, 'input').every((input) => input.props.readOnly), 'Status is informational until a mutation API is wired');

console.log('Service catalog: filters, CSV export safety, real/unknown metrics, and unsupported controls passed.');
