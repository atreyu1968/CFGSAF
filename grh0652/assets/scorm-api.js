(function(){
const DEFAULTS={'cmi.core.lesson_status':'not attempted','cmi.core.score.raw':'0','cmi.core.score.min':'0','cmi.core.score.max':'100','cmi.core.lesson_location':'inicio','cmi.suspend_data':'','cmi.core.exit':'','cmi.core.session_time':'0000:00:00.00'};
let key='grh0652.scorm.GRH0652_UT1.alumno',data={},initialized=false,lastError='0';
function load(){try{data=Object.assign({},DEFAULTS,JSON.parse(localStorage.getItem(key)||'{}'))}catch(e){data=Object.assign({},DEFAULTS)}}
function persist(){try{localStorage.setItem(key,JSON.stringify(data));window.dispatchEvent(new CustomEvent('scormcommit',{detail:{score:data['cmi.core.score.raw'],status:data['cmi.core.lesson_status'],location:data['cmi.core.lesson_location'],data}}));return true}catch(e){lastError='101';return false}}
const api={
LMSInitialize(){initialized=true;lastError='0';return'true'},
LMSFinish(){persist();initialized=false;lastError='0';return'true'},
LMSGetValue(k){lastError='0';if(k==='cmi.core.student_name')return window.SCORM_STUDENT_ID||'';if(k==='cmi.core.student_id')return window.SCORM_STUDENT_ID||'';return data[k]??''},
LMSSetValue(k,v){data[k]=String(v);lastError='0';return'true'},
LMSCommit(){return persist()?'true':'false'},
LMSGetLastError(){return lastError},
LMSGetErrorString(c){return c==='0'?'No error':'SCORM local storage error'},
LMSGetDiagnostic(){return''}
};
window.SCORM_API={api,configure(o={}){key='grh0652.scorm.'+(o.courseId||'course')+'.'+(o.studentId||'alumno');window.SCORM_STUDENT_ID=o.studentId||'alumno';load()},commit:persist,getData(){return data}};
load();
})();