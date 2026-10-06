const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),ts=require(path.join(root,'frontend/node_modules/typescript'));
const toolkit=require(path.join(root,'frontend/node_modules/@reduxjs/toolkit'));
function environment(){
  const values=new Map(),events=[];
  const storage={getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,String(v)),removeItem:k=>values.delete(k)};
  const window={dispatchEvent:e=>events.push(e.type),setTimeout,location:{pathname:'/patient',replace(){throw Error('Unexpected redirect')}}};
  return {values,events,storage,window};
}
function load(file,mocks,env,fetch,apiBaseUrl='http://localhost:8000'){
  const source=fs.readFileSync(path.join(root,file),'utf8').replace('import.meta.env.VITE_API_BASE_URL',JSON.stringify(apiBaseUrl));
  const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  const exports={};
  vm.runInNewContext(code,{exports,require:n=>{assert(n in mocks,n);return mocks[n]},localStorage:env.storage,window:env.window,navigator:{locks:{request:async(_,fn)=>fn({})}},Response,Headers,URL,Event,Date,Math,console,fetch,setTimeout,clearTimeout});
  return exports;
}
const profile={id:'account-a',full_name:'Test account',role:'patient'};
function setup(fetch,apiBaseUrl){
  const env=environment(),session=load('frontend/src/features/auth/session.ts',{},env);
  const api=load('frontend/src/app/apiClient.ts',{'../features/auth/session':session},env,fetch,apiBaseUrl);
  const slice=load('frontend/src/features/auth/authSlice.ts',{'@reduxjs/toolkit':toolkit,'../../app/apiClient':api,'./session':session},env);
  return {env,session,api,slice,store:toolkit.configureStore({reducer:{auth:slice.default}})};
}
async function main(){
  {
    const x=setup(async()=>Response.json({data:null}));
    assert.equal(x.api.resolveWebSocketUrl('/staff/chat-takeover/ws/session%2Fone?channel=staff'),
      'ws://localhost:8000/api/v1/staff/chat-takeover/ws/session%2Fone?channel=staff');
    const production=setup(async()=>Response.json({data:null}),'https://api.example.invalid');
    assert.equal(production.api.resolveWebSocketUrl('/staff/chat-takeover/ws/staff?channel=staff'),
      'wss://api.example.invalid/api/v1/staff/chat-takeover/ws/staff?channel=staff');
  }
  {
    let calls=0;
    const x=setup(async(url,options)=>{calls++;assert.equal(options.credentials,'include');assert.equal(new Headers(options.headers).get('authorization'),null);return Response.json({data:profile})});
    await x.store.dispatch(x.slice.initializeAuth());
    assert.equal(x.store.getState().auth.user.id,profile.id);
    // Reload creates a fresh Redux store; server cookies restore the user without any JS-readable token.
    const slice=load('frontend/src/features/auth/authSlice.ts',{'@reduxjs/toolkit':toolkit,'../../app/apiClient':x.api,'./session':x.session},x.env);
    const fresh=toolkit.configureStore({reducer:{auth:slice.default}});
    await fresh.dispatch(slice.initializeAuth());
    assert.equal(calls,2);
    assert.equal(fresh.getState().auth.user.id,profile.id);
    assert(!x.env.storage.getItem('access_token') && !x.env.storage.getItem('refresh_token'));
    assert(!('token' in fresh.getState().auth.user));
  }
  {
    const x=setup(async(url,options)=>{
      assert.equal(options.credentials,'include');
      if(url.endsWith('/auth/login'))return Response.json({data:{authenticated:true,expires_in:3600}});
      if(url.endsWith('/auth/logout')){assert(!options.body);return Response.json({data:null})}
      return Response.json({data:profile});
    });
    await x.store.dispatch(x.slice.loginUser({username:'cookie@example.invalid',password:'example-password'}));
    assert.equal(x.store.getState().auth.user.id,profile.id);
    await x.store.dispatch(x.slice.logoutUser());
    assert.equal(x.store.getState().auth.user,null);assert.equal(x.session.readPublishedSession(),null);
  }
  {
    let reads=0,refreshes=0;
    const x=setup(async(url,options)=>{
      if(url.endsWith('/auth/refresh-token')){refreshes++;assert(!options.body);return Response.json({data:{authenticated:true}})}
      reads++;return reads===1?new Response('',{status:401}):Response.json({data:profile});
    });
    const result=await x.api.fetchWithAuth('/users/me');assert.equal(result.status,200);assert.equal(refreshes,1);
  }
  for(const failure of ['network',503,429]){
    const x=setup(async url=>{
      if(url.endsWith('/auth/refresh-token')){if(failure==='network')throw TypeError('Failed to fetch');return new Response('',{status:failure})}
      return new Response('',{status:401});
    });
    x.session.publishSession(profile);x.store.dispatch(x.slice.sessionChanged(profile));
    await x.store.dispatch(x.slice.initializeAuth());
    assert.equal(x.store.getState().auth.user.id,profile.id);assert(x.store.getState().auth.restoreError);
    assert(!x.env.events.includes('auth:unauthorized'));
  }
  {
    const x=setup(async()=>new Response('',{status:401}));
    x.session.publishSession(profile);x.store.dispatch(x.slice.sessionChanged(profile));
    await x.store.dispatch(x.slice.initializeAuth());assert.equal(x.store.getState().auth.user,null);
  }
  {
    let transferred=false;
    const x=setup(async(url,options)=>{
      if(url.endsWith('/auth/refresh-token')){assert.equal(JSON.parse(options.body).refresh_token,'legacy-refresh');transferred=true;return Response.json({data:{authenticated:true}})}
      return Response.json({data:profile});
    });
    x.env.storage.setItem('access_token','legacy-access');x.env.storage.setItem('refresh_token','legacy-refresh');
    await x.store.dispatch(x.slice.initializeAuth());assert(transferred);
    assert(!x.env.storage.getItem('access_token')&&!x.env.storage.getItem('refresh_token'));
  }
  {
    let release,calls=0;const wait=new Promise(resolve=>release=resolve);
    const x=setup(async()=>{calls++;await wait;return Response.json({data:profile})});
    const first=x.store.dispatch(x.slice.initializeAuth());await x.store.dispatch(x.slice.initializeAuth());
    await new Promise(resolve=>setTimeout(resolve,0));assert.equal(calls,1);
    x.session.clearSession();x.store.dispatch(x.slice.logout());release();await first;
    assert.equal(x.store.getState().auth.user,null);
  }
  console.log('Cookie auth: credentials, no JS tokens, reload restoration, login/logout, rotation, transient errors, migration and duplicate bootstrap passed.');
}
main().catch(error=>{console.error(error);process.exitCode=1});
