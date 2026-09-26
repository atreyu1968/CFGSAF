(function(){
const API=(new URLSearchParams(location.search).get('api')||localStorage.getItem('grh0652.api')||'').replace(/\/$/,'');
const student=()=>window.SCORM_STUDENT_ID||localStorage.getItem('grh0652.student')||'';
const studentKey=()=>window.SCORM_STUDENT_KEY||localStorage.getItem('grh0652.studentKey')||'';
const course=()=>window.SCORM_COURSE_ID||'GRH0652_UT1';
async function call(path,opt={}){if(!API)return null;try{const r=await fetch(API+path,{headers:{'Content-Type':'application/json',...(studentKey()?{'X-Student-Token':studentKey()}:{}),...(opt.headers||{})},...opt});const data=await r.json().catch(()=>({}));if(!r.ok){const e=new Error(data.detail||('HTTP '+r.status));e.status=r.status;throw e}return data}catch(e){console.warn('Evidence API:',e.message);return {error:e.message,status:e.status||0}}}
function localEvent(ev){const k='grh0652.evidence.'+course()+'.'+student();const a=JSON.parse(localStorage.getItem(k)||'[]');a.push({...ev,student_id:student(),course_id:course(),ts:new Date().toISOString()});localStorage.setItem(k,JSON.stringify(a.slice(-2000)))}
window.EVIDENCE={api:API,
 async event(ev){localEvent(ev);return call('/api/evidence',{method:'POST',body:JSON.stringify({...ev,student_id:student(),course_id:course()})})},
 async state(state,courseId){courseId=courseId||course();localStorage.setItem('grh0652.remoteState.'+courseId+'.'+student(),JSON.stringify(state));return call('/api/state/'+encodeURIComponent(student()),{method:'PUT',body:JSON.stringify({course_id:courseId,state})})},
 async load(courseId){courseId=courseId||course();return call('/api/state/'+encodeURIComponent(student())+'?course_id='+encodeURIComponent(courseId))},
 async config(courseId){return call('/api/config/'+encodeURIComponent(courseId||course()))},
 async portfolio(courseId){return call('/api/portfolio/'+encodeURIComponent(courseId||course()))},
 async result(payload){return call('/api/result',{method:'POST',body:JSON.stringify({...payload,student_id:student(),course_id:course()})})},
 async startAttempt(kind,itemId,payload){return call('/api/attempts/start',{method:'POST',body:JSON.stringify({student_id:student(),course_id:course(),kind,item_id:itemId,payload:payload||{}})})},
 async answerAttempt(id,response,ce){return call('/api/attempts/'+encodeURIComponent(id)+'/answer',{method:'POST',body:JSON.stringify({response,ce:ce||null})})},
 async submitAttempt(id,payload){return call('/api/attempts/'+encodeURIComponent(id)+'/submit',{method:'POST',body:JSON.stringify({payload:payload||{}})})},
 async startExam(payload){return call('/api/exam/start',{method:'POST',body:JSON.stringify({student_id:student(),course_id:course(),kind:'exam',item_id:'final',payload:payload||{}})})},
 async submitExam(id,answers){return call('/api/exam/'+encodeURIComponent(id)+'/submit',{method:'POST',body:JSON.stringify({payload:{answers}})})},
 async dashboard(courseId){return call('/api/student/dashboard/'+encodeURIComponent(courseId||course()))},
 async feedback(courseId){return call('/api/student/feedback/'+encodeURIComponent(courseId||course()))},
 async recovery(courseId){return call('/api/recovery/'+encodeURIComponent(student())+'/'+encodeURIComponent(courseId||course()))},
 async recoveryContent(courseId){return call('/api/recovery/'+encodeURIComponent(student())+'/'+encodeURIComponent(courseId||course())+'/content')},
 async startRecovery(courseId){return call('/api/recovery/start',{method:'POST',body:JSON.stringify({student_id:student(),course_id:courseId||course(),kind:'recovery',item_id:'recovery-final',payload:{}})})},
 async submitRecovery(id,answers){return call('/api/recovery/'+encodeURIComponent(id)+'/submit',{method:'POST',body:JSON.stringify({payload:{answers}})})}
};})();