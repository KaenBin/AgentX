/* Readiness is returned by the server, never inferred from a quiz percentage. */
function saveLearning(session) {
  S.learning_sessions = [...(S.learning_sessions || []).filter(s => s.id !== session.id), session];
}

function readinessView(c) {
  selected = c.id;
  const session = (S.learning_sessions || []).find(s => s.course_id === c.id && s.user_id === S.user.id);
  const objectives = session?.objectives || c.content.readiness.objectives;
  const activity = session?.activity;
  const label = session?.state || 'not_started';
  $('content').innerHTML = `${demoWalkthroughHtml(c, session)}<div class="grid"><section>
    <div class="card"><span class="tag">${esc(label.replaceAll('_', ' '))}</span>
      <h2>${esc(c.title)}</h2><label for="course">Choose a course</label>
      <select id="course">${S.courses.filter(x => x.status === 'published').map(x => `<option value="${x.id}" ${x.id === c.id ? 'selected' : ''}>${esc(x.title)}</option>`).join('')}</select>
      <p>${session ? 'Your next activity follows your saved evidence. Each critical step must be demonstrated in a fresh case.' : 'Start with a diagnostic, review the steps you miss, then apply them in different cases.'}</p>
      <p class="muted">Source: ${esc(session?.source_title || S.documents.find(d => d.id === c.document_id)?.title)} · Rule version ${c.content.readiness.rule_version}</p>
      ${!activity && !['ready', 'blocked', 'superseded', 'needs_trainer'].includes(label) ? '<button id="continue-learning">'+(session ? 'Coach me through the next step' : 'Start readiness practice')+'</button>' : ''}
      ${label === 'ready' ? '<p>You demonstrated the required steps in this procedure version. This is training evidence, not professional certification.</p>' : ''}
      ${label === 'blocked' ? '<p>This source or course is no longer approved. Ask your trainer for current material.</p>' : ''}
      ${label === 'needs_trainer' ? '<p>The available fresh cases are exhausted. Your trainer has a saved review item. Further reassessment needs a newly approved course.</p>' : ''}
      <p id="selection-reason" class="muted"></p>
    </div>
    ${activity ? learningActivityHtml(activity) : ''}
    ${session ? '<div class="card"><h3>Ask your trainer</h3><form id="learning-question"><label for="review-question">Question or uncertain policy detail</label><textarea id="review-question" required maxlength="2000"></textarea><button>Save review request</button></form></div>' : ''}
    ${(session?.reviews || []).map(r => `<div class="card"><span class="tag">${esc(r.status)}</span><p>${esc(r.reason)}</p>${r.resolution ? `<p><b>Trainer guidance</b><br>${esc(r.resolution)}</p>` : '<p class="muted">Saved for your trainer.</p>'}</div>`).join('')}
  </section><aside>${decisionPanelHtml(session)}<div class="card"><h2>Evidence by objective</h2>
    <p class="muted">Target: ${c.content.readiness.threshold}% of objectives and every critical step demonstrated. Reading a lesson alone does not count.</p>
    ${objectives.map(o => `<div class="source"><b>${esc(o.title)}</b> ${o.critical ? '<span class="tag">Critical</span>' : ''}<p>${o.carried_from_session ? 'Earlier evidence accepted by trainer for this unchanged objective' : o.demonstrated ? 'Demonstrated in a fresh case' : o.needs_trainer ? 'Trainer support needed' : 'Not yet demonstrated'}</p>
    ${o.refresh_required && !o.demonstrated ? '<p>Changed procedure step: fresh practice required</p>' : ''}
    ${o.diagnostic_correct !== undefined && o.diagnostic_correct !== null ? `<small>Diagnostic: ${o.diagnostic_correct ? 'correct' : 'gap identified'}</small>` : ''}
    ${(o.evidence || []).map(e => `<p class="muted">${esc(e.kind)} · ${e.correct === null ? 'reviewed' : e.correct ? 'correct' : 'needs practice'}</p>`).join('')}</div>`).join('')}
  </div></aside></div>`;
  $('course').onchange = e => changeCourse(e.target.value);
  if ($('continue-learning')) $('continue-learning').onclick = e => run(e.currentTarget, async () => {
    $('selection-reason').textContent = 'Checking your saved evidence and choosing an eligible activity…';
    announce($('selection-reason').textContent);
    const current = session || await api('/api/learning/start', {course_id:c.id});
    saveLearning(current);
    let response;
    try { response = await api(`/api/learning/${current.id}/next`, {}); }
    catch (error) { $('selection-reason').textContent = 'Could not load the next step. Retry to resume your saved progress.'; throw error; }
    saveLearning(response.session);
    if (tab !== 'learn' || selected !== c.id) return;
    readinessView(c);
    $('selection-reason').textContent = `${response.selection_mode === 'gateway' ? 'Agent selected' : response.selection_mode === 'demo' ? 'Offline simulation selected' : 'Resumed'}: ${response.reason}`;
    announce($('selection-reason').textContent);
  }, '#learning-answer h2, #content h2');
  if ($('learning-answer')) $('learning-answer').onsubmit = e => {
    e.preventDefault();
    run(e.submitter, async () => {
      const answer = activity.kind === 'lesson' ? null : Number(new FormData(e.target).get('answer'));
      const response = await api(`/api/learning/${session.id}/answer`, {issued_id:activity.id, answer});
      saveLearning(response.session);
      readinessView(c);
      $('selection-reason').textContent = `${response.correct === null ? '' : response.correct ? 'Correct. ' : 'Review this step. '}${response.feedback}`;
      announce($('selection-reason').textContent);
    }, '#continue-learning, #content h2');
  };
  if ($('learning-question')) $('learning-question').onsubmit = e => {
    e.preventDefault();
    run(e.submitter, async () => {
      saveLearning(await api(`/api/learning/${session.id}/review`, {reason:$('review-question').value}));
      readinessView(c);
      $('selection-reason').textContent = 'Review request saved for your trainer.';
      announce($('selection-reason').textContent);
    }, '#review-question');
  };
}

function learningActivityHtml(activity) {
  return `<form id="learning-answer" class="card"><span class="tag">${esc(activity.kind)}</span><h2>${esc(activity.title)}</h2>
    ${activity.kind === 'lesson' ? `<p class="text">${esc(activity.text)}</p><p class="muted">Approved source · Section ${activity.source_section}</p><button>I have reviewed this step</button>` :
      `<fieldset style="border:0;padding:0"><legend>${esc(activity.prompt)}</legend>${activity.options.map((o,i) => `<label class="option"><input type="radio" name="answer" value="${i}" required><span>${esc(o)}</span></label>`).join('')}</fieldset><button>Submit my answer</button>`}
  </form>`;
}

function learningEvidenceHtml() {
  if (S.user.role === 'trainer') return trainerDashboardHtml();
  const sessions = S.learning_sessions || [];
  return sessions.length ? `<div class="card"><h2>Procedure readiness</h2>${sessions.map(s => `<details class="source"><summary>${esc(s.title)} · ${esc(S.user.role === 'trainer' ? 'Learner '+s.user_id+' · ' : '')}${esc(s.state.replaceAll('_',' '))}</summary><p>${esc(s.source_title)} · Rule ${s.rule_version}</p>${s.objectives.map(o=>`<p><b>${esc(o.title)}</b> ${o.critical ? '(critical)' : ''}: ${o.carried_from_session ? 'equivalent evidence from session '+o.carried_from_session : o.demonstrated ? 'demonstrated' : 'pending'}<br><small>${o.evidence.map(e=>`${esc(e.kind)}: ${e.correct === null ? 'reviewed' : e.correct ? 'correct' : 'needs practice'}`).join(' → ')}</small></p>`).join('')}</details>`).join('')}</div>` : '';
}

function dashboardSummary(sessions) {
  const current = sessions.filter(s => s.state !== 'superseded');
  return {
    current,
    ready: current.filter(s => s.state === 'ready').length,
    practicing: current.filter(s => ['diagnosing', 'practicing'].includes(s.state)).length,
    needsTrainer: current.filter(s => s.state === 'needs_trainer').length,
    blocked: current.filter(s => s.state === 'blocked').length,
    criticalGaps: current.reduce((n,s) => n+s.objectives.filter(o => o.critical && !o.demonstrated).length, 0),
    carried: current.reduce((n,s) => n+s.objectives.filter(o => o.carried_from_session).length, 0),
    refreshAssigned: current.reduce((n,s) => n+s.objectives.filter(o => o.refresh_required).length, 0),
    refreshRemaining: current.reduce((n,s) => n+s.objectives.filter(o => o.refresh_required && !o.demonstrated).length, 0),
    openReviews: current.reduce((n,s) => n+(s.reviews || []).filter(r => r.status === 'open').length, 0),
  };
}

function trainerSessionEvidence(s) {
  return `<details class="source" id="session-evidence-${s.id}"><summary>Learner ${s.user_id} · ${esc(s.title)} · ${esc(s.state.replaceAll('_',' '))}</summary>
    <p>${esc(s.source_title)} · readiness rule ${s.rule_version}</p>
    ${s.objectives.map(o => `<div class="source"><b>${esc(o.title)}</b>${o.critical ? ' · Critical' : ''}<p>${o.carried_from_session ? 'Prior evidence accepted from session '+o.carried_from_session : o.demonstrated ? 'Demonstrated in a fresh case' : 'Not yet demonstrated'}${o.refresh_required ? ' · Procedure refresher assigned' : ''}</p><small>${o.evidence.map(e => `${esc(e.kind)}: ${e.correct === null ? 'reviewed' : e.correct ? 'correct' : 'needs practice'}`).join(' → ') || 'No submitted activity evidence in this version.'}</small></div>`).join('')}
    <h3>Recorded decisions</h3>${(s.decisions || []).length ? [...s.decisions].reverse().map(decisionHtml).join('') : '<p>No decision records for these earlier activities.</p>'}
    ${(s.reviews || []).map(r => `<p><b>${esc(r.status)} trainer review</b> · ${esc(r.reason)}${r.resolution ? '<br>'+esc(r.resolution) : ''}</p>`).join('')}
  </details>`;
}

function trainerDashboardHtml() {
  const sessions = S.learning_sessions || [];
  const summary = dashboardSummary(sessions);
  const metrics = [[summary.ready,'Ready'],[summary.practicing,'Practicing'],[summary.needsTrainer,'Needs trainer'],[summary.blocked,'Blocked']];
  return `${rehearsalPreparationHtml()}<section class="card"><div class="eyebrow">Trainer results</div><h2>Readiness at a glance</h2>
    <p>${summary.current.length} current learner/course sessions. Counts describe recorded sessions, not all employees; superseded versions appear in history below.</p>
    <div class="dashboard-metrics">${metrics.map(([value,label]) => `<div><strong>${value}</strong><span>${label}</span></div>`).join('')}</div>
    <p><b>${summary.criticalGaps}</b> critical objective gaps · <b>${summary.openReviews}</b> open review requests on current sessions</p>
    <h3>After procedure changes</h3><p><b>${summary.carried}</b> objective records carried forward · <b>${summary.refreshAssigned}</b> refreshers assigned · <b>${summary.refreshRemaining}</b> still need fresh evidence</p>
    <p class="muted">These are counts of objective records across current sessions, not measured time saved. Readiness is determined by the backend.</p>
    <label for="dashboard-status">Filter current sessions</label><select id="dashboard-status" onchange="filterDashboard(this.value)"><option value="all">All current sessions</option><option value="ready">Ready</option><option value="practicing">Practicing</option><option value="needs_trainer">Needs trainer</option><option value="blocked">Blocked</option><option value="gaps">Critical gaps</option><option value="reviews">Open reviews</option></select>
    <div class="table-card"><table><thead><tr><th>Learner / procedure</th><th>Status</th><th>Critical gaps</th><th>Evidence</th></tr></thead><tbody>
      ${summary.current.map(s => `<tr data-dashboard-state="${esc(s.state)}" data-dashboard-gaps="${s.objectives.some(o => o.critical && !o.demonstrated)}" data-dashboard-reviews="${(s.reviews || []).some(r => r.status === 'open')}"><td>Learner ${s.user_id}<br>${esc(s.title)}</td><td>${esc(s.state.replaceAll('_',' '))}</td><td>${s.objectives.filter(o => o.critical && !o.demonstrated).map(o => esc(o.title)).join(', ') || 'None'}</td><td><button onclick="openSessionEvidence(${s.id})">View evidence</button></td></tr>`).join('')}
    </tbody></table></div><p id="dashboard-empty" ${summary.current.length ? 'hidden' : ''}>No sessions match this view.</p>
    <p class="muted">Summary counts above always cover all current sessions. The filter changes the table only.</p>
    <h3>Evidence behind the results</h3>${summary.current.map(trainerSessionEvidence).join('')}
    <details><summary>Superseded session history (${sessions.length-summary.current.length})</summary>${sessions.filter(s => s.state === 'superseded').map(trainerSessionEvidence).join('') || '<p>No superseded sessions.</p>'}</details></section>`;
}

function filterDashboard(value) {
  const rows = document.querySelectorAll('[data-dashboard-state]');
  let visible = 0;
  rows.forEach(row => {
    const match = value === 'all' || (value === 'practicing' ? ['diagnosing','practicing'].includes(row.dataset.dashboardState) : value === 'gaps' ? row.dataset.dashboardGaps === 'true' : value === 'reviews' ? row.dataset.dashboardReviews === 'true' : row.dataset.dashboardState === value);
    row.hidden = !match;
    if (match) visible++;
  });
  $('dashboard-empty').hidden = visible > 0;
}

function openSessionEvidence(id) {
  const detail = $('session-evidence-'+id);
  if (!detail) return;
  detail.open = true;
  detail.scrollIntoView({block:'start'});
  detail.querySelector('summary').focus();
}

function trainerReviewsHtml() {
  if (S.user.role !== 'trainer') return '';
  return `<div class="card"><h2>Learner review queue</h2>${(S.learning_sessions || []).flatMap(s => s.reviews.map(r => `<div class="source"><b>Learner ${s.user_id} · ${esc(s.title)}</b><p>${esc(r.reason)}</p><span class="tag">${esc(r.status)}</span>${r.status === 'open' ? `<label for="resolution-${r.id}">Trainer guidance</label><textarea id="resolution-${r.id}" maxlength="2000"></textarea><button onclick="resolveLearningReview(this,${r.id})">Record guidance</button>` : `<p>${esc(r.resolution)}</p>`}</div>`)).join('') || '<p>No saved review requests.</p>'}<p class="muted">Recording guidance does not award a pass. Exhausted cases need a new approved course.</p></div>`;
}

function resolveLearningReview(button, id) {
  run(button, async () => {
    await api(`/api/learning/reviews/${id}/resolve`, {resolution:$('resolution-'+id).value});
    await refresh();
  });
}
