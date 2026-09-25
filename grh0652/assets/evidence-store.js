(function(){
const API=(new URLSearchParams(location.search).get('api')||localStorage.getItem('grh0652.api')||'').replace(/\/$/,'');
const student=()=>window.SCORM_STUDENT_ID||localStorage.getItem('grh0652.student')||'';
async function call(path,opt={}){if(!API)return null;try{const r=await fetch(API+path,{headers:{'Content-Type':'application/json',...(opt.headers||{})},...opt});if(!r.ok)throw new Error('HTTP '+r.status);return await r.json()}catch(e){console.warn('Evidence API:',e.message);return null}}
function localEvent(ev){const k='grh0652.evidence.'+student();const a=JSON.parse(localStorage.getItem(k)||'[]');a.push({...ev,student_id:student(),ts:new Date().toISOString()});localStorage.setItem(k,JSON.stringify(a.slice(-2000)))}
window.EVIDENCE={
 api:API,
 async event(ev){localEvent(ev);return call('/api/evidence',{method:'POST',body:JSON.stringify({...ev,student_id:student(),course_id:'GRH0652_UT1'})})},
 async state(state){localStorage.setItem('grh0652.remoteState.'+student(),JSON.stringify(state));return call('/api/state/'+encodeURIComponent(student()),{method:'PUT',body:JSON.stringify({course_id:'GRH0652_UT1',state})})},
 async load(){return call('/api/state/'+encodeURIComponent(student())+'?course_id=GRH0652_UT1')},
 async config(){return call('/api/config/GRH0652_UT1')},
 async result(payload){return call('/api/result',{method:'POST',body:JSON.stringify({...payload,student_id:student(),course_id:'GRH0652_UT1'})})}
};
})();