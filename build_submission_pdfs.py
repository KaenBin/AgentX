"""Build the two SMYA submission documents from reviewed as-built facts."""
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output' / 'pdf'
OUT.mkdir(parents=True, exist_ok=True)
pdfmetrics.registerFont(TTFont('Segoe', 'C:/Windows/Fonts/segoeui.ttf'))
pdfmetrics.registerFont(TTFont('SegoeBold', 'C:/Windows/Fonts/segoeuib.ttf'))
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Body', fontName='Segoe', fontSize=10.4, leading=14.5, spaceAfter=8, textColor=colors.HexColor('#263c36')))
styles.add(ParagraphStyle(name='TitleX', fontName='SegoeBold', fontSize=29, leading=34, spaceAfter=14, textColor=colors.HexColor('#254e40')))
styles.add(ParagraphStyle(name='HeadingX', fontName='SegoeBold', fontSize=15, leading=20, spaceBefore=13, spaceAfter=8, textColor=colors.HexColor('#254e40')))
styles.add(ParagraphStyle(name='SmallX', fontName='Segoe', fontSize=8.5, leading=12, spaceAfter=7, textColor=colors.HexColor('#5c6a61')))
styles.add(ParagraphStyle(name='CellX', fontName='Segoe', fontSize=9, leading=13, textColor=colors.HexColor('#263c36')))

def p(text, style='Body'):
    return Paragraph(escape(text).replace('\n', '<br/>'), styles[style])

def heading(text): return p(text, 'HeadingX')
def table(rows, widths):
    t = Table([[p(str(x), 'CellX') for x in row] for row in rows], colWidths=widths, hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e6eddf')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9),('LINEBELOW',(0,0),(-1,-1),0.4,colors.HexColor('#d5dfd3'))]))
    return t

def page(title, subtitle):
    return [p('AGENTX LEARN  /  SHOW ME YOUR AGENTS', 'SmallX'), p(title,'TitleX'), p(subtitle,'SmallX'), Spacer(1,8)]

def footer(canvas, doc):
    canvas.setStrokeColor(colors.HexColor('#d5dfd3')); canvas.line(48,45,A4[0]-48,45)
    canvas.setFont('Segoe',8); canvas.setFillColor(colors.HexColor('#5c6a61'))
    canvas.drawString(48,31,'AgentX Learn | Submission documents | 27 September 2026')
    canvas.drawRightString(A4[0]-48,31,str(doc.page))

def build(name, story):
    path = OUT / name
    SimpleDocTemplate(str(path), pagesize=A4, rightMargin=48,leftMargin=48,topMargin=42,bottomMargin=61,title=name.replace('_',' ').replace('.pdf',''),author='AgentX Learn').build(story,onFirstPage=footer,onLaterPages=footer)
    reader=PdfReader(path)
    print(name, len(reader.pages), 'pages')
    assert all((page.extract_text() or '').strip() for page in reader.pages)

b=page('Business proposal','A focused pilot for procedure readiness and targeted refreshers')
b += [heading('The problem'),p('A completed course does not establish whether an employee can apply every critical procedure step. When guidance changes, that completion record may also conceal outdated understanding. Supervisors need to know which steps still need help and which prior evidence remains applicable.'),
heading('Our proposition'),p('AgentX Learn connects approved guidance, learner diagnostics, targeted coaching and fresh scenario assessment. The agent selects an eligible activity using saved learner evidence. The backend grades the answer and checks readiness. When a procedure changes, a trainer reviews the update and approves which objectives require fresh practice.'),
heading('First customer and use case'),p('The proposed first buyer is an operations or finance lead in a small or medium-sized organization with recurring procedure questions and avoidable corrections. The initial use case is expense reimbursement. This customer hypothesis has not yet been validated through interviews or a paid pilot.'),
table([['Stakeholder','Value to validate'],['Employee','Focused practice on an observed gap, with approved guidance close at hand.'],['Trainer / process owner','Evidence by objective, visible critical gaps and a saved human-review queue.'],['Operations lead','A traceable response to procedure changes without automatically repeating every objective.']],[130,369]),
heading('Small initial adoption decision'),p('Start with one process owner, one employee role and one procedure. Interview the owner and two or three employees about recurring errors and teaching effort. Proceed only if the problem is material and the owner can review the source, objectives and cases.')]
b += [PageBreak()] + page('The working solution','Implemented prototype and observed fictional demonstration')
b += [heading('The demonstration'),p('The learner deliberately missed receipt evidence in a diagnostic. The live agent selected the approved receipt lesson, then a different scenario. Fresh cases established all four original objectives. A trainer then reviewed a revised policy permitting a written Finance exception when the supplier cannot replace a receipt. Three unchanged objectives carried forward; the receipt objective required an updated lesson and new case. Passing that case restored readiness for version two.'),
heading('Why this is useful'),table([['Design choice','Practical distinction'],['Evidence, not completion alone','Readiness requires fresh assessment evidence and every critical objective.'],['Policy-version awareness','Historical results remain intact while affected objectives are reassessed.'],['Inspectable choices','Each new activity records selection mode, evidence at selection, source reference and outcome.'],['Human approval','The trainer reviews changed content and approves evidence carryover; the model cannot publish policy.']],[145,354]),
p('These are design distinctions, not claims of market exclusivity. No external competitor benchmark has been performed.' ,'SmallX'),
heading('What is working today'),p('The local prototype includes learner and trainer views, approved-source chat, persistent learning sessions, deterministic grading, a review queue, procedure revisions, targeted refreshers, a results dashboard and separate live/offline rehearsals. It runs with FastAPI, plain JavaScript and SQLite plus a configured model gateway.'),
heading('Evidence achieved'),p('The latest recorded checks passed 71 Python tests and 2 dashboard tests. Three consecutive gateway smoke runs passed after bounded JSON recovery. A browser rehearsal completed the original and updated fictional procedure. These results demonstrate implementation behavior; they do not establish improved retention, reduced trainer workload or production reliability.')]
b += [PageBreak()] + page('Pilot and commercial path','Proposed evaluation and economics, not achieved business outcomes')
b += [heading('A fair first pilot'),p('Compare the workflow with the organization\'s existing training or document Q&A process using comparable unseen cases. Keep evaluation cases separate from training examples. Have a trainer review scoring and, where practical, score without knowing the condition. For a small volunteer group, report exploratory results and raw counts rather than broad causal claims.'),
table([['Measure','Proposed decision criterion'],['Critical mistakes','Fewer missed mandatory steps on unseen cases; show per-person results.'],['Trainer effort','Lower active preparation, review and correction time without worse reviewed quality.'],['Grounded answers','Review supported and unsupported questions for factual accuracy, citations and appropriate referral.'],['Retention','Repeat equivalent unseen cases after a defined delay agreed with the process owner.'],['Operating cost','Track model calls, latency, hosting and content-maintenance effort per completed journey.']],[130,369]),
heading('Commercial hypothesis'),p('Offer a guided pilot, then consider an organization subscription with an onboarding/content-review service and usage limits. Pricing and willingness to pay remain unvalidated. Expansion to other procedures should follow measured benefit, not feature count.'),
heading('Economic model'),p('Estimate monthly capacity released from observed learner minutes saved and trainer hours saved, valued using the customer\'s own labor assumptions. Subtract model, hosting and continuing content-review costs. Three of four objectives carried in the demo does not mean 75% of time or cost was saved.'),
heading('Risks and next milestone'),p('The main risks are poor case design, unsupported explanations, weak transfer to real tasks and content-review overhead. Start with reviewed material and a narrow procedure. Managed identity, organization-specific access and public deployment are separate work. The next business milestone is a supervised real pilot.'),
p('Basis: supplied organizer submission screenshot; local README.md, PITCH.md, REHEARSAL.md and recorded test results. No market-size, customer-adoption or financial-return figures are asserted. Team code and repository URL are maintained in the email package pending confirmation.','SmallX')]
build('AgentX_Learn_Business_Proposal.pdf',b)

t=page('Technical document','As-built local prototype | Architecture, controls and verification')
t += [heading('System overview'),p('The web app is a local FastAPI service with a plain JavaScript interface and SQLite persistence. A server-side adapter calls the configured Ollama-compatible gateway at POST /api/chat. Live mode uses model-selected actions; offline mode uses labeled deterministic selections. No cloud hosting, managed knowledge base or HR integration is asserted.'),
table([['Component','Implemented responsibility'],['Browser interface','Learning path, source-grounded chat, trainer studio, evidence dashboard and rehearsal controls.'],['FastAPI routes','Authenticate requests, enforce roles and validate typed request bodies.'],['Agent layer','Bounded chat tool loop and eligible-activity selection; malformed JSON receives limited repair.'],['Workflow layer','Source approval, course publication, activity eligibility, scoring, revision activation and evidence carryover.'],['SQLite','Users, sessions, sources, courses, attempts, chats, learning evidence, reviews and revision lineage.'],['Model gateway','Remote inference using server-side configuration; credentials are not returned to the browser.']],[125,374]),
heading('Two execution paths'),p('Chat: authenticated question -> model chooses an allowed read tool -> tool result -> model answer -> citation/source checks -> saved response. Learning: saved session -> eligible choices -> model selection -> transactional revalidation -> issued activity -> learner submission -> backend outcome.'),
heading('Trust boundary'),p('The model does not grade answers, approve sources, publish courses or activate revisions. The trainer uses separate authenticated routes for those approvals. Source text is reference data, not executable instructions. The browser displays backend readiness rather than inferring it from a quiz percentage.')]
t += [PageBreak()] + page('Agent contract and learning','Constrained tools and server-authoritative evidence')
t += [table([['Allowed read tool','Purpose'],['get_learning_state','Read the signed-in learner\'s readiness sessions and eligible actions.'],['select_approved_activity','Recommend a currently eligible activity; chat does not issue or answer it.'],['get_my_progress','Read permitted course and attempt information.'],['retrieve_sources','Search approved passages using lexical overlap.'],['get_course_outline','Read an approved course outline without answer keys.'],['recommend_lesson','Read an approved lesson and its source reference.']],[165,334]),
heading('Bounded execution and failure behavior'),p('Pydantic schemas reject unknown tools, unexpected fields and invalid argument types. Chat permits at most five model turns, including final output and any format repair. Learning-path selection permits at most two model calls when JSON repair is needed. Responses use a 512-token output budget and a 60-second transport timeout. Invalid output is not executed; errors are explicit rather than silently switching to offline mode.'),
heading('Readiness rules'),p('Diagnostic answers identify gaps but do not demonstrate an objective. Reviewing a lesson also awards no readiness. Fresh reassessment evidence must demonstrate at least 80% of objectives and every critical objective. In the four-objective pilot this requires all four. Two available fresh cases per objective bound automatic practice; exhaustion creates a trainer-review item. Trainer guidance does not change scores.'),
heading('Persistence and revalidation'),p('Each user/course has one learning session and at most one pending activity. The backend checks approval and eligibility when issuing and checks the issued activity when scoring. An identical resubmission is idempotent; a changed answer to an already submitted activity is rejected. Answer keys and future case banks are excluded from learner state. Decision records preserve observable evidence at selection and join the later submitted outcome.')]
t += [PageBreak()] + page('Version changes and isolation','Human approval, preserved history and separate rehearsals')
t += [heading('Procedure revision workflow'),p('A trainer creates an unapproved source/course revision. Deterministic comparison inspects objective content, supporting source sections and completion rules. Changed or new objectives must be refreshed. The trainer reviews the source, lessons and cases and explicitly approves the mapping before activation.'),
p('Activation checks stored fingerprints and rejects stale or superseded bases. It publishes the new version, retires the prior source, creates successor sessions, links demonstrated unchanged objectives as carryover, and assigns changed objectives for refresh. Original attempts are not rewritten. Reused case prompts are excluded by exact normalized text matching; semantic paraphrase detection is not implemented.'),
table([['Record group','Purpose'],['learning_sessions / learning_activities','User/course state and issued/submitted evidence.'],['learning_decisions / learning_reviews','Selection evidence snapshots and saved trainer requests/resolutions.'],['procedure_revisions / procedure_successors','Draft/activation metadata, fingerprints and version lineage.'],['learning_carryovers / learning_refreshes','Accepted prior evidence and assigned procedure refresh requirements.']],[225,274]),
heading('Rehearsal isolation'),p('A trainer can create a new fictional rehearsal in live or offline mode. Each rehearsal receives a separate SQLite file and original seed policy. Request-local ContextVars select the database and model mode; they do not change the process-wide database for other requests. Cookies select the rehearsal and preserve the main login for return. Browser tabs share that selection. Exiting retains the rehearsal file and restores the main workspace session.'),
heading('Access and operational limits'),p('Learners see their own progress; trainers can inspect team evidence and approve content. Sessions use HttpOnly, SameSite cookies, with Secure enabled for HTTPS. POST origin checks and request-size bounds are implemented. Shared demonstration credentials and local SQLite are suitable for the prototype only. Managed identity, tenant authorization, rate limits, backups and deployment hardening remain required before public use.')]
t += [PageBreak()] + page('Reproduction and verification','Evidence recorded through 27 September 2026')
t += [heading('Local setup'),p('Use Python 3.12 or newer. In employee-training-assistant, create .venv with python -m venv .venv, install requirements.txt, then run ./start.ps1 -Port 8013. Open http://127.0.0.1:8013. The shared fictional accounts are learner, alex and trainer; local demo password: LearnDemo2026!.'),
p('Configure AGENT_MODE as demo or gateway. Live mode requires LLM_GATEWAY_URL, LLM_GATEWAY_API_KEY and LLM_MODEL in the ignored local .env. TRAINING_DB optionally sets the database path. Never include .env, session cookies, learner databases or gateway logs in a shared submission.'),
heading('Verification commands'),p('Python suite: .venv/Scripts/python.exe -m pytest -q\nDashboard checks: node --test tests/dashboard.test.cjs\nOpt-in live check: .venv/Scripts/python.exe -m src.validate_live\nHealth endpoint: GET /health'),
table([['Evidence','Observed result / limit'],['Automated tests','71 Python tests and 2 dashboard aggregation tests passed in the latest recorded run. Python run reported two dependency deprecation warnings.'],['Gateway smoke checks','Three consecutive runs passed activity selection, cited policy response and unsupported-question referral after bounded format recovery. Earlier output/timeout failures occurred.'],['Browser rehearsal','Original policy reached ready; revision carried three objectives, refreshed one, then reached ready on version two.'],['Timing','Resumed segment approximately 2m 47s; excludes prior diagnostic work and interruption. Not a continuous full-demo benchmark.']],[130,369]),
heading('Known limitations and deployment evidence'),p('Lexical retrieval can miss paraphrases. Citation identifiers prove neither semantic support nor learning effectiveness. No short-answer grading, semantic change analysis or retention study is implemented. The demonstrated deployment is localhost, not a judge-accessible public URL. A repository URL, actual demo video and deployment evidence package still need submission-specific completion.'),
p('Implementation references: src/main.py; src/agents/{protocol,orchestrator,learning_coach,worker}.py; src/workflows/{readiness,change_impact,rehearsal}.py; src/core/{state,config}.py; tests/. Reproduction narrative: README.md, DEMO.md, REHEARSAL.md. Requirements source: organizer screenshot supplied by the user.','SmallX')]
build('AgentX_Learn_Technical_Document.pdf',t)
