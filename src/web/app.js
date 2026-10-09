
let S=null,tab=location.pathname==='/chat'?'ask':'learn',selected=null,result=null;
/** Find a workspace element by its DOM ID. */
const $=id=>document.getElementById(id);
/** Escape values before inserting them into HTML templates. */
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

/** Fetch JSON from the demo API and reject non-success responses with a readable error. */
async function api(path,data){const r=await fetch(path,{method:data?'POST':'GET',headers:data?{'Content-Type':'application/json'}:{},body:data?JSON.stringify(data):undefined});const x=await r.json();if(!r.ok)throw Error(typeof x.error==='string'?x.error:(typeof x.detail==='string'?x.detail:'Unable to complete this request'));return x}

/** Clear obsolete progress announcements and expose an error through the visible alert. */
function notice(e) {
 announce('');
 const element = $('notice');
 if (element) { element.className = 'error'; element.textContent = e.message || e; }
 else alert(e.message || e);
}

/** Update the persistent polite live region without moving keyboard focus. */
function announce(message) {
 const status = $('workspace-status');
 status.textContent = message;
}

/** Focus a destination, allowing headings to receive focus outside the normal Tab order. */
function focusElement(element) {
 if (!element) return;
 if (!element.matches('button,input,textarea,select,a[href],summary')) element.tabIndex = -1;
 element.focus();
}

/** Render a workspace view and place focus on its first content heading. */
function showTab(next) {
 tab = next; result = null; render();
 focusElement(document.querySelector('#content h2') || $('content'));
}

/** Render the selected course and preserve keyboard position on its replacement selector. */
function changeCourse(value) {
 selected = Number(value); result = null; learn();
 focusElement($('course'));
}

/** Disable an action during its request, expose failures, and recover lost focus without overriding a surviving focus target. Optional comma-separated selectors express focus priority. */
async function run(button, fn, focusTarget) {
 if ($('notice')) $('notice').textContent = '';
 const previousFocus = document.activeElement;
 let completed = false;
 button.disabled = true;
 try { await fn(); completed = true; } catch (error) { notice(error); }
 finally {
  button.disabled = false;
  // Keep any focus the user moved during the request; recover only lost focus.
  if (document.activeElement === document.body && (previousFocus === button || !previousFocus.isConnected)) {
   const target = completed && focusTarget && focusTarget.split(',').map(selector => document.querySelector(selector)).find(Boolean);
   focusElement(target || (button.isConnected ? button : document.querySelector('#content h2') || $('content')));
  }
 }
}

/** Render the demo login form and focus the workspace heading after successful sign-in. */
function loginView(){ $('identity').innerHTML='';$('main').innerHTML=`<div class="login"><div class="eyebrow">A workspace for growing teams</div><h1>Make company knowledge<br>second nature.</h1><p class="muted">Study approved guidance, ask for evidence, and build confidence one skill at a time.</p><form class="card" id="login"><h2>Welcome back</h2><label for="name">Username</label><input id="name" value="learner" autocomplete="username" required><label for="password">Password</label><input id="password" type="password" value="LearnDemo2026!" autocomplete="current-password" required><div id="notice" role="alert" aria-atomic="true"></div><button style="margin-top:18px;width:100%">Sign in</button><p class="muted" style="font-size:13px">Local demo accounts: learner, alex, trainer<br>Password: LearnDemo2026!<br>Example policies are fictional.</p></form></div>`;$('login').onsubmit=e=>{e.preventDefault();run(e.submitter,async()=>{await api('/api/login',{name:$('name').value,password:$('password').value});await refresh();focusElement(document.querySelector('#main > h1'));announce('Signed in.')})}}

/** Reload authenticated workspace state and render its current view and rehearsal banner. */
async function refresh(){S=await api('/api/state');render();renderRehearsalBanner()}

/** Return the selected course, falling back to the newest published course. */
function course(){return S.courses.find(c=>c.id===selected)||[...S.courses].reverse().find(c=>c.status==='published')}

/** Render role-appropriate workspace navigation and dispatch its selected content view. */
function render(){ $('main').classList.toggle('chat-view',tab==='ask'); if(tab==='manage' && S.user.role!=='trainer') tab='learn';  $('identity').innerHTML=`<span class="tag">${esc(S.mode)}</span> &nbsp; ${esc(S.user.name)} <button onclick="logout()" style="margin-left:12px">Sign out</button>`;$('main').innerHTML=`<div class="eyebrow">${S.user.role==='trainer'?'Training workspace':'Your learning workspace'}</div><h1>${S.user.role==='trainer'?'Turn knowledge into understanding.':'Build confidence,<br>one lesson at a time.'}</h1><p class="muted">Your training, grounded in approved company knowledge.</p><nav class="tabs" aria-label="Workspace">${['learn','ask','progress',...(S.user.role==='trainer'?['manage']:[])].map(t=>`<button class="${tab===t?'active':''}" ${tab===t?'aria-current="page"':''} onclick="showTab('${t}')">${{learn:'Learning path',ask:'Ask your assistant',progress:'Progress',manage:'Trainer studio'}[t]}</button>`).join('')}</nav><div id="notice" role="alert" aria-atomic="true"></div><div id="content"></div>`;({learn:learn,ask:ask,progress:progress,manage:manage}[tab])()}

/** Render server-backed readiness when available, otherwise the legacy course practice path. */
function learn(){let c=course();if(c?.content.readiness){readinessView(c);return;}if(!c){$('content').innerHTML='<div class="card">No approved courses yet. Ask your trainer to publish a course.</div>';return}selected=c.id;const attempts=S.attempts.filter(a=>a.course_id===c.id&&a.user_id===S.user.id),latest=attempts[0];const weak=latest?[...new Set(latest.feedback.filter(f=>!f.correct).map(f=>f.skill))]:[];let completed=latest&&latest.phase==='assessment'&&latest.score>=80;$('content').innerHTML=`<div class="grid"><section><div class="card"><span class="tag">${completed?'Completed':latest?'Practice in progress':'Ready to begin'}</span><h2>${esc(c.title)}</h2><label for="course">Choose a course</label><select id="course" onchange="changeCourse(this.value)">${S.courses.filter(x=>x.status==='published').map(x=>`<option value="${x.id}" ${x.id===c.id?'selected':''}>${esc(x.title)}</option>`).join('')}</select><p>${!latest?'Start with a short diagnostic. Your results help select the lessons you need.':completed?'You reached the practice target. Revisit the source whenever you need a refresher.':weak.length?'Your next step: review '+weak.length+' knowledge gap(s), then try the assessment.':'Your diagnostic looks strong. Take the assessment next.'}</p><button onclick="quiz()">${!latest?'Start diagnostic':completed?'Practice again':'Take assessment'}</button></div>${latest?c.content.lessons.map((l,i)=>`<article class="card"><span class="tag">${weak.includes(i)?'Recommended for you':'Reference lesson'}</span><h2>${esc(l.title)}</h2><div class="text">${esc(l.text)}</div><div class="source">Source: ${esc(S.documents.find(d=>d.id===c.document_id)?.title)} · Section ${l.source_section}</div></article>`).join(''):''}</section><aside><div class="card"><div class="eyebrow">Your path</div><h2>Understand. Apply. Improve.</h2><p>1. Check your starting point<br>2. Study the relevant guidance<br>3. Apply it in an assessment<br>4. Review feedback and practice</p><p class="muted">Passing target: 80%. This practice result is not professional certification.</p>${latest?`<div class="big">${latest.score}%</div><progress value="${latest.score}" max="100"></progress>`:''}</div><div class="card"><h3>Need a clearer explanation?</h3><p class="muted">Ask a question and inspect the evidence behind the answer.</p><button onclick="showTab('ask')">Ask the assistant</button></div></aside></div>`}

/** Render a diagnostic or assessment form and show saved practice feedback after submission. */
function quiz(){const c=course();const phase=S.attempts.some(a=>a.course_id===c.id&&a.user_id===S.user.id&&a.phase==='diagnostic')?'assessment':'diagnostic';const bank=phase==='diagnostic'?c.content.questions:c.content.assessment_questions;if(!bank){notice('Choose the v2 course for a separate final assessment.');return;}$('content').innerHTML=`<form id="quiz" class="card"><span class="tag">${phase}</span><h2>${esc(c.title)}</h2><p class="muted">Choose one answer per question. The diagnostic checks knowledge; the final assessment uses a different question set. Repeated attempts remain practice, not independent evidence of learning.</p>${bank.map((q,i)=>`<fieldset style="border:0;padding:0;margin:24px 0"><legend><b>${i+1}. ${esc(q.prompt)}</b></legend>${q.options.map((o,j)=>`<label class="option"><input required type="radio" name="q${i}" value="${j}"><span>${esc(o)}</span></label>`).join('')}</fieldset>`).join('')}<button>Submit answers</button></form>`;$('quiz').onsubmit=e=>{e.preventDefault();run(e.submitter,async()=>{const fd=new FormData(e.target);const r=await api('/api/attempt',{course_id:c.id,phase,answers:bank.map((_,i)=>Number(fd.get('q'+i)))});S=await api('/api/state');$('content').innerHTML=`<div class="card"><span class="tag">Attempt saved</span><h1>${r.score}%</h1><p>Next step: ${esc(r.next_action.replaceAll('_',' '))}</p>${r.feedback.map(f=>`<div class="source"><b>${f.correct?'Correct':'Review this skill'} · ${esc(f.prompt)}</b><p>${esc(f.explanation)}</p></div>`).join('')}<button onclick="showTab('learn')">Continue my learning path</button><div class="trace">Workflow: ${esc(r.trace.join(' → '))}</div></div>`})}}


/** Escape a chat exchange and render its answer with expandable source evidence. */
function messageHtml(item) {
 return `<div class="message user-message"><span class="message-label">You</span><div class="text">${esc(item.question)}</div></div><div class="message assistant-message"><span class="message-label">✦ Training coach</span><div class="text">${esc(item.answer)}</div>${(item.sources||[]).map((s,i)=>`<details class="source"><summary>[${i+1}] ${esc(s.title)} · Section ${s.section}</summary><p class="text">${esc(s.excerpt)}</p></details>`).join('')}</div>`;
}

/** Render the evidence-backed chat interface and wire keyboard submission and composer recovery. */
function ask(){
 $('content').innerHTML=`<div class="grid chat-layout"><section class="card chat-panel"><div class="chat-heading"><div><span class="eyebrow">Here to help you learn</span><h2>Your training coach</h2></div><span class="tag">● Available</span></div><div id="messages" aria-live="polite" role="log">${(S.chats||[]).length?S.chats.map(messageHtml).join(''):`<div class="chat-empty"><div class="coach-mark">✦</div><h2>What would you like to understand?</h2><p class="muted">Ask about a policy, explore an example,<br>or find out what to study next.</p><div class="suggestions"><button data-question="What should I do if my receipt is missing?">I lost an expense receipt</button><button data-question="What should I study next?">Help me choose my next lesson</button><button data-question="When do I need manager approval?">Explain manager approval</button></div></div>`}</div><form id="ask" class="composer"><label class="sr-only" for="question">Message your training coach</label><textarea id="question" rows="2" placeholder="Ask about your training…" required maxlength="2000"></textarea><div class="row"><small>Answers use approved sources · Shift + Enter for a new line</small><button type="submit" id="send">Send message ↗</button></div><div id="thinking" role="status"></div></form></section><aside><div class="card evidence-card"><div class="eyebrow">Your knowledge library</div><h2>Evidence you can inspect.</h2><p class="muted">Expand a citation to read the passage behind an answer.</p>${S.documents.map(d=>`<div class="library-item"><span>▤</span><div><b>${esc(d.title)}</b><br><small>${d.approved?'Approved source':'Awaiting approval'}</small></div></div>`).join('')}<p class="muted">Questions outside the material are referred to your trainer.</p></div><div class="card"><h3>Keep your learning moving</h3><p class="muted">A short diagnostic helps identify the lessons that matter to you.</p><button class="secondary" onclick="showTab('learn')">Open learning path →</button></div></aside></div>`;
 document.querySelectorAll('[data-question]').forEach(button=>button.onclick=()=>{$('question').value=button.dataset.question;$('question').focus()});
 $('question').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();if(!$('send').disabled)$('ask').requestSubmit()}};
 $('ask').onsubmit=e=>{e.preventDefault();const question=$('question').value.trim();if(!question)return;run($('send'),async()=>{const input=$('question');input.disabled=true;$('thinking').textContent='Checking your approved sources…';try {const response=await api('/chat',{question});S.chats=[...(S.chats||[]),{question,...response}];$('messages').innerHTML=S.chats.map(messageHtml).join('');input.value='';$('messages').scrollTop=$('messages').scrollHeight;}finally{input.disabled=false;$('thinking').textContent='';input.focus()}})};
 $('messages').scrollTop=$('messages').scrollHeight;
}

/** Render procedure evidence and the current role's separate course quiz history. */
function progress(){$('content').innerHTML=learningEvidenceHtml()+`<div class="card table-card"><h2>${S.user.role==='trainer'?'Team course quiz results':'Your course quiz attempts'}</h2>${S.attempts.length?`<table><thead><tr><th>Learner</th><th>Course</th><th>Stage</th><th>Score</th><th>Recorded</th></tr></thead><tbody>${S.attempts.map(a=>`<tr><td>${esc(a.name)}</td><td>${esc(S.courses.find(c=>c.id===a.course_id)?.title||'Archived course')}</td><td>${esc(a.phase)}</td><td>${a.score}%</td><td>${new Date(a.created*1000).toLocaleString()}</td></tr>`).join('')}</tbody></table>`:'<p>No separate course quiz attempts. Procedure readiness and its evidence appear above.</p>'}</div>`}

/** Render trainer source and course queues and wire document upload for review. */
function manage(){$('content').innerHTML=revisionStudioHtml()+trainerReviewsHtml()+`<div class="grid"><section><div class="card"><h2>Add a source document</h2><form id="upload"><label>Document title and version<input id="title" required placeholder="Expense policy v2"></label><label>Upload a text or Markdown file<input type="file" id="file" accept=".txt,.md"></label><label>Document text<textarea id="body" required placeholder="Separate sections with blank lines. Put each section heading on its first line."></textarea></label><button>Save for review</button></form></div>${standardDocuments().map(d=>`<div class="card"><div class="row"><h3>${esc(d.title)}</h3><span class="tag">${d.approved?'Approved':'Pending'}</span></div><details><summary>Review source text</summary><p class="text">${esc(d.body)}</p></details><button onclick="documentApproval(this,${d.id},${!d.approved})">${d.approved?'Withdraw approval':'Approve source'}</button> ${d.approved?`<button onclick="draft(this,${d.id})">Create course draft</button>`:''}</div>`).join('')}</section><aside><div class="card"><h2>Course review queue</h2><p class="muted">Check lesson facts, source sections, question wording and answer keys before publication. Published versions cannot be edited.</p></div>${standardCourses().map(c=>`<div class="card"><span class="tag">${esc(c.status)}</span><h3>${esc(c.title)}</h3>${c.status==='draft'?`<label>Editable course JSON<textarea id="draft${c.id}" style="min-height:330px;font-family:monospace;font-size:12px">${esc(JSON.stringify(c.content,null,2))}</textarea></label><button onclick="publish(this,${c.id})">Approve and publish</button>`:`<p>${c.content.readiness ? c.content.readiness.objectives.length+' objectives · '+c.content.readiness.objectives.reduce((n,o)=>n+o.reassessments.length,0)+' fresh cases' : c.content.lessons.length+' lessons · '+c.content.questions.length+' diagnostic · '+(c.content.assessment_questions?.length||0)+' final questions'}</p>`}</div>`).join('')}<div class="card"><h3>Recent audit events</h3>${S.events.slice(0,10).map(x=>`<p class="muted">${esc(x.action.replaceAll('_',' '))}<br><small>${new Date(x.created*1000).toLocaleString()}</small></p>`).join('')}</div></aside></div>`;$('file').onchange=async e=>{let f=e.target.files[0];if(f){if(f.size>100000){notice('File is too large');return}$('body').value=await f.text();if(!$('title').value)$('title').value=f.name}};$('upload').onsubmit=e=>{e.preventDefault();run(e.submitter,async()=>{await api('/api/document',{title:$('title').value,body:$('body').value});await refresh()})}}

/** Change source approval through the API and refresh the trainer workspace. */
function documentApproval(b,id,approved){run(b,async()=>{await api('/api/document/approve',{id,approved});await refresh()})}
/** Create a course draft from an approved document and refresh the trainer queue. */
function draft(b,id){run(b,async()=>{await api('/api/course/create',{document_id:id});await refresh()})}
/** Submit reviewed course JSON for publication and refresh workspace state. */
function publish(b,id){run(b,async()=>{await api('/api/course/publish',{id,content:JSON.parse($('draft'+id).value)});await refresh()})}
/** End the demo session, clear learner selection, and return focus to the username field. */
async function logout(){await api('/api/logout',{});S=null;selected=null;tab='learn';loginView();$('name').focus();announce('Signed out.')}refresh().catch(loginView);
