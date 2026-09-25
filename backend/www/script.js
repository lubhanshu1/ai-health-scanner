const API="";
let mode="simple",riskChart=null,lastResult=null,chatHistory=[];
const $=id=>document.getElementById(id);
const token=()=>localStorage.getItem("token");

function jsonHeaders(auth=true){const h={"Content-Type":"application/json"};if(auth&&token())h.Authorization="Bearer "+token();return h}
function toast(message){const el=$("toast");el.textContent=message;el.classList.remove("hidden");el.classList.add("show");clearTimeout(window.__toast);window.__toast=setTimeout(()=>el.classList.add("hidden"),2800)}
function formatApiError(data,fallback){const d=data?.detail;if(Array.isArray(d))return d.map(x=>{const loc=Array.isArray(x?.loc)?x.loc.filter(Boolean).join(" → "):"";return loc?loc+": "+(x?.msg||"Invalid value"):(x?.msg||"Invalid value")}).join(" | ");if(typeof d==="string")return d;if(d&&typeof d==="object")return d.message||d.msg||JSON.stringify(d);return data?.message||fallback}
async function api(path,options={}){const res=await fetch(API+path,options);let data={};try{data=await res.json()}catch{}const authEndpoint=path==="/login"||path==="/register";if(res.status===401&&!authEndpoint&&token()){localStorage.removeItem("token");showLogin();throw Error("Session expired. Please log in again")}if(!res.ok)throw Error(formatApiError(data,"Request failed ("+res.status+")"));return data}

function showLogin(){$("loginPage").classList.remove("hidden");$("dashboard").classList.add("hidden")}
function showDashboard(){$("loginPage").classList.add("hidden");$("dashboard").classList.remove("hidden")}
function setMode(next){
 mode=next;
 const titles={simple:"Overview screening",heart:"Heart risk screening",diabetes:"Diabetes risk screening"};
 $("modeTitle").textContent=titles[next];$("chartMode").textContent=next==="simple"?"All scans":next[0].toUpperCase()+next.slice(1);
 document.querySelectorAll(".mode-btn").forEach(b=>b.classList.toggle("active",b.dataset.mode===next));
 const groups={simple:$("simpleFields"),heart:$("heartFields"),diabetes:$("diabetesFields")};
 Object.entries(groups).forEach(([name,group])=>{const active=name===next;group.classList.toggle("hidden",!active);group.querySelectorAll("input,select").forEach(i=>i.disabled=!active)});
 $("healthForm").reset();$("result").classList.add("hidden");setEngine("READY","ready");
}
function setEngine(label,state){$("engineState").textContent=label;$("engineState").className="status-badge "+(state||"ready")}
async function login(){
 const email=$("authEmail").value.trim(),password=$("authPassword").value;$("loginStatus").textContent="";
 if(!email||!password){$("loginStatus").textContent="Enter your email and password.";return}
 localStorage.removeItem("token");
 try{const data=await api("/login",{method:"POST",headers:jsonHeaders(false),body:JSON.stringify({email,password})});localStorage.setItem("token",data.access_token);await boot()}catch(e){$("loginStatus").textContent=e.message}
}
async function register(){
 const email=$("authEmail").value.trim(),password=$("authPassword").value;$("loginStatus").textContent="";
 if(!email||!password){$("loginStatus").textContent="Enter an email and password first.";return}
 if(password.length<8){$("loginStatus").textContent="Password must be at least 8 characters.";return}
 try{await api("/register",{method:"POST",headers:jsonHeaders(false),body:JSON.stringify({email,password})});$("loginStatus").textContent="Account created. Click Login.";toast("Account created successfully")}catch(e){$("loginStatus").textContent=e.message}
}
async function loadProfile(){const d=await api("/profile",{headers:jsonHeaders()});$("profileBox").textContent=d.email;$("avatar").textContent=(d.email||"U")[0].toUpperCase()}
async function loadAnalytics(){
 const d=await api("/analytics",{headers:jsonHeaders()});$("totalScans").textContent=d.total_scans;$("lowScans").textContent=d.low;$("moderateScans").textContent=d.moderate;$("highScans").textContent=d.high;$("chartTotal").textContent=d.total_scans;
 const empty=d.total_scans===0;$("chartEmpty").classList.toggle("hidden",!empty);$("chartCenter").classList.toggle("hidden",empty);
 if(riskChart)riskChart.destroy();
 riskChart=new Chart($("riskChart"),{type:"doughnut",data:{labels:["Low","Moderate","High"],datasets:[{data:[d.low,d.moderate,d.high],backgroundColor:["#38bdf8","#fb7185","#fb923c"],borderColor:"#0b1225",borderWidth:4,hoverOffset:7}]},options:{responsive:true,maintainAspectRatio:false,cutout:"75%",plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>" "+ctx.label+": "+ctx.raw}}}}});
}
async function loadHistory(){
 const data=await api("/history",{headers:jsonHeaders()});const box=$("history");box.replaceChildren();
 if(!data.length){const p=document.createElement("p");p.className="muted";p.textContent="No screening events yet. Your first scan will appear here.";box.appendChild(p);return}
 data.forEach(item=>{const card=document.createElement("div");card.className="history-card";const type=document.createElement("strong");type.textContent=item.type;const mid=document.createElement("div");const pill=document.createElement("span");const cls=item.risk==="Low"?"risk-low":item.risk==="High"?"risk-high":"risk-moderate";pill.className="risk-pill "+cls;pill.textContent=item.risk;const score=document.createElement("span");score.className="score";score.textContent=Math.round(item.score*100)+"% score";mid.append(pill,score);const date=document.createElement("small");date.textContent=new Date(item.date).toLocaleString();card.append(type,mid,date);box.appendChild(card)})
}
async function loadTelemetry(){
 try{const d=await api("/health");const dm=d.models?.diabetes,hm=d.models?.heart;const label=m=>typeof m==="object"?((m.status||"ready")+(m.accuracy!=null?" • "+Math.round(m.accuracy*100)+"% validation":"")):String(m||"unknown");$("diabetesModel").textContent=label(dm);$("heartModel").textContent=label(hm);$("aiModel").textContent=d.chat==="openai"?"OpenAI":d.chat==="local-safe-assistant"?"Nexus local assistant":"Safe fallback";$("systemStatus").textContent="v"+d.version+" • live"}catch{$("systemStatus").textContent="API unavailable"}
}
function payloadForMode(){
 if(mode==="simple")return{age:+$("age").value,glucose:+$("glucose").value,bp:+$("bp").value,bmi:+$("bmi").value};
 if(mode==="heart")return{age:+$("h_age").value,sex:+$("sex").value,trestbps:+$("trestbps").value,chol:+$("chol").value,thalach:+$("thalach").value,oldpeak:+$("oldpeak").value};
 return{pregnancies:+$("pregnancies").value,glucose:+$("d_glucose").value,blood_pressure:+$("blood_pressure").value,skin_thickness:+$("skin_thickness").value,insulin:+$("insulin").value,bmi:+$("d_bmi").value,diabetes_pedigree:+$("diabetes_pedigree").value,age:+$("d_age").value}
}
function validateCurrent(){const ids=mode==="simple"?["age","glucose","bp","bmi"]:mode==="heart"?["h_age","trestbps","chol","thalach","oldpeak"]:["pregnancies","d_glucose","blood_pressure","skin_thickness","insulin","d_bmi","diabetes_pedigree","d_age"];const bad=ids.find(id=>{const el=$(id);return !el.value||!Number.isFinite(Number(el.value))});if(bad){$(bad).focus();return"Fill all screening fields first."}return null}
function buildResult(d){
 const wrap=document.createElement("div");wrap.className="result";
 const head=document.createElement("div");head.className="result-head";
 const left=document.createElement("div");const label=document.createElement("div");label.className="result-label";label.textContent="SCREENING SIGNAL";const title=document.createElement("div");title.className="risk-big";title.textContent=d.risk_level+" risk";left.append(label,title);
 const score=document.createElement("div");score.className="result-score";score.textContent=Math.round(d.risk_score*100)+"%";head.append(left,score);wrap.appendChild(head);
 const factorRow=document.createElement("div");factorRow.className="factor-row";(d.reasons?.length?d.reasons:["No major screening factors detected"]).forEach(x=>{const chip=document.createElement("span");chip.className="factor-chip";chip.textContent=x;factorRow.appendChild(chip)});wrap.appendChild(factorRow);
 const meta=document.createElement("div");meta.className="result-meta";[["ENGINE",d.method||"screening"],["UPDATED",new Date().toLocaleTimeString()]].forEach(([k,v])=>{const cell=document.createElement("div");const s=document.createElement("span");s.textContent=k;const b=document.createElement("strong");b.textContent=v;cell.append(s,b);meta.appendChild(cell)});wrap.appendChild(meta);
 return wrap
}
async function runScan(e){
 e.preventDefault();const error=validateCurrent();if(error){toast(error);return}
 const btn=$("scanBtn"),progress=$("scanProgress"),result=$("result");btn.disabled=true;setEngine("RUNNING","ready");progress.classList.remove("hidden");result.classList.add("hidden");
 const stages=["Validating inputs…","Running screening model…","Generating explainable factors…","Saving live artifact…"];let n=0;const timer=setInterval(()=>{if(n<stages.length){$("progressText").textContent=stages[n];$("progressStep").textContent=String(n+1).padStart(2,"0")+" / 04";n++}},350);
 const path=mode==="simple"?"/predict-simple":mode==="heart"?"/heart-risk":"/diabetes-risk";
 try{const d=await api(path,{method:"POST",headers:jsonHeaders(),body:JSON.stringify(payloadForMode())});lastResult=d;result.replaceChildren();result.appendChild(buildResult(d));result.classList.remove("hidden");$("lastUpdated").textContent="Last scan · "+new Date().toLocaleTimeString();setEngine("COMPLETE","live");toast("Live screening artifact generated");await Promise.all([loadHistory(),loadAnalytics()])}
 catch(e){result.classList.remove("hidden");result.textContent=e.message;setEngine("ERROR","safe");toast(e.message)}
 finally{clearInterval(timer);progress.classList.add("hidden");btn.disabled=false}
}
async function uploadImage(){const file=$("imageInput").files[0];if(!file){$("imageStatus").textContent="Choose an image first.";return}const b=$("imageBtn");b.disabled=true;$("imageStatus").textContent="Uploading and validating…";try{const form=new FormData();form.append("image",file);const res=await fetch("/scan-image",{method:"POST",headers:{Authorization:"Bearer "+token()},body:form});let d={};try{d=await res.json()}catch{}if(res.status===401){localStorage.removeItem("token");showLogin();throw Error("Session expired. Please log in again")}if(!res.ok)throw Error(formatApiError(d,"Upload failed"));$("imageStatus").textContent=d.message;toast("Image intake completed")}catch(e){$("imageStatus").textContent=e.message}finally{b.disabled=false}}
function appendChat(who,text){
 const box=$("chatBox");const welcome=box.querySelector(".chat-welcome");if(welcome)welcome.remove();
 const row=document.createElement("div");row.className="chat-message "+(who==="You"?"user":"ai");const bubble=document.createElement("div");bubble.className="bubble";bubble.textContent=text;const time=document.createElement("span");time.className="bubble-time";time.textContent=new Date().toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"});bubble.appendChild(time);row.appendChild(bubble);box.appendChild(row);box.scrollTop=box.scrollHeight
}
function setTyping(on){$("typing").classList.toggle("hidden",!on)}
async function sendChat(prefilled){
 const input=$("chatInput"),message=(prefilled||input.value).trim();if(!message)return;if(!prefilled)input.value="";
 appendChat("You",message);chatHistory.push({role:"user",content:message});chatHistory=chatHistory.slice(-8);
 const b=$("sendChat");b.disabled=true;setTyping(true);
 try{const d=await api("/chat",{method:"POST",headers:jsonHeaders(),body:JSON.stringify({message,history:chatHistory})});appendChat("AI",d.reply);chatHistory.push({role:"assistant",content:d.reply});chatHistory=chatHistory.slice(-8);$("chatStatus").textContent=d.mode==="openai"?"OpenAI · contextual":"Nexus local · contextual"}catch(e){appendChat("AI",e.message)}finally{setTyping(false);b.disabled=false;input.focus()}
}
function downloadPDF(){if(!lastResult){toast("Run a screening first.");return}const{jsPDF}=window.jspdf,doc=new jsPDF();doc.setFontSize(20);doc.text("AI Health Scanner — Screening Report",20,20);doc.setFontSize(12);doc.text("Risk level: "+lastResult.risk_level,20,40);doc.text("Screening score: "+Math.round(lastResult.risk_score*100)+"%",20,50);doc.text("Engine: "+(lastResult.method||"screening"),20,60);doc.text("Screening only; not a diagnosis.",20,75);doc.text("Generated: "+new Date().toLocaleString(),20,90);doc.save("AI_Health_Scanner_Report.pdf");toast("Report artifact generated")}
function clearForm(){$("healthForm").reset();$("result").classList.add("hidden");setEngine("READY","ready");$("lastUpdated").textContent="Ready for a new screening";toast("Fields cleared")}
async function boot(){if(!token()){showLogin();return}try{showDashboard();setMode("simple");await Promise.all([loadProfile(),loadHistory(),loadAnalytics(),loadTelemetry()])}catch(e){localStorage.removeItem("token");showLogin()}}
$("loginBtn").onclick=login;$("registerBtn").onclick=register;$("logoutBtn").onclick=()=>{localStorage.removeItem("token");showLogin()};document.querySelectorAll(".mode-btn").forEach(b=>b.onclick=()=>setMode(b.dataset.mode));$("healthForm").onsubmit=runScan;$("refreshBtn").onclick=()=>Promise.all([loadHistory(),loadAnalytics(),loadTelemetry()]);$("historyRefresh").onclick=()=>Promise.all([loadHistory(),loadAnalytics()]);$("downloadBtn").onclick=downloadPDF;$("clearBtn").onclick=clearForm;$("imageBtn").onclick=uploadImage;$("chatToggle").onclick=()=>{$("chatbot").classList.toggle("hidden");if(!$("chatbot").classList.contains("hidden"))$("chatInput").focus()};$("closeChat").onclick=()=>{$("chatbot").classList.add("hidden")};$("sendChat").onclick=()=>sendChat();$("chatInput").addEventListener("keydown",e=>{if(e.key==="Enter")sendChat()});document.querySelectorAll("[data-prompt]").forEach(b=>b.onclick=()=>sendChat(b.dataset.prompt));boot();
