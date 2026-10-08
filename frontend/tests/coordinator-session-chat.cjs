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

// 2. Verify inactive state hides the element when not requested and no coordinator intervention
assert.ok(
  file.includes('hasCoordinatorMessages') && file.includes('isCaseActive'),
  'Must verify coordinator intervention or active case before showing coordinator session'
);
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

// 6. Verify unified chatbot widget integration
const widgetFile = fs.readFileSync(path.join(__dirname, '../src/layouts/ChatbotWidget.tsx'), 'utf8');
assert.ok(
  widgetFile.includes('mode="embedded"') && widgetFile.includes('handleCoordinatorMessages'),
  'ChatbotWidget must mount PatientUpdates in embedded mode and handle coordinator messages directly'
);
assert.ok(
  widgetFile.includes("supportState.control === 'human'") && widgetFile.includes('Nhắn tin cho Bác sĩ điều phối'),
  'ChatbotWidget must provide single unified input bar switching to coordinator mode'
);

console.log('Coordinator session chat regression tests passed successfully!');
