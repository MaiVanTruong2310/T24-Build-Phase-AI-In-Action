const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../..');
const ts = require(path.join(root, 'frontend/node_modules/typescript'));
function load(relative, mocks) {
  const source = fs.readFileSync(path.join(root, relative), 'utf8');
  const compiled = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
    jsx: ts.JsxEmit.ReactJSX,
  }}).outputText;
  const exports = {};
  vm.runInNewContext(compiled, { exports, require: (name) => {
    if (!(name in mocks)) throw new Error(`Unexpected dependency: ${name}`);
    return mocks[name];
  }, Response, Headers, TextDecoder, AbortController, console,
  crypto: require('node:crypto').webcrypto,
  sessionStorage: { getItem: () => null, setItem() {} },
  setTimeout, clearTimeout }, { filename: relative });
  return exports;
}
let response;
const api = load('frontend/src/features/chat/api.ts', {
  '../../app/apiClient': { fetchPublicApi: async () => response, fetchWithAuth: async () => response },
  '../auth/session': { readAccessToken: () => null, readRefreshToken: () => null },
});
const sse = (body) => new Response(body, { headers: { 'content-type': 'text/event-stream' } });
async function transportTests() {
  response = new Response('<html>ngrok offline</html>', { headers: { 'content-type': 'text/html' } });
  await assert.rejects(api.streamChat({ message: 'Chào bạn', sessionId: 'test', onToken() {}, onMetadata() {} }));
  await assert.rejects(api.sendChat('Chào bạn', 'test'));
  for (const body of ['', 'data: {"type":"token","content":"unfinished"}\n\n', 'data: [DONE]\n\n']) {
    response = sse(body);
    await assert.rejects(api.streamChat({ message: 'hello', sessionId: 'test', onToken() {}, onMetadata() {} }));
  }
  response = sse('data: {"type":"token","content":"Xin chào"}\n\ndata: {"type":"metadata","workflow_status":"FAQ_ANSWERED"}\n\ndata: [DONE]\n\n');
  let text = '', metadata;
  await api.streamChat({ message: 'hello', sessionId: 'test', onToken: t => { text += t; }, onMetadata: m => { metadata = m; } });
  assert.equal(text, 'Xin chào');
  assert.equal(metadata.workflow_status, 'FAQ_ANSWERED');
  response = Response.json({ response: 'Xin chào', ats_level: null });
  assert.equal((await api.sendChat('hello', 'test')).response, 'Xin chào');
  console.log('Transport: HTML, invalid JSON, empty/truncated SSE rejected; valid SSE/JSON preserved.');
}
async function widgetTest(mode) {
  const states = [];
  let calls = 0;
  const react = {
    useState(initial) {
      const i = states.length;
      // Simulate the greeting typed in the input.
      states.push(i === 2 ? 'Chào bạn' : typeof initial === 'function' ? initial() : initial);
      return [states[i], value => { states[i] = typeof value === 'function' ? value(states[i]) : value; }];
    },
    useRef: value => ({ current: value }), useEffect() {}, useCallback: fn => fn,
  };
  const jsx = (type, props) => ({ type, props });
  const widget = load('frontend/src/layouts/ChatbotWidget.tsx', {
    react, 'react/jsx-runtime': { jsx, jsxs: jsx },
    '../components/ChatMessageInput.css': {},
    '../components/ChatSendButton.css': {},
    '../components/AIIdentity': { AIIdentity: 'AIIdentity' },
    '../features/chat/BookingDrawer': { BookingDrawer: 'BookingDrawer' },
    '../features/chat/AssistantTurnMetrics': { AssistantTurnMetrics: 'AssistantTurnMetrics' },
    'lucide-react': {}, 'react-redux': { useDispatch: () => () => {}, useSelector: f => f({ layout: { isChatOpen: true }, auth: { user: mode === 'authenticated' ? { id: 'auth-1', full_name: 'Nguyễn An', phone: '0912345678' } : null } }) },
    '../features/chat/AssistantMessage': {},
    '../features/chat/ChatHistoryPanel': { ChatHistoryPanel: 'ChatHistoryPanel' },
    '../features/chat/ChatAccessGate': { ChatAccessGate: 'ChatAccessGate' },
    '../features/chat/SosButton': { SosButton: 'SosButton' },
    '../features/patient-profiles/PatientSelector': {
      PatientSelector: 'PatientSelector',
    },
    '../features/patient-profiles/usePatientSelection': {
      usePatientSelection: () => ({ profileId: '', selectedProfile: null, profiles: [], loading: false, error: '' }),
    },
    '../features/coordinator/PatientUpdates': { PatientUpdates: 'PatientUpdates' },
    '../features/chat/profile': { readGuestProfile: () => mode === 'locked' || mode === 'authenticated' ? null : { name: 'Nguyễn An', phone: '0912345678' }, saveGuestProfile() {}, GUEST_PROFILE_EVENT: 'guest-profile' },
    '../app/store': {}, '../features/chat/api': {
      checkAgentStatus: async () => true, submitBooking() {},
      streamChat: async opts => {
        assert.equal(opts.profile.name, 'Nguyễn An');
        assert.equal(opts.profile.phone, '0912345678');
        if (mode === 'partial') {
          opts.onToken('partial');
          opts.onMetadata({ ats_level: 4, booking_intake: { required: true } });
        }
        if (mode === 'success' || mode === 'authenticated') {
          opts.onToken('Xin chào!');
          opts.onMetadata({ ats_level: null, workflow_status: 'FAQ_ANSWERED' });
          return;
        }
        throw new Error('offline');
      },
      sendChat: async () => { calls++; throw new Error('offline'); },
    },
  });
  const tree = widget.ChatbotWidget({ embedded: true });
  function findForm(node) {
    if (!node || typeof node !== 'object') return;
    if (node.type === 'form') return node;
    for (const child of [node.props?.children].flat(Infinity)) {
      const found = findForm(child); if (found) return found;
    }
  }
  findForm(tree).props.onSubmit({ preventDefault() {} });
  await new Promise(resolve => setTimeout(resolve, 0));
  if (mode === 'locked') {
    assert.equal(states[3].length, 1);
    assert.equal(calls, 0);
    return;
  }
  const last = states[3].at(-1);
  assert.equal(states[4], false);
  assert.match(states[5], /^web-/);
  if (mode === 'success' || mode === 'authenticated') {
    assert.equal(last.text, 'Xin chào!');
    assert.equal(last.metadata.ats_level, null);
    assert.equal(calls, 0);
  } else {
    assert.equal(last.error, true);
    assert.equal(last.metadata, undefined);
    assert.equal(calls, mode === 'partial' ? 0 : 1);
    assert(!last.text.includes('ATS'));
  }
}
function gateTests() {
  const profileModule = load('frontend/src/features/chat/profile.ts', {});
  assert.equal(profileModule.normalizeChatProfile('a', 'abc'), null);
  assert.equal(profileModule.normalizeChatProfile('  Nguyễn   An ', '0912 345 678').phone, '0912345678');
  const jsx = (type, props) => ({ type, props });
  for (const guestMode of [false, true]) {
    const states = [];
    let accepted;
    const gate = load('frontend/src/features/chat/ChatAccessGate.tsx', {
      react: { useState(initial) {
        const index = states.length;
        states.push([guestMode, 'Nguyễn An', '0912 345 678', ''][index] ?? initial);
        return [states[index], value => { states[index] = value; }];
      } },
      'react/jsx-runtime': { jsx, jsxs: jsx }, 'lucide-react': {},
      'react-router-dom': { Link: 'Link', useLocation: () => ({ pathname: '/patient/consultation' }) },
      './profile': profileModule,
    });
    const tree = gate.ChatAccessGate({ onGuest: profile => { accepted = profile; } });
    const nodes = [];
    const walk = node => {
      if (!node || typeof node !== 'object') return;
      nodes.push(node);
      [node.props?.children].flat(Infinity).forEach(walk);
    };
    walk(tree);
    if (guestMode) {
      nodes.find(node => node.type === 'form').props.onSubmit({ preventDefault() {} });
      assert.equal(accepted.name, 'Nguyễn An');
      assert.equal(accepted.phone, '0912345678');
    } else {
      assert(nodes.find(node => node.type === 'Link').props.to.includes('returnTo='));
      assert(nodes.some(node => node.type === 'button'));
    }
  }
  console.log('Access gate: login return, guest name/phone form, and profile validation passed.');
}
(async () => {
  gateTests();
  await transportTests();
  await widgetTest('offline'); await widgetTest('partial'); await widgetTest('success'); await widgetTest('locked'); await widgetTest('authenticated');
  console.log('Widget: failed APIs show error without clinical metadata; interrupted stream is not replayed; greeting preserved.');
})().catch(error => { console.error(error); process.exitCode = 1; });
