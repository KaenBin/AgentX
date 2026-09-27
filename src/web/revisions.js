/* Procedure drafts require a trainer's explicit source, content and mapping approval. */
function revisionStudioHtml() {
  if (S.user.role !== 'trainer') return '';
  const current = S.courses.filter(c => c.status === 'published' && c.content.readiness && S.documents.find(d => d.id === c.document_id)?.approved);
  return `<div class="card"><h2>Procedure updates</h2><p>Compare the source and training content, then approve which objectives need fresh practice. Earlier results remain in history.</p>
    <label for="revision-base">Current course</label><select id="revision-base">${current.map(c=>`<option value="${c.id}">${esc(c.title)}</option>`).join('')}</select>
    ${current.length ? '<button onclick="prepareDemoRevision(this)">Prepare fictional receipt policy update</button><details><summary>Prepare your own revision</summary><label for="revision-title">New version title</label><input id="revision-title"><label for="revision-source">New source text</label><textarea id="revision-source"></textarea><label for="revision-content">Reviewed course JSON with readiness objectives</label><textarea id="revision-content" style="min-height:240px"></textarea><button onclick="prepareCustomRevision(this)">Save revision for review</button></details>' : '<p>No current readiness course is available.</p>'}
    <p class="muted">Preparing a revision saves an unapproved draft. The fictional example adds a written Finance exception when a supplier cannot replace a receipt.</p></div>
    ${(S.procedure_revisions || []).map(r=>`<div class="card"><span class="tag">${esc(r.status)} · Version ${r.version}</span><h3>${esc(r.new_title)}</h3><p>Previous: ${esc(r.old_title)} · ${r.learner_count} existing learning session(s)</p>
    <details><summary>Source changes</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere">${esc(r.comparison.diff || 'No source text changes')}</pre></details>
    <details><summary>Review the complete new source</summary><p class="text">${esc(r.new_source)}</p></details>
    <details><summary>Review new lessons and answer keys</summary>${r.new_content.readiness.objectives.map(o=>`<details class="source"><summary>${esc(o.title)} · Source section ${o.source_section}</summary><p>${esc(o.lesson)}</p>${[o.diagnostic,...o.reassessments].map(q=>`<p><b>${esc(q.prompt)}</b></p><ul>${q.options.map((option,index)=>`<li>${esc(option)}${index===q.answer?' — approved answer':''}</li>`).join('')}</ul><p>${esc(q.explanation)}</p>`).join('')}</details>`).join('')}</details>
    ${r.comparison.objectives.map(o=>`<div class="source"><b>${esc(o.title)}</b><p>${esc(o.reason)}</p><label><input type="checkbox" data-revision="${r.id}" data-objective="${esc(o.id)}" ${o.required_refresh?'checked disabled':''} ${r.status!=='draft'?'disabled':''}> Require fresh practice</label></div>`).join('')}
    ${r.comparison.removed_objectives.length ? `<p>Removed objectives: ${esc(r.comparison.removed_objectives.join(', '))}. Their earlier evidence stays in history.</p>` : ''}
    ${r.status === 'draft' ? (r.can_activate ? `<label class="option"><input type="checkbox" id="approve-revision-${r.id}"><span>I reviewed the source, lessons, cases and answer keys. I approve carrying forward demonstrated evidence for unchecked, unchanged objectives.</span></label><button onclick="activateRevision(this,${r.id})">Approve version and assign refreshers</button>` : '<p>This draft is based on a withdrawn or superseded version. Prepare a new revision from the current course.</p>') : `<p>Approved mapping: refresh ${esc(JSON.parse(r.affected).join(', ') || 'none')}; preserve equivalent evidence for ${esc(JSON.parse(r.equivalent).join(', ') || 'none')}.</p>`}
    </div>`).join('')}`;
}

function standardDocuments() {
  return S.documents.filter(d=>!(S.procedure_revisions||[]).some(r=>(r.status==='draft'&&r.new_document_id===d.id)||(r.status==='activated'&&r.old_document_id===d.id)));
}
function standardCourses() {
  return S.courses.filter(c=>!(S.procedure_revisions||[]).some(r=>r.new_course_id===c.id||r.old_course_id===c.id));
}

function prepareDemoRevision(button) {
  run(button, async()=>{await api('/api/revisions/demo',{course_id:Number($('revision-base').value)}); await refresh();});
}
function prepareCustomRevision(button) {
  run(button, async()=>{
    await api('/api/revisions/draft',{old_course_id:Number($('revision-base').value),title:$('revision-title').value,body:$('revision-source').value,content:JSON.parse($('revision-content').value)});
    await refresh();
  });
}
function activateRevision(button,id) {
  run(button,async()=>{
    if(!$('approve-revision-'+id).checked) throw Error('Review the source, training content and evidence mapping, then check the approval box.');
    const affected_ids=[], equivalent_ids=[];
    document.querySelectorAll(`[data-revision="${id}"]`).forEach(el=>(el.checked?affected_ids:equivalent_ids).push(el.dataset.objective));
    await api(`/api/revisions/${id}/activate`,{affected_ids,equivalent_ids});
    await refresh();
  });
}
