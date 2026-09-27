const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../src/web/readiness.js'), 'utf8'), context);

test('retired readiness is excluded; carried and pending refresher evidence remain distinct', () => {
  const sessions = [
    {state:'superseded', objectives:[{critical:true, demonstrated:true}], reviews:[{status:'open'}]},
    {state:'ready', objectives:[{critical:true, demonstrated:true, carried_from_session:1}, {critical:true, demonstrated:true, refresh_required:true}], reviews:[]},
    {state:'diagnosing', objectives:[{critical:true, demonstrated:false, refresh_required:true}], reviews:[{status:'open'}]},
    {state:'blocked', objectives:[{critical:true, demonstrated:false}], reviews:[]},
    {state:'needs_trainer', objectives:[{critical:false, demonstrated:false}], reviews:[{status:'resolved'}]},
  ];
  const s = context.dashboardSummary(sessions);
  assert.equal(s.current.length, 4);
  assert.equal(s.ready, 1);
  assert.equal(s.practicing, 1);
  assert.equal(s.blocked, 1);
  assert.equal(s.needsTrainer, 1);
  assert.equal(s.criticalGaps, 2);
  assert.equal(s.carried, 1);
  assert.equal(s.refreshAssigned, 2);
  assert.equal(s.refreshRemaining, 1);
  assert.equal(s.openReviews, 1);
});

test('empty state does not invent readiness or participants', () => {
  const s = context.dashboardSummary([]);
  assert.equal(s.current.length, 0);
  for (const [key, value] of Object.entries(s)) if (key !== 'current') assert.equal(value, 0);
});
