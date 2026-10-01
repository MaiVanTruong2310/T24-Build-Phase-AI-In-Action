const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../..');
const ts = require(path.join(root,'frontend/node_modules/typescript'));
function load(mocks) {
  const source = fs.readFileSync(path.join(root,'frontend/src/pages/PatientProfile/index.tsx'),'utf8');
  const compiled = ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}}).outputText;
  const exports = {};
  vm.runInNewContext(compiled,{exports,require(name){ assert(name in mocks, name); return mocks[name]; }, Date,Number,String,Boolean});
  return exports.default;
}
function traverse(node, predicate) {
  if (!node || typeof node !== 'object') return [];
  return [...(predicate(node) ? [node] : []), ...[].concat(node.props?.children || []).flatMap(child => traverse(child,predicate))];
}
function text(node) {
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (!node || typeof node !== 'object') return '';
  return [].concat(node.props?.children || []).map(text).join(' ');
}
async function test() {
  const states = [ {id:'real-profile-id',full_name:'Actual API Name',email:'test@example.invalid',phone:null,patient_details:{blood_type:'O+'}}, false,'','', 'history',null,'',false,''];
  let pointer=0, patch;
  const jsx=(type,props) => ({type,props});
  const component=load({
    react:{useState(initial){const index=pointer++; if (!(index in states)) states[index]=initial;return [states[index],value=>states[index]=typeof value==='function'?value(states[index]):value];},useEffect(){}},
    'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{Link:'Link'},'react-redux':{useDispatch:()=>async()=>{}},'lucide-react':{Pencil:'Pencil'},
    '../../features/auth/authSlice':{initializeAuth:()=>({})},'../../features/auth/session':{readPublishedSession:()=>({id:'real-profile-id'})},
    './api':{fetchPatientProfile:async()=>states[0],updateCurrentUser:async update=>{patch=update;return {...states[0],...update,patient_details:{...states[0].patient_details,...update.patient_details}};}},
    './MedicalHistory':{MedicalHistory:'MedicalHistory'}, './Header':{Header:'Header'}, './MedicalTabs':{MedicalTabs:'MedicalTabs'},
  });
  let tree=component();
  assert(text(tree).includes('Actual API Name'));
  assert(text(tree).includes('Chưa cung cấp'));
  assert(text(tree).includes('Chưa có dữ liệu lịch sử khám'));
  assert(!text(tree).includes('Nguyễn Văn An'));
  const edit=traverse(tree,n=>n.type==='button'&&n.props['aria-label']==='Chỉnh sửa địa chỉ liên hệ')[0];
  assert(edit);edit.props.onClick();pointer=0;tree=component();
  const input=traverse(tree,n=>n.type==='input'&&n.props.id==='profile-field')[0];
  input.props.onChange({target:{value:'Saved Test Address'}});pointer=0;tree=component();
  await traverse(tree,n=>n.type==='form')[0].props.onSubmit({preventDefault(){}});
  assert.deepEqual(JSON.parse(JSON.stringify(patch)),{patient_details:{address:'Saved Test Address'}});
  pointer=0;tree=component();
  assert(text(tree).includes('Saved Test Address'));
  assert(text(tree).includes('O+'));
  console.log('Profile: API identity, missing fields, pencil edit, partial save, and preserved other fields passed.');
}
test().catch(e=>{console.error(e);process.exitCode=1;});
