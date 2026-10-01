const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const assert = require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
const ts=require(path.join(root,'frontend/node_modules/typescript'));
const states=[];let pointer=0,saved;
const jsx=(type,props)=>({type,props});
const source=fs.readFileSync(path.join(root,'frontend/src/pages/PatientProfile/MedicalHistory.tsx'),'utf8');
const exportsObj={};
vm.runInNewContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022}}).outputText,{
  exports:exportsObj, crypto:require('node:crypto').webcrypto,
  require(name){ if(name==='react') return {useState(initial){const i=pointer++;if(!(i in states))states[i]=initial;return[states[i],v=>states[i]=v];}};
    if(name==='react/jsx-runtime')return {jsx,jsxs:jsx};if(name==='lucide-react')return {};
    throw new Error(name); }
});
function find(node,predicate){if(!node||typeof node!=='object')return [];return [...(predicate(node)?[node]:[]),...[].concat(node.props?.children||[]).flatMap(child=>find(child,predicate))];}
const history=[{id:'test-1',name:'History test condition',status:'in_treatment'},{id:'test-2',name:'Another test condition',status:'recovered'}];
function render(){pointer=0;return exportsObj.MedicalHistory({history,onSave:async value=>saved=value});}
async function main(){
  let tree=render();
  find(tree,n=>n.type==='button'&&n.props['aria-label']==='Chỉnh sửa bệnh History test condition')[0].props.onClick();
  tree=render();
  find(tree,n=>n.type==='select'&&n.props.id==='condition-status')[0].props.onChange({target:{value:'recovered'}});
  tree=render();await find(tree,n=>n.type==='form')[0].props.onSubmit({preventDefault(){}});
  assert.equal(saved[0].id,'test-1');assert.equal(saved[0].status,'recovered');assert.equal(saved[1].name,'Another test condition');
  tree=render();find(tree,n=>n.type==='button'&&n.props.children?.some?.(child=>child==='Thêm bệnh'))[0].props.onClick();
  tree=render();find(tree,n=>n.type==='input'&&n.props.id==='condition-name')[0].props.onChange({target:{value:' New history entry '}});
  tree=render();await find(tree,n=>n.type==='form')[0].props.onSubmit({preventDefault(){}});
  assert.equal(saved.length,3);assert.equal(saved[2].name,'New history entry');assert.equal(saved[2].status,'in_treatment');assert(saved[2].id);
  const page=fs.readFileSync(path.join(root,'frontend/src/pages/PatientProfile/index.tsx'),'utf8');
  for(const label of ['Nhịp tim','Huyết áp tâm trương','Huyết áp tâm thu','Đường huyết'])assert(!page.includes(label));
  console.log('Medical history: add, edit status, preserve other entries, and removed vital inputs passed.');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
