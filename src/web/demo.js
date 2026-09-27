/* Presenter guidance uses real saved state. It never awards or submits evidence. */
function rehearsalPreparationHtml() {
  return `<section class="card"><h2>Prepare a fresh demo</h2><p>Create a separate fictional workspace at the original policy. Existing records are preserved. This browser's tabs share the selected workspace.</p><button onclick="startRehearsal(this,'gateway')">Start fresh live demo</button> <button class="secondary" onclick="startRehearsal(this,'demo')">Start fresh offline demo</button><p class="muted">Opens as learner. Use trainer / LearnDemo2026! for the policy update. Live mode uses the configured gateway; offline mode makes deterministic selections.</p></section>`;
}

function startRehearsal(button, mode) {
  run(button, async () => {
    await api('/api/rehearsal/start', {mode});
    selected = null; tab = 'learn'; result = null;
    await refresh();
  });
}

async function loadRehearsalBanner() {
  try { renderRehearsalBanner(await api('/api/rehearsal/context')); } catch (_) { /* Login remains available. */ }
}

function renderRehearsalBanner(context = S) {
  let banner = $('rehearsal-banner');
  if (!banner) {
    banner = document.createElement('section');
    banner.id = 'rehearsal-banner';
    document.querySelector('main').before(banner);
  }
  banner.hidden = !context?.rehearsal;
  banner.innerHTML = context?.rehearsal ? `<div class="card"><b>Fictional rehearsal · ${esc(context.mode)}</b><p>Separate demo records. Existing workspace progress is preserved.</p><button onclick="exitRehearsal(this)">Return to main workspace</button></div>` : '';
}

document.addEventListener('DOMContentLoaded', loadRehearsalBanner);

function exitRehearsal(button) {
  run(button, async () => {
    await api('/api/rehearsal/exit', {});
    selected = null; tab = 'progress'; result = null;
    try { await refresh(); } catch (e) { S = null; renderRehearsalBanner(); loginView(); }
  });
}

function demoWalkthroughHtml(course, session) {
  if (!course.title.toLowerCase().includes('fictional')) return '';
  const objectives = session?.objectives || [];
  const carried = objectives.filter(o => o.carried_from_session).length;
  const demonstrated = objectives.filter(o => o.demonstrated).length;
  return `<details class="card demo-guide"><summary>Demo walkthrough · from a missed step to an updated policy</summary>
    <p>Aim for a three-minute story using the fictional expense procedure. Every result comes from saved learner evidence.</p>
    <ol class="demo-steps">
      <li><b>Find the gap.</b> Use a learner who has not started the original pilot. Complete the diagnostic and deliberately miss receipt evidence.</li>
      <li><b>Show the agent's choice.</b> Continue the learning path. Point to the decision card: selected activity, prior evidence and approved source. Review the missed step.</li>
      <li><b>Prove understanding.</b> Complete the fresh cases. The backend requires every critical objective; reading alone does not earn readiness.</li>
      <li><b>Change the procedure.</b> Sign in as trainer. In Trainer studio, prepare the fictional receipt update, review its source and cases, and approve the refresh mapping.</li>
      <li><b>Retrain only the changed skill.</b> Return as the same learner. Show three carried objectives, then review and demonstrate the changed receipt rule.</li>
    </ol>
    <p class="demo-snapshot"><b>Current course:</b> ${demonstrated}/${objectives.length || course.content.readiness.objectives.length} objectives demonstrated · ${carried} carried forward${session ? ' · '+esc(session.state.replaceAll('_',' ')) : ' · not started'}</p>
    <p class="muted">This guide does not reset data or complete activities. If the policy is already updated, use a fresh demo database to rehearse the full story. An offline selection is labeled separately from a live agent choice.</p>
  </details>`;
}

function decisionHtml(d) {
  const mode = {gateway:'Live agent selected', demo:'Offline simulation selected', backend:'Backend selected'}[d.mode] || 'Saved selection';
  const evidence = d.refresh_required ? 'The trainer approved a procedure change requiring fresh practice.' : d.reassessment_count ? `${d.reassessment_count} earlier fresh case(s) did not establish this objective.` : d.diagnostic_correct === false ? 'The diagnostic identified a gap in this objective.' : d.diagnostic_correct === true ? 'The diagnostic was correct; a fresh case must still demonstrate the skill.' : 'No diagnostic evidence had been recorded for this objective.';
  const outcome = !d.submitted ? 'Awaiting learner response' : d.kind === 'lesson' ? 'Lesson reviewed · readiness not awarded' : d.kind === 'diagnostic' ? (d.correct ? 'Diagnostic correct · fresh evidence still required' : 'Diagnostic gap identified') : d.correct ? 'Demonstrated in a fresh case' : 'More practice needed';
  return `<article class="decision-record"><span class="tag">${esc(mode)}</span><h3>${esc(d.objective_title)}</h3>
    <p><b>Chosen activity</b><br>${esc(d.kind)} · ${esc(d.reason)}</p>
    <p><b>Evidence at selection</b><br>${esc(evidence)} ${d.critical ? 'This is a critical objective.' : ''}</p>
    <p><b>Approved source at selection</b><br>${esc(d.source_title)} · Section ${d.source_section}</p>
    <p><b>Recorded outcome</b><br>${esc(outcome)}</p>
    <small>${d.eligible_count} eligible activity choice(s) · ${new Date(d.created*1000).toLocaleString()}</small></article>`;
}

function decisionPanelHtml(session) {
  const decisions = [...(session?.decisions || [])].reverse();
  return `<div class="card decision-panel"><div class="eyebrow">Visible decisions</div><h2>Why this next step?</h2>
    ${decisions.length ? decisionHtml(decisions[0]) : '<p>Your next coaching selection will appear here with the evidence and source behind it. Earlier activities without a saved decision are not reconstructed.</p>'}
    ${decisions.length > 1 ? `<details><summary>Earlier decisions (${decisions.length-1})</summary>${decisions.slice(1).map(decisionHtml).join('')}</details>` : ''}
    <p class="muted">Reasons summarize saved evidence and backend rules. They are not the model's private reasoning. The backend validates eligibility and grades answers.</p></div>`;
}
