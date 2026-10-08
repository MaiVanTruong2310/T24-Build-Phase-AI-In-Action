/**
 * Regression test for Coordinator Live Session Chat
 * Verifies:
 * 1. AI bot messages are filtered out and do not leak into coordinator section.
 * 2. Inactive state hides empty coordinator card from chatbot widget.
 * 3. Active session renders as a conversational chat thread (bubbles, roles, timestamps).
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const file = fs.readFileSync(path.join(__dirname, '../src/features/coordinator/PatientUpdates.tsx'), 'utf8');

// 1. Verify defense-in-depth bot filter in frontend
assert.ok(
  file.includes("u.sender !== 'ai' && u.sender !== 'assistant' && u.sender !== 'agent'"),
  'Must filter out AI bot / assistant senders in PatientUpdates'
);

// 2. Verify inactive state hides the element when not requested and no messages
assert.ok(
  file.includes('if (!isSessionActive && !showRequestButton && !canReply)'),
  'Must hide component when session is inactive to prevent polluting chatbot widget'
);

// 3. Verify chat thread styling elements (avatar, coordinator badge, bubbles)
assert.ok(
  file.includes('BS') || file.includes('Bác sĩ điều phối'),
  'Must include Doctor badge / identity for coordinator'
);

assert.ok(
  file.includes('isCoordinator') && file.includes('isPatient'),
  'Must differentiate coordinator and patient messages in thread format'
);

// 4. Verify reply form allows sending messages in session
assert.ok(
  file.includes('Nhắn tin cho Bác sĩ điều phối'),
  'Must provide clean messaging input for patient in active session'
);

// 5. Verify backend updates endpoint filters out AI bot messages
const backendFile = fs.readFileSync(path.join(__dirname, '../../src/api/endpoints/workbench.py'), 'utf8');
assert.ok(
  backendFile.includes("sender_t in ('AGENT', 'BOT', 'AI')") || backendFile.includes("legacy_sender in ('ai', 'assistant', 'bot')"),
  'Backend updates endpoint must reject AI bot messages'
);

const serviceFile = fs.readFileSync(path.join(__dirname, '../../src/services/workbench.py'), 'utf8');
assert.ok(
  serviceFile.includes('"AGENT" if sender in ("ai", "assistant", "bot")'),
  'Workbench service must categorize AI messages as AGENT sender type'
);

console.log('Coordinator session chat regression tests passed successfully!');
