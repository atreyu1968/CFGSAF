(function(){
'use strict';
const $=s=>document.querySelector(s), $$=s=>Array.from(document.querySelectorAll(s));
const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const shuffle=a=>{const x=[...a];for(let i=x.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[x[i],x[j]]=[x[j],x[i]]}return x};
let api=null,connected=false,examActive=false,lastIncident=0,autoSubmitPending=false,interactionIndex=0,portfolioBank={};
let state={visited:[],mastered:[],best:0,attempts:0,examTaken:false,incidents:0,last:'inicio',practiceAttempts:{},portfolioAttempts:{},portfolioScores:{},examScore:null,ceExam:{},evaluationConfig:null};

function findAPI(){
 let w=window,tries=0;
 while(w&&tries<10){try{if(w.API)return w.API;if(w.parent&&w.parent!==w)w=w.parent;else break}catch(e){break}tries++}
 try{if(window.opener&&window.opener.API)return window.opener.API}catch(e){}
 return null;
}
function evidence(){try{return window.EVIDENCE||(parent&&parent.EVIDENCE)||null}catch(e){return null}}
function studentId(){try{return api&&api.LMSGetValue('cmi.core.student_id')||'alumno'}catch(e){return'alumno'}}
function localKey(){return 'grh0652.sco.'+UNIT_ID+'_'+studentId()}
function loadLocal(){try{const x=JSON.parse(localStorage.getItem(localKey())||'{}');state=Object.assign(state,x)}catch(e){}}
function saveLocal(){try{localStorage.setItem(localKey(),JSON.stringify(state))}catch(e){}}
function initSCORM(){
 api=findAPI();
 if(api){try{connected=api.LMSInitialize('')==='true';const raw=api.LMSGetValue('cmi.suspend_data');if(raw){const x=JSON.parse(raw);state=Object.assign(state,x)}const loc=api.LMSGetValue('cmi.core.lesson_location');if(loc)state.last=loc;const score=Number(api.LMSGetValue('cmi.core.score.raw')||0);if(score>state.best)state.best=score;if(api.LMSGetValue('cmi.core.lesson_status')==='not attempted')api.LMSSetValue('cmi.core.lesson_status','incomplete')}catch(e){connected=false;loadLocal()}}
 else loadLocal();
 const mode=$('#mode');if(mode)mode.textContent=connected?'Seguimiento SCORM 1.2':'Modo local';
}
function sync(){
 state.visited=[...new Set(state.visited)];state.mastered=[...new Set(state.mastered)];
 const raw=JSON.stringify(state);
 if(connected&&api){try{
   api.LMSSetValue('cmi.suspend_data',raw);
   api.LMSSetValue('cmi.core.lesson_location',state.last||'inicio');
   api.LMSSetValue('cmi.core.score.raw',String(Math.round(state.examTaken&&state.evaluation?state.evaluation.final:(state.best||0))));
   api.LMSSetValue('cmi.core.score.min','0');api.LMSSetValue('cmi.core.score.max','100');
   api.LMSSetValue('cmi.core.lesson_status',state.examTaken?(state.evaluation?.ra?'passed':'failed'):'incomplete');
   api.LMSSetValue('cmi.core.exit','suspend');
   api.LMSCommit('');
 }catch(e){saveLocal()}} else saveLocal();
 updateProgress();
 try{if(evidence())evidence().state(state)}catch(e){}
}
function finish(){
 sync();if(connected&&api){try{api.LMSSetValue('cmi.core.exit','suspend');api.LMSCommit('');api.LMSFinish('')}catch(e){}}
}
function showScreen(id,mark=true){
 if(examActive&&id!=='examen-evaluable')return;
 const el=document.getElementById(id)||document.getElementById('inicio');
 $$('.screen').forEach(x=>x.classList.remove('active'));el.classList.add('active');
 $$('.nav-btn').forEach(x=>x.classList.toggle('active',x.dataset.target===el.id));
 if(mark&&TRACKED_SCREENS.includes(el.id)&&!state.visited.includes(el.id))state.visited.push(el.id);
 state.last=el.id;
 const side=$('.sidebar');if(side)side.classList.remove('open');
 window.scrollTo(0,0);sync();
}

async function loadStudentFeedback(){
 const box=document.getElementById('studentFeedback');if(!box)return;const ev=evidence();if(!ev||!ev.api||!ev.feedback){box.innerHTML='<p>El seguimiento requiere conexión con el servidor de evaluación.</p>';return}
 box.innerHTML='<p>Cargando resultados…</p>';const [dash,rows]=await Promise.all([ev.dashboard?ev.dashboard():null,ev.feedback()]);
 if((dash&&dash.error)||(rows&&rows.error)){box.innerHTML='<p>No se pudieron cargar los resultados.</p>';return}
 let html='';if(dash&&dash.result){const r=dash.result;html+='<div class="mini-stat"><div><strong>'+Math.round(r.final)+'</strong>Nota RA</div><div><strong>'+Math.round(r.portfolio)+'</strong>Portafolio</div><div><strong>'+Math.round(r.exam)+'</strong>Examen</div><div><strong>'+r.ce_passed+'/'+r.ce_total+'</strong>CE superados</div></div><div class="notice"><strong>'+(r.ra_passed?'RA superado':'RA pendiente')+'</strong>'+(r.recovery&&r.recovery.length?' · Recuperación: '+r.recovery.map(safe).join(', '):'')+'</div>'}else html+='<div class="notice">La calificación global del RA todavía no está cerrada.</div>';
 if(dash&&dash.ce&&Object.keys(dash.ce).length)html+='<h2>Situación por criterio</h2><div class="ce-table">'+Object.entries(dash.ce).map(([ce,v])=>'<div><b>'+safe(ce)+' · '+(v.passed?'Superado':'Pendiente')+'</b><span>Portafolio '+Math.round(v.portfolio)+' · Examen '+Math.round(v.exam)+' · Resultado '+Math.round(v.final)+'</span></div>').join('')+'</div>';
 if(dash&&dash.recovery_plan)html+='<div class="notice"><strong>Plan de recuperación '+safe(dash.recovery_plan.status)+'</strong> · '+dash.recovery_plan.criteria.map(safe).join(', ')+'</div>';
 html+='<h2>Feedback de actividades abiertas</h2>';if(!rows||!rows.length)html+='<p>Todavía no tienes respuestas abiertas corregidas y validadas.</p>';else html+=rows.map(r=>'<article class="exercise done"><div class="type">CE '+safe(r.ce||'')+' · '+safe(r.item_id||'')+'</div><h3>'+Math.round(Number(r.score||0))+' / 100</h3><p>'+safe(r.feedback||'Sin comentario')+'</p>'+(r.breakdown&&r.breakdown.length?'<div class="ce-table">'+r.breakdown.map(x=>'<div><b>'+safe(x.name)+' · '+Number(x.weight||0)+'%</b><span>'+Math.round(Number(x.score||0))+'/100 · '+safe(x.feedback||'')+'</span></div>').join('')+'</div>':'')+'</article>').join('');
 box.innerHTML=html;
}
function bindNav(){
 $$('[data-target]').forEach(b=>b.addEventListener('click',()=>showScreen(b.dataset.target)));
 $$('[data-goto]').forEach(b=>b.addEventListener('click',()=>showScreen(b.dataset.goto)));
 const m=$('#menuBtn');if(m)m.onclick=()=>$('.sidebar')?.classList.toggle('open');
 const f=$('#fullscreenBtn');if(f)f.onclick=toggleFull;
 const e=$('#exitBtn');if(e)e.onclick=()=>{if(examActive){alert('Entrega primero la autoevaluación.');return}finish();try{if(parent&&parent!==window&&typeof parent.exitCourse==='function')parent.exitCourse();else history.back()}catch(x){history.back()}};
 const lf=document.getElementById('loadFeedback');if(lf)lf.onclick=loadStudentFeedback;
 const enter=$('#enterBtn');if(enter)enter.onclick=async()=>{$('#launchOverlay')?.classList.add('hidden');await requestFull();showScreen(state.last||'inicio')};
}
async function requestFull(){try{if(!document.fullscreenElement)await document.documentElement.requestFullscreen()}catch(e){}}
async function toggleFull(){try{if(!document.fullscreenElement)await document.documentElement.requestFullscreen();else await document.exitFullscreen()}catch(e){}}

function renderPractice(){
 CRITERIA.forEach(c=>{const box=document.getElementById('ex-'+c.id.replace('.',''));if(!box)return;box.innerHTML=(PRACTICE[c.id]||[]).map((e,i)=>exerciseHTML(c.id,e,i)).join('')});
 $$('.check-ex').forEach(b=>b.onclick=()=>checkExercise(b.dataset.ce,b.dataset.id));
 $$('.move-up').forEach(b=>b.onclick=()=>moveOrder(b,-1));
 $$('.move-down').forEach(b=>b.onclick=()=>moveOrder(b,1));
}
function exerciseHTML(ce,e,i){
 let body='';
 if(e.type==='choice'){
   body=e.options.map((o,j)=>`<label class="option"><input type="radio" name="ex-${e.id}" value="${j}"> ${safe(o)}</label>`).join('');
 }else if(e.type==='tf'){
   body=`<label class="option"><input type="radio" name="ex-${e.id}" value="true"> Verdadero</label><label class="option"><input type="radio" name="ex-${e.id}" value="false"> Falso</label>`;
 }else if(e.type==='multi'){
   body=e.options.map((o,j)=>`<label class="option"><input type="checkbox" name="ex-${e.id}" value="${j}"> ${safe(o)}</label>`).join('');
 }else if(e.type==='order'){
   body=`<ul class="order-list" id="order-${e.id}">${shuffle(e.items).map(it=>`<li class="order-item" data-key="${safe(it[0])}"><span>${safe(it[1])}</span><button class="move move-up" type="button">↑</button><button class="move move-down" type="button">↓</button></li>`).join('')}</ul>`;
 }else if(e.type==='match'){
   const rights=e.pairs.map((p,j)=>[j,p[1]]);
   body=e.pairs.map((p,j)=>`<div class="match-row"><b>${safe(p[0])}</b><select id="match-${e.id}-${j}"><option value="">Selecciona…</option>${shuffle(rights).map(r=>`<option value="${r[0]}">${safe(r[1])}</option>`).join('')}</select></div>`).join('');
 }
 const done=state.mastered.includes(e.id);
 return `<article class="exercise ${done?'done':''}" id="card-${e.id}"><div class="type">Actividad ${i+1} · ${safe(e.type)}</div><h3>${safe(e.q)}</h3>${body}<button class="btn primary check-ex" data-ce="${ce}" data-id="${e.id}" type="button">Comprobar</button><div class="feedback hidden" id="fb-${e.id}"></div></article>`;
}
function moveOrder(btn,d){const li=btn.closest('li'),ul=li.parentNode;if(d<0&&li.previousElementSibling)ul.insertBefore(li,li.previousElementSibling);if(d>0&&li.nextElementSibling)ul.insertBefore(li.nextElementSibling,li)}
function getEx(ce,id){return (PRACTICE[ce]||[]).find(x=>x.id===id)}
async function checkExercise(ce,id){
 const e=getEx(ce,id);if(!e)return;let ok=false,answered=true;
 if(e.type==='choice'){const x=$(`input[name="ex-${e.id}"]:checked`);if(!x)answered=false;else ok=Number(x.value)===e.answer}
 else if(e.type==='tf'){const x=$(`input[name="ex-${e.id}"]:checked`);if(!x)answered=false;else ok=(x.value==='true')===e.answer}
 else if(e.type==='multi'){const got=$$(`input[name="ex-${e.id}"]:checked`).map(x=>Number(x.value)).sort((a,b)=>a-b);if(!got.length)answered=false;else ok=JSON.stringify(got)===JSON.stringify([...e.answer].sort((a,b)=>a-b))}
 else if(e.type==='order'){const got=$$(`#order-${e.id} .order-item`).map(x=>x.dataset.key);ok=JSON.stringify(got)===JSON.stringify(e.answer)}
 else if(e.type==='match'){const got=e.pairs.map((p,j)=>document.getElementById(`match-${e.id}-${j}`)?.value);if(got.some(v=>v===''))answered=false;else ok=got.every((v,j)=>Number(v)===j)}
 if(!answered){alert('Completa la actividad antes de comprobar.');return}
 const ev=evidence();if(ev&&ev.api){const gate=await ev.startAttempt('portfolio',id,{ce});if(!gate||gate.error){alert('No se puede registrar este intento: '+(gate?.error||'servidor no disponible'));return}await ev.answerAttempt(gate.id,answerForExercise(e),ce);await ev.submitAttempt(gate.id,{correct:ok,score:ok?100:0});}
 const fb=document.getElementById('fb-'+e.id);fb.classList.remove('hidden','ok','bad');fb.classList.add(ok?'ok':'bad');fb.innerHTML=`<b>${ok?'Correcto.':'Revisa la respuesta.'}</b> ${safe(e.feedback||'')}`;
 if(ok&&!state.mastered.includes(e.id)){state.mastered.push(e.id);document.getElementById('card-'+e.id)?.classList.add('done');sync()}else updateProgress();
}
function updateProgress(){
 const mastered=state.mastered.length,visited=state.visited.filter(x=>TRACKED_SCREENS.includes(x)).length,best=Number(state.best||0);
 const pct=Math.min(100,Math.round((visited/TRACKED_SCREENS.length)*30+(mastered/PRACTICE_TOTAL)*50+(best/100)*20));
 const pb=$('#progressBar'),pt=$('#progressText'),pc=$('#practiceCount'),bs=$('#bestScore');if(pb)pb.style.width=pct+'%';if(pt)pt.textContent=pct+'% recorrido';if(pc)pc.textContent=mastered+'/'+PRACTICE_TOTAL;if(bs)bs.textContent=Math.round(best)+'%';
 const ps=$('#practiceSummary');if(ps)ps.textContent=mastered+' de '+PRACTICE_TOTAL+' actividades dominadas.';
 CRITERIA.forEach(c=>{const ex=PRACTICE[c.id]||[],n=ex.filter(e=>state.mastered.includes(e.id)).length,k=c.id.replace('.','');const tx=document.getElementById('prog-'+k),hb=document.getElementById('homeprog-'+k),bar=document.getElementById('bar-'+k),hbar=document.getElementById('homebar-'+k);if(tx)tx.textContent=n+'/6 dominadas';if(hb)hb.textContent=n+'/6';if(bar)bar.style.width=(n/6*100)+'%';if(hbar)hbar.style.width=(n/6*100)+'%'});
}

let examQuestions=[];\nlet examDeadline=null,examTimer=null;\nfunction renderExam(){
 const box=$('#examBox');if(!box)return;
 box.innerHTML=`<div class="notice" id="incidentNotice"><strong>Modo evaluación.</strong> Tiempo restante: <strong id="examCountdown">--:--</strong> · Incidencias de foco: <span id="incidentCount">0</span>/3.</div>`+examQuestions.map((q,i)=>{
 let opts='';
 if(q.type==='choice')opts=q.options.map((o,j)=>`<label class="option"><input type="radio" name="q-${q.id}" value="${j}"> ${safe(o)}</label>`).join('');
 else if(q.type==='tf')opts=`<label class="option"><input type="radio" name="q-${q.id}" value="true"> Verdadero</label><label class="option"><input type="radio" name="q-${q.id}" value="false"> Falso</label>`;
 else if(q.type==='multi')opts=q.options.map((o,j)=>`<label class="option"><input type="checkbox" name="q-${q.id}" value="${j}"> ${safe(o)}</label>`).join('');
 return `<article class="question" id="qcard-${q.id}"><div class="qnum">Pregunta ${i+1} de ${examQuestions.length} · CE ${safe(q.ce)}</div><h3>${safe(q.q)}</h3>${opts}<div class="feedback hidden" id="qfb-${q.id}"></div></article>`
 }).join('')+`<button class="btn primary big" id="submitExam" type="button">Entregar examen</button>`;
 $('#submitExam').onclick=()=>submitExam(false);
}
function updateExamCountdown(){
 const el=$('#examCountdown');if(!el||!examDeadline)return;
 const left=Math.max(0,new Date(examDeadline).getTime()-Date.now()),sec=Math.ceil(left/1000),m=Math.floor(sec/60),s=sec%60;el.textContent=String(m).padStart(2,'0')+':'+String(s).padStart(2,'0');
 if(left<=0&&examActive&&!autoSubmitPending){autoSubmitPending=true;clearInterval(examTimer);examTimer=null;submitExam(true)}
}
function startExamTimer(){clearInterval(examTimer);examTimer=null;updateExamCountdown();if(examDeadline)examTimer=setInterval(updateExamCountdown,1000);}
async function startExam(){
 if(state.examTaken){alert('El examen solo permite un intento.');return}if(!state.evaluationConfig||!state.evaluationConfig.exam_enabled){alert('El profesor todavía no ha activado el examen.');return}
 const ev=evidence();if(ev&&ev.api){const gate=await ev.startExam({unit:UNIT_ID});if(!gate||gate.error){alert('No se puede iniciar el examen: '+(gate?.error||'servidor no disponible'));return}state.serverExamAttempt=gate.attempt;state.serverExamAttemptId=gate.attempt_id;state.examVersion=gate.version||state.examVersion;examDeadline=gate.deadline_at||null;examQuestions=(gate.questions||[]).map(q=>({...q,type:q.type||'choice'}));}
 if(!examQuestions.length){alert('El servidor no ha proporcionado preguntas para el examen.');return}\n examActive=true;autoSubmitPending=false;state.incidents=0;state.examIncidentLog=[];state.attempts=(state.attempts||0)+1;document.body.classList.add('exam-mode');$('#examIntro')?.classList.add('hidden');$('#examResult').innerHTML='';$('#examBox')?.classList.remove('hidden');renderExam();startExamTimer();requestFull();sync();
}

function examGuard(e){if(!examActive)return;if(e.type==='beforeunload'){e.preventDefault();e.returnValue='';return ''}if(e.type==='popstate'){history.pushState(null,'',location.href);registerIncident('navigation')}if(e.type==='contextmenu'||(e.type==='keydown'&&(e.key==='F5'||(e.ctrlKey||e.metaKey)&&['r','l','t','n','w'].includes(e.key.toLowerCase())))){e.preventDefault();registerIncident('blocked_command')}}
document.addEventListener('fullscreenchange',()=>{if(examActive&&!document.fullscreenElement){registerIncident('fullscreen_exit');setTimeout(()=>{if(examActive)requestFull()},150)}});
document.addEventListener('visibilitychange',()=>{if(examActive&&document.hidden)registerIncident('tab_hidden')});
window.addEventListener('blur',()=>{if(examActive)registerIncident('window_blur')});
window.addEventListener('beforeunload',examGuard);window.addEventListener('popstate',examGuard);document.addEventListener('contextmenu',examGuard);document.addEventListener('keydown',examGuard,true);

function registerIncident(reason){
 if(!examActive)return;const now=Date.now();if(now-lastIncident<1400)return;lastIncident=now;state.incidents=(state.incidents||0)+1;state.examIncidentLog=(state.examIncidentLog||[]);state.examIncidentLog.push({reason:reason||'focus',at:new Date().toISOString()});const c=$('#incidentCount');if(c)c.textContent=state.incidents;sync();
 if(state.incidents>=3){autoSubmitPending=true;if(!document.hidden)setTimeout(()=>submitExam(true),200)}
}
function examAnswer(q){
 if(q.type==='choice'){const x=$(`input[name="q-${q.id}"]:checked`);return x?Number(x.value):null}
 if(q.type==='tf'){const x=$(`input[name="q-${q.id}"]:checked`);return x?(x.value==='true'):null}
 if(q.type==='multi'){const x=$$(`input[name="q-${q.id}"]:checked`).map(v=>Number(v.value)).sort((a,b)=>a-b);return x.length?x:null}
 return null;
}
function isCorrect(q,a){if(a===null)return false;if(q.type==='multi')return JSON.stringify(a)===JSON.stringify([...q.answer].sort((x,y)=>x-y));return a===q.answer}
function answerText(q,a){if(a===null)return'(sin respuesta)';if(q.type==='choice')return q.options[a]||'';if(q.type==='tf')return a?'Verdadero':'Falso';if(q.type==='multi')return a.map(i=>q.options[i]).join(' | ');return String(a)}
function correctText(q){if(q.type==='choice')return q.options[q.answer];if(q.type==='tf')return q.answer?'Verdadero':'Falso';if(q.type==='multi')return q.answer.map(i=>q.options[i]).join(' | ');return''}
function recordInteraction(q,a,ok,i){
 if(!connected||!api)return;try{const n=(state.attempts-1)*EXAM.length+i;api.LMSSetValue(`cmi.interactions.${n}.id`,q.id+'-a'+state.attempts);api.LMSSetValue(`cmi.interactions.${n}.type`,q.type==='tf'?'true-false':'choice');api.LMSSetValue(`cmi.interactions.${n}.student_response`,answerText(q,a).slice(0,240));api.LMSSetValue(`cmi.interactions.${n}.result`,ok?'correct':'wrong')}catch(e){}
}
async function submitExam(auto){
 if(!examActive)return;
 const answers=examQuestions.map(examAnswer),answered=answers.filter(x=>x!==null).length;
 if(!auto&&answered<examQuestions.length&&!confirm('Has respondido '+answered+' de '+examQuestions.length+'. ¿Quieres entregar igualmente?'))return;
 let good=0,by={},score=0;const ev=evidence();if(!(ev&&ev.api&&state.serverExamAttemptId)){alert('El examen evaluable requiere conexión con el servidor. Tus respuestas no se han entregado.');return}if(ev&&ev.api&&state.serverExamAttemptId){const amap={};examQuestions.forEach((q,i)=>amap[q.id]=answers[i]);const graded=await ev.submitExam(state.serverExamAttemptId,amap);if(!graded||graded.error){alert('No se pudo entregar el examen: '+(graded?.error||'error de servidor'));return}score=graded.score;by=graded.by_ce||{};good=Object.values(by).reduce((a,v)=>a+(v.ok||0),0);examQuestions.forEach((q,i)=>recordInteraction(q,answers[i],false,i));}state.examTaken=true;state.examScore=score;state.best=score;state.last='examen-evaluable';examActive=false;autoSubmitPending=false;clearInterval(examTimer);examTimer=null;document.body.classList.remove('exam-mode');$('#examBox')?.classList.add('hidden');
 const evaluation=calculateEvaluation(by);
 if(connected&&api){try{api.LMSSetValue('cmi.core.score.raw',String(Math.round(evaluation.final)));api.LMSSetValue('cmi.core.lesson_status',evaluation.ra?'passed':'failed')}catch(e){}}
 try{if(evidence())evidence().event({kind:'exam',attempt:1,score:score,payload:{by_ce:by,incidents:state.incidents,incident_log:state.examIncidentLog||[],variant:examQuestions.map(q=>q.id)}})}catch(e){}
 const breakdown=CRITERIA.map(c=>{const v=by[c.id]||{ok:0,n:0};return `<div><b>CE ${safe(c.id)}</b><br>${Math.round((v.ok/(v.n||1))*100)}%</div>`}).join('');
 $('#examResult').innerHTML=`<div class="exam-result"><div class="score-big">${score}%</div><h2>${evaluation.ra?'RA superado':'RA no superado'}</h2><p>${good} respuestas correctas de ${EXAM.length}. Mejor nota registrada: <b>${state.best}%</b>.${auto?' El intento se entregó automáticamente al alcanzar tres incidencias de foco.':''}</p><div class="result-grid">${breakdown}</div><p><b>Estado RA:</b> ${evaluation.ra?'SUPERADO':'NO SUPERADO'} · CE superados: ${evaluation.passed}/${evaluation.total}. ${evaluation.recovery.length?'Programa de recuperación: '+evaluation.recovery.join(', '):'Sin recuperación pendiente.'}</p></div>`;
 sync();try{if(document.fullscreenElement)document.exitFullscreen()}catch(e){}
}
function renderSelfAssessment(){
 const box=$('#selfBox');if(!box)return;const pool=shuffle([...EXAM]).slice(0,Math.min(30,EXAM.length));box.innerHTML=pool.map((q,i)=>{let opts='';if(q.type==='choice')opts=q.options.map((o,j)=>`<label class="option"><input type="radio" name="self-${q.id}" value="${j}"> ${safe(o)}</label>`).join('');else if(q.type==='tf')opts=`<label class="option"><input type="radio" name="self-${q.id}" value="true"> Verdadero</label><label class="option"><input type="radio" name="self-${q.id}" value="false"> Falso</label>`;else if(q.type==='multi')opts=q.options.map((o,j)=>`<label class="option"><input type="checkbox" name="self-${q.id}" value="${j}"> ${safe(o)}</label>`).join('');return `<article class="question"><div class="qnum">Pregunta ${i+1} · CE ${safe(q.ce)}</div><h3>${safe(q.q)}</h3>${opts}</article>`}).join('')+'<button class="btn primary big" id="submitSelf" type="button">Corregir autoevaluación</button>';
 $('#submitSelf').onclick=()=>{let good=0;pool.forEach(q=>{let a=null;if(q.type==='choice'){const x=$(`input[name="self-${q.id}"]:checked`);a=x?Number(x.value):null}else if(q.type==='tf'){const x=$(`input[name="self-${q.id}"]:checked`);a=x?(x.value==='true'):null}else if(q.type==='multi'){const x=$(`input[name="self-${q.id}"]:checked`).map(v=>Number(v.value)).sort((a,b)=>a-b);a=x.length?x:null}if(isCorrect(q,a))good++});const pct=Math.round(good/pool.length*100);$('#selfResult').innerHTML=`<div class="exam-result"><div class="score-big">${pct}%</div><h2>Autoevaluación de preparación</h2><p>${good} respuestas correctas de ${pool.length}. Esta puntuación no forma parte de la nota.</p></div>`;try{if(evidence())evidence().event({kind:'self_assessment',score:pct,payload:{questions:pool.map(q=>q.id)}})}catch(e){}};
}
function bindSelfAssessment(){const b=$('#startSelf');if(b)b.onclick=renderSelfAssessment;renderSelfAssessment()}

async function loadRecovery(){
 const box=$('#recoveryBox'),ev=evidence();if(!box||!ev||!ev.api){if(box)box.innerHTML='<p>La recuperación requiere conexión con el servidor.</p>';return}
 const r=await ev.recoveryContent();if(!r||r.error||!r.plan){box.innerHTML='<p>No tienes un programa de recuperación activo.</p>';return}
 const p=r.plan;if(p.status==='passed'){box.innerHTML='<h2>Recuperación superada</h2><p>Has completado los criterios pendientes.</p>';return}
 const field=i=>{const n='rec-'+safe(i.item_id);if(i.kind==='multi')return i.options.map((o,j)=>'<label class="option"><input type="checkbox" name="'+n+'" value="'+j+'"> '+safe(o)+'</label>').join('');if(i.kind==='tf')return '<label class="option"><input type="radio" name="'+n+'" value="true"> Verdadero</label><label class="option"><input type="radio" name="'+n+'" value="false"> Falso</label>';if(i.kind==='free')return '<textarea name="'+n+'" rows="4" placeholder="Escribe tu respuesta"></textarea>';return i.options.map((o,j)=>'<label class="option"><input type="radio" name="'+n+'" value="'+j+'"> '+safe(o)+'</label>').join('')};
 const by={};(p.items||[]).forEach(i=>(by[i.ce]=by[i.ce]||[]).push(i));let html='<h2>Criterios pendientes: '+p.criteria.map(safe).join(', ')+'</h2><p>Repasa la teoría del criterio, realiza las nuevas actividades y entrega la prueba de recuperación.</p>';
 Object.entries(by).forEach(([ce,items])=>{html+='<div class="card"><h3>CE '+safe(ce)+'</h3><p><b>Refuerzo:</b> revisa el apartado teórico y los errores detectados en tu evaluación ordinaria.</p>';items.forEach(i=>{html+='<article class="question"><p>'+safe(i.prompt)+'</p>'+field(i)+'</article>'});html+='</div>'});html+='<button id="submitRecovery" class="btn primary big">Entregar recuperación</button>';box.innerHTML=html;
 $('#submitRecovery').onclick=async()=>{const gate=await ev.startRecovery();if(!gate||gate.error){alert(gate?.error||'No se puede iniciar la recuperación');return}const answers={};(p.items||[]).forEach(i=>{const n='rec-'+i.item_id;if(i.kind==='multi')answers[i.item_id]=Array.from(document.querySelectorAll('input[name="'+n+'"]:checked')).map(x=>Number(x.value));else if(i.kind==='tf'){const x=$('input[name="'+n+'"]:checked');answers[i.item_id]=x?x.value==='true':null}else if(i.kind==='free'){const x=document.querySelector('[name="'+n+'"]');answers[i.item_id]=x?x.value:null}else{const x=$('input[name="'+n+'"]:checked');answers[i.item_id]=x?Number(x.value):null}});const out=await ev.submitRecovery(gate.id,answers);if(!out||out.error){alert(out?.error||'No se pudo entregar');return}$('#recoveryResult').innerHTML='<div class="exam-result"><div class="score-big">'+Math.round(out.score)+'%</div><h2>'+(out.status==='passed'?'Recuperación superada':'Aún quedan criterios pendientes')+'</h2><p>CE superados en recuperación: '+out.criteria_passed.map(safe).join(', ')+'</p></div>';loadRecovery()}
}

function bindExam(){
 const b=$('#startExam');if(b)b.onclick=startExam;
 document.addEventListener('visibilitychange',()=>{if(examActive){if(document.hidden)registerIncident('visibility');else if(autoSubmitPending&&state.incidents>=3)submitExam(true)}});
 window.addEventListener('blur',()=>registerIncident('blur'));
 document.addEventListener('fullscreenchange',()=>{if(examActive&&!document.fullscreenElement&&!document.hidden)registerIncident('fullscreen')});
}

function answerForExercise(e){
 if(e.type==='choice'){const x=$(`input[name="ex-${e.id}"]:checked`);return x?Number(x.value):null}
 if(e.type==='tf'){const x=$(`input[name="ex-${e.id}"]:checked`);return x?(x.value==='true'):null}
 if(e.type==='multi'){const x=Array.from(document.querySelectorAll(`input[name="ex-${e.id}"]:checked`)).map(x=>Number(x.value)).sort((a,b)=>a-b);return x.length?x:null}
 if(e.type==='order')return Array.from(document.querySelectorAll(`#order-${e.id} .order-item`)).map(x=>x.dataset.key);
 if(e.type==='match')return e.pairs.map((p,j)=>document.getElementById(`match-${e.id}-${j}`)?.value);
 return null
}
function correctExercise(e,a){
 if(a===null)return false;
 if(e.type==='choice'||e.type==='tf')return a===e.answer;
 if(e.type==='multi')return JSON.stringify(a)===JSON.stringify([...e.answer].sort((x,y)=>x-y));
 if(e.type==='order')return JSON.stringify(a)===JSON.stringify(e.answer);
 if(e.type==='match')return a.every((v,j)=>Number(v)===j);
 return false
}
function installFormativePractice(){
 const first=document.getElementById('pract-1a');if(!first)return;
 const sec=document.createElement('section');sec.className='screen';sec.id='practica-formativa';
 sec.innerHTML='<div class="hero compact"><span class="pill">No evaluable</span><h1>Práctica guiada por criterios</h1><p>Dispones de 3 oportunidades por ejercicio. Tras el tercer intento se muestra la solución orientativa. Estos ejercicios generan evidencia de trabajo, pero no nota.</p></div><div id="formativeBoxes"></div>';
 first.parentNode.insertBefore(sec,first);
 const nav=document.querySelector('[data-target="practica-home"]');if(nav){const b=document.createElement('button');b.className='nav-btn';b.dataset.target='practica-formativa';b.textContent='Práctica guiada · 3 intentos';nav.parentNode.insertBefore(b,nav.nextSibling);b.onclick=()=>showScreen('practica-formativa')}
 const host=sec.querySelector('#formativeBoxes');
 CRITERIA.forEach(c=>{const block=document.createElement('div');block.className='card';block.innerHTML='<h2>CE '+safe(c.id)+'</h2><div class="form-list"></div>';host.appendChild(block);const list=block.querySelector('.form-list');
  (PRACTICE[c.id]||[]).forEach((e,i)=>{const q=document.createElement('article');q.className='exercise';q.innerHTML='<div class="type">Práctica '+(i+1)+' · CE '+safe(c.id)+'</div><h3>'+safe(e.q)+'</h3><div class="fp-options"></div><button class="btn primary fp-check" type="button">Comprobar</button><div class="feedback hidden"></div>';list.appendChild(q);
   const opts=q.querySelector('.fp-options');let choices=[];
   if(e.type==='choice')choices=e.options.map((o,j)=>({label:o,value:j,ok:j===e.answer}));
   else if(e.type==='tf')choices=[{label:'Verdadero',value:true,ok:e.answer===true},{label:'Falso',value:false,ok:e.answer===false}];
   else {choices=[{label:'He completado el procedimiento propuesto',value:'done',ok:true}]}
   shuffle(choices).forEach((o,j)=>{const l=document.createElement('label');l.className='option';l.innerHTML='<input type="radio" name="fp-'+e.id+'" value="'+j+'"> '+safe(o.label);l.dataset.ok=o.ok?'1':'0';opts.appendChild(l)});
   q.querySelector('.fp-check').onclick=async()=>{const chosen=q.querySelector('input:checked');if(!chosen){alert('Selecciona una respuesta.');return}let n=(state.practiceAttempts[e.id]||0)+1;const ev=evidence();let serverId=null;if(ev&&ev.api){const gate=await ev.startAttempt('practice',e.id,{ce:c.id});if(!gate||gate.error){alert('No se puede registrar este intento: '+(gate?.error||'servidor no disponible'));return}n=gate.attempt;serverId=gate.id}state.practiceAttempts[e.id]=n;const lab=chosen.closest('label'),ok=lab.dataset.ok==='1',fb=q.querySelector('.feedback');fb.classList.remove('hidden','ok','bad');fb.classList.add(ok?'ok':'bad');
    if(ok)fb.innerHTML='<b>Correcto.</b> '+safe(e.feedback||'');else if(n>=3){const sol=Array.from(opts.querySelectorAll('label')).find(x=>x.dataset.ok==='1')?.textContent.trim()||'Consulta la explicación.';fb.innerHTML='<b>Has agotado los 3 intentos.</b> Solución orientativa: '+safe(sol)+'. '+safe(e.feedback||'');q.querySelector('.fp-check').disabled=true}else fb.innerHTML='<b>Respuesta incorrecta.</b> Revisa el contenido. Te quedan '+(3-n)+' intento(s).';
    try{if(ev&&serverId){await ev.answerAttempt(serverId,lab.textContent.trim(),c.id);await ev.submitAttempt(serverId,{correct:ok})}if(evidence())evidence().event({kind:'practice',ce:c.id,item_id:e.id,attempt:n,response:lab.textContent.trim(),correct:ok,payload:{max_attempts:3}})}catch(x){};sync()
   }
  })
 })
}
async function loadSecurePortfolio(){
 const ev=evidence();if(!ev||!ev.api||!ev.portfolio)return;
 const r=await ev.portfolio('GRH0652');if(!r||r.error||!Array.isArray(r.items))return;
 portfolioBank={};r.items.filter(q=>String(q.ce||'').startsWith('1.')).forEach(q=>{(portfolioBank[q.ce]||(portfolioBank[q.ce]=[])).push(q)});
 CRITERIA.forEach(cr=>{const box=document.getElementById('ex-'+cr.id.replace('.',''));if(!box)return;box.innerHTML=(portfolioBank[cr.id]||[]).map((q,i)=>portfolioHTML(cr.id,q,i)).join('')});
 installPortfolioRules();
}
function portfolioHTML(ce,q,i){
 const id=q.id,type=q.kind||q.type;let body='';
 if(type==='choice'||type==='multi')body=(q.options||[]).map((o,j)=>`<label class="option"><input type="${type==='multi'?'checkbox':'radio'}" name="ex-${id}" value="${j}"> ${safe(o)}</label>`).join('');
 else if(type==='tf')body=`<label class="option"><input type="radio" name="ex-${id}" value="true"> Verdadero</label><label class="option"><input type="radio" name="ex-${id}" value="false"> Falso</label>`;
 else body=`<textarea id="free-${id}" rows="4" placeholder="Escribe tu respuesta"></textarea>`;
 return `<article class="exercise" id="card-${id}"><div class="type">Portfolio ${i+1} · ${safe(type)}</div><h3>${safe(q.prompt||q.q)}</h3>${body}<button class="btn primary check-ex" data-ce="${ce}" data-id="${id}" type="button">Entregar</button><div class="feedback hidden" id="fb-${id}"></div></article>`;
}
function portfolioAnswer(q){const id=q.id,type=q.kind||q.type;if(type==='choice'){const x=$(`input[name="ex-${id}"]:checked`);return x?Number(x.value):null}if(type==='tf'){const x=$(`input[name="ex-${id}"]:checked`);return x?(x.value==='true'):null}if(type==='multi'){const a=$$(`input[name="ex-${id}"]:checked`).map(x=>Number(x.value));return a.length?a:null}const x=document.getElementById('free-'+id);return x&&x.value.trim()?x.value.trim():null}
function installPortfolioRules(){
 document.querySelectorAll('.nav-group').forEach(x=>{if(x.textContent.trim()==='Práctica por CE')x.textContent='Portafolio de Actividades'});
 const mh=document.querySelector('#practica-home h1');if(mh)mh.textContent='Portafolio de Actividades · evaluación por criterios';
 document.addEventListener('click',async ev=>{const b=ev.target.closest('.check-ex');if(!b)return;const q=(portfolioBank[b.dataset.ce]||[]).find(x=>x.id===b.dataset.id);if(!q)return;ev.preventDefault();ev.stopImmediatePropagation();const id=q.id,n=state.portfolioAttempts[id]||0;if(n>=2){alert('Esta actividad del portafolio ya ha consumido sus 2 intentos.');return}const a=portfolioAnswer(q);if(a===null){alert('Completa la actividad antes de entregar.');return}const api=evidence();if(!api||!api.api){alert('El portafolio evaluable requiere conexión con el servidor.');return}const gate=await api.startAttempt('portfolio',id,{ce:b.dataset.ce});if(!gate||gate.error){alert('No se puede registrar este intento: '+(gate?.error||'servidor no disponible'));return}await api.answerAttempt(gate.id,a,b.dataset.ce);const sent=await api.event({kind:'portfolio',ce:b.dataset.ce,item_id:id,attempt:n+1,response:a,payload:{max_attempts:2}});await api.submitAttempt(gate.id,{submitted:true});if(sent&&typeof sent.score==='number')state.portfolioScores[id]=sent.score;state.portfolioAttempts[id]=n+1;const fb=document.getElementById('fb-'+id);if(fb){fb.classList.remove('hidden','ok','bad');fb.textContent='Intento registrado. La corrección se ha realizado en el servidor.'}sync();
 },true)
}
function seededRandom(seed){let h=2166136261;for(let i=0;i<seed.length;i++){h^=seed.charCodeAt(i);h=Math.imul(h,16777619)}return()=>{h+=0x6D2B79F5;let t=h;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return((t^t>>>14)>>>0)/4294967296}}
function randomizeExam(){
 const rnd=seededRandom(studentId()+'|GRH0652|'+new Date().toISOString().slice(0,10));
 for(const q of EXAM){if(q.type==='choice'){const arr=q.options.map((o,i)=>({o,i}));for(let i=arr.length-1;i>0;i--){const j=Math.floor(rnd()*(i+1));[arr[i],arr[j]]=[arr[j],arr[i]]}const old=q.answer;q.options=arr.map(x=>x.o);q.answer=arr.findIndex(x=>x.i===old)}}
 for(let i=EXAM.length-1;i>0;i--){const j=Math.floor(rnd()*(i+1));[EXAM[i],EXAM[j]]=[EXAM[j],EXAM[i]]}
}
async function loadEvaluationConfig(){
 let c=null;try{if(evidence())c=await evidence().config()}catch(e){}
 state.evaluationConfig=c||state.evaluationConfig||{portfolio_weight:40,exam_weight:60,pass_score:50,ce_pass_percent:80,ce_pass_score:50,exam_enabled:false,exam_questions_per_ce:3,exam_minutes:45,require_both_instruments:false};
 const n=Math.max(1,Number(state.evaluationConfig.exam_questions_per_ce||3));const selected=[];CRITERIA.forEach(cr=>selected.push(...EXAM.filter(q=>q.ce===cr.id).slice(0,n)));EXAM.splice(0,EXAM.length,...selected);
 const intro=$('#examIntro');if(intro)intro.insertAdjacentHTML('afterbegin','<div class="notice"><strong>Examen evaluable:</strong> un único intento. El profesor debe activar la convocatoria.</div>');
 const b=$('#startExam');if(b){b.textContent=state.examTaken?'Examen ya realizado':(state.evaluationConfig.exam_enabled?'Comenzar examen · 1 intento':'Examen no activado');b.disabled=state.examTaken||!state.evaluationConfig.exam_enabled}
}
function calculateEvaluation(examBy){
 const cfg=state.evaluationConfig||{portfolio_weight:40,exam_weight:60,pass_score:50,ce_pass_percent:80,ce_pass_score:50,require_both_instruments:false};
 const ce={};CRITERIA.forEach(c=>{const items=PRACTICE[c.id]||[];const ps=items.map(e=>Number(state.portfolioScores[e.id]||0));const p=ps.length?ps.reduce((a,b)=>a+b,0)/ps.length:0;const ex=examBy[c.id]||{ok:0,n:0};const x=ex.n?ex.ok/ex.n*100:0;const final=p*cfg.portfolio_weight/100+x*cfg.exam_weight/100;ce[c.id]={portfolio:p,exam:x,final,passed:final>=cfg.ce_pass_score}});
 const vals=Object.values(ce),passed=vals.filter(x=>x.passed).length,portfolio=vals.reduce((a,x)=>a+x.portfolio,0)/vals.length,exam=vals.reduce((a,x)=>a+x.exam,0)/vals.length,final=portfolio*cfg.portfolio_weight/100+exam*cfg.exam_weight/100,needed=Math.ceil(vals.length*cfg.ce_pass_percent/100);
 const both=!cfg.require_both_instruments||(portfolio>=cfg.pass_score&&exam>=cfg.pass_score),ra=final>=cfg.pass_score&&passed>=needed&&both,recovery=Object.entries(ce).filter(([k,v])=>!v.passed).map(([k])=>k);
 state.evaluation={portfolio,exam,final,passed,total:vals.length,ra,recovery,ce};try{if(evidence()){const authoritative=evidence().result({portfolio,exam,final,ce_passed:passed,ce_total:vals.length,ra_passed:ra,recovery});if(authoritative&&typeof authoritative.then==='function')authoritative.then(r=>{if(r&&r.ok){state.evaluation={portfolio:r.portfolio,exam:r.exam,final:r.final,passed:r.ce_passed,total:r.ce_total,ra:r.ra_passed,recovery:r.recovery,ce:r.ce};sync()}}).catch(()=>{})}}catch(e){};return state.evaluation
}

window.addEventListener('message',e=>{if(e.origin===location.origin&&e.data&&e.data.type==='scorm-save-exit')sync()});
window.addEventListener('beforeunload',finish);
window.addEventListener('pagehide',sync);

initSCORM();bindNav();renderPractice();installFormativePractice();loadSecurePortfolio();randomizeExam();bindSelfAssessment();bindExam();loadEvaluationConfig();loadRecovery();updateProgress();
const start=state.last&&document.getElementById(state.last)?state.last:'inicio';$$('.screen').forEach(x=>x.classList.remove('active'));document.getElementById(start)?.classList.add('active');$$('.nav-btn').forEach(x=>x.classList.toggle('active',x.dataset.target===start));
setInterval(sync,15000);
})();