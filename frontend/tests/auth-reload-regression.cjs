const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
const ts=require(path.join(root,'frontend/node_modules/typescript'));
const toolkit=require(path.join(root,'frontend/node_modules/@reduxjs/toolkit'));
function environment(){
  const values=new Map(), redirects=[],events=[];
  const storage={getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,String(v)),removeItem:k=>values.delete(k)};
  const window={dispatchEvent:e=>events.push(e.type),setTimeout,location:{pathname:'/patient',replace:p=>redirects.push(p)}};
  return {values,redirects,events,storage,window};
}
function load(file,mocks,env,fetch){
  const source=fs.readFileSync(path.join(root,file),'utf8').replace('import.meta.env.VITE_API_BASE_URL',"'http://localhost:8000'");
  const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  const exports={};
  vm.runInNewContext(code,{exports,require:n=>{assert(n in mocks,n);return mocks[n]},localStorage:env.storage,window:env.window,navigator:{locks:{request:async(_,fn)=>fn({})}},Response,Headers,URL,Event,Date,Math,console,fetch,setTimeout,clearTimeout});
  return exports;
}
function authenticated(env,session){
  session.saveTokens('old-access','old-refresh');
  session.publishSession({id:'account-a',full_name:'Test account',role:'patient'});
}
function auth(env,fetch){
  const session=load('frontend/src/features/auth/session.ts',{},env);
  const slice=load('frontend/src/features/auth/authSlice.ts',{'@reduxjs/toolkit':toolkit,'../../app/apiClient':{fetchWithAuth:fetch},'./session':session},env);
  const store=toolkit.configureStore({reducer:{auth:slice.default}});
  return {session,slice,store};
}
async function main(){
  for(const failure of ['network',503,429]){
    const env=environment();const session=load('frontend/src/features/auth/session.ts',{},env);authenticated(env,session);
    const {slice,store}=auth(env,async()=>{if(failure==='network')throw new TypeError('Failed to fetch');return new Response('',{status:failure})});
    assert.equal(store.getState().auth.user.id,'account-a');
    await store.dispatch(slice.initializeAuth());
    assert.equal(store.getState().auth.user.id,'account-a');
    assert(store.getState().auth.initialized && store.getState().auth.restoreError);
    assert.equal(session.readRefreshToken(),'old-refresh');
  }
  {
    const env=environment();const session=load('frontend/src/features/auth/session.ts',{},env);authenticated(env,session);
    let release,calls=0;
    const waiting=new Promise(resolve=>release=resolve);
    const {slice,store}=auth(env,async()=>{calls++;await waiting;return Response.json({data:{id:'account-a',full_name:'Updated account',role:'patient'}})});
    const first=store.dispatch(slice.initializeAuth());await store.dispatch(slice.initializeAuth());assert.equal(calls,1);
    release();await first;assert.equal(store.getState().auth.user.full_name,'Updated account');
  }
  {
    const env=environment();const session=load('frontend/src/features/auth/session.ts',{},env);authenticated(env,session);
    const {slice,store}=auth(env,async()=>new Response('',{status:401}));
    await store.dispatch(slice.initializeAuth());assert.equal(store.getState().auth.user,null);assert.equal(session.readRefreshToken(),null);
  }
  {
    const env=environment();const session=load('frontend/src/features/auth/session.ts',{},env);authenticated(env,session);
    let release;const waiting=new Promise(resolve=>release=resolve);
    const {slice,store}=auth(env,async()=>{await waiting;return Response.json({data:{id:'account-a',full_name:'Test account',role:'patient'}})});
    const request=store.dispatch(slice.initializeAuth());session.clearSession();store.dispatch(slice.logout());release();await request;
    assert.equal(store.getState().auth.user,null);assert.equal(session.readPublishedSession(),null);
  }
  for(const scenario of ['network',503,429,'malformed',400,401,'success','switched']){
    const env=environment();const session=load('frontend/src/features/auth/session.ts',{},env);authenticated(env,session);
    let requests=0;
    const api=load('frontend/src/app/apiClient.ts',{'../features/auth/session':session},env,async url=>{
      requests++;
      if(url.endsWith('/auth/refresh-token')){
        if(scenario==='network')throw new TypeError('Failed to fetch');
        if(scenario==='switched'){session.saveTokens('different-access','different-refresh');return Response.json({data:{access_token:'stale-access',refresh_token:'stale-refresh'}})}
        if(scenario==='success')return Response.json({data:{access_token:'new-access',refresh_token:'new-refresh'}});
        if(scenario==='malformed')return Response.json({});
        return new Response('',{status:scenario});
      }
      return new Response('',{status:requests===1?401:200});
    });
    if(['network',503,429,'malformed'].includes(scenario)){
      await assert.rejects(api.fetchWithAuth('/users/me'));
      assert.equal(session.readRefreshToken(),'old-refresh');assert.equal(env.redirects.length,0);
    }else{
      const response=await api.fetchWithAuth('/users/me');
      if(scenario==='switched'){assert.equal(response.status,200);assert.equal(session.readRefreshToken(),'different-refresh')}
      else if(scenario==='success'){assert.equal(response.status,200);assert.equal(session.readRefreshToken(),'new-refresh')}
      else {assert.equal(session.readRefreshToken(),null);assert.equal(env.redirects.length,1)}
    }
  }
  console.log('Auth reload: cached bootstrap, verified restore, single initialization, transient failures, token rotation, invalid session logout and logout race passed.');
}
main().catch(error=>{console.error(error);process.exitCode=1});
