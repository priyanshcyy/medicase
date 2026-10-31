import {useState,useEffect,useRef} from "react"
import {api} from "./api.js"

export const KL={bp:"Blood pressure",sugar:"Blood sugar",weight:"Weight",pulse:"Pulse",spo2:"Oxygen saturation",temp:"Temperature",dose:"Medicine"}
const UN={bp:"mmHg",sugar:"mg/dL",weight:"kg",pulse:"bpm",spo2:"%",temp:"°C"}
const SUG={1:["08:00"],2:["08:00","20:00"],3:["08:00","14:00","20:00"],4:["07:00","12:00","17:00","21:00"],5:["07:00","10:00","13:00","17:00","21:00"],6:["06:00","09:00","12:00","15:00","18:00","21:00"]}
const fmt=r=>r.kind==="bp"?`${r.v1}/${r.v2}`:`${r.v1}`
const tm=s=>new Date(s.replace(" ","T")).getTime()
const lvl=f=>f==="urgent"?"lock":f?"warn":"ok"
const err=e=>alert(e.message||e)

/* ---------- small SVG line chart with the normal range shaded ---------- */
function Chart({rows,lines,bands=[],h=190}){
  const W=640,L=38,R=10,Tp=26,B=22
  if(!rows.length)return <p className="muted small">No readings in the last 30 days.</p>
  const xs=rows.map(r=>tm(r.at)),x0=Math.min(...xs),x1=Math.max(...xs,x0+1)
  const vals=rows.flatMap(r=>lines.map(l=>r[l.k])).filter(v=>v!=null).concat(bands.flat())
  let y0=Math.min(...vals),y1=Math.max(...vals);const pad=((y1-y0)||10)*.12;y0-=pad;y1+=pad
  const X=t=>L+(t-x0)/(x1-x0)*(W-L-R),Y=v=>Tp+(1-(v-y0)/(y1-y0))*(h-Tp-B)
  const ticks=[0,1,2,3].map(i=>y0+(y1-y0)*i/3)
  return <svg viewBox={`0 0 ${W} ${h}`} className="chart" role="img">
    {bands.map(([a,b],i)=><rect key={i} x={L} width={W-L-R} y={Y(b)} height={Math.max(Y(a)-Y(b),0)} fill="#dff3ea" opacity=".7"/>)}
    {ticks.map((v,i)=><g key={i}><line x1={L} x2={W-R} y1={Y(v)} y2={Y(v)} stroke="#e6edf2"/><text x={L-5} y={Y(v)+4} textAnchor="end" fontSize="10" fill="#718397">{Math.round(v)}</text></g>)}
    {lines.map(l=>{const pts=rows.filter(r=>r[l.k]!=null);return <g key={l.k}><polyline fill="none" stroke={l.c} strokeWidth="2" points={pts.map(r=>`${X(tm(r.at))},${Y(r[l.k])}`).join(" ")}/>
      {pts.map((r,i)=><circle key={i} cx={X(tm(r.at))} cy={Y(r[l.k])} r="3.2" fill={r.flag?(r.flag==="urgent"?"#c0455a":"#e0902b"):l.c}><title>{`${r.at}: ${fmt(r)} ${r.unit||""}${r.why?" - "+r.why:""}${r.note?" ("+r.note+")":""}`}</title></circle>)}</g>})}
    <text x={L} y={h-5} fontSize="10" fill="#718397">{rows[0].at.slice(5,10)}</text><text x={W-R} y={h-5} textAnchor="end" fontSize="10" fill="#718397">{rows[rows.length-1].at.slice(5,10)}</text>
    <g fontSize="10" fill="#718397">{lines.map((l,i)=><g key={l.k}><circle cx={L+6+i*80} cy={11} r="4" fill={l.c}/><text x={L+14+i*80} y={15}>{l.n}</text></g>)}</g>
  </svg>
}

function Card({k,v,sub,f}){return <div><small>{k}</small><b>{v}</b>{sub&&<small>{sub}</small>}{f&&<span className={"tag "+lvl(f)}>{f.toUpperCase()}</span>}</div>}

/* ---------- Dashboard (doctor and patient) ---------- */
export function Dashboard({pid,me,ver=0}){
  const [d,setD]=useState(null),[e,setE]=useState("")
  const load=()=>api(`/patients/${pid}/dashboard`).then(setD).catch(x=>setE(x.message))
  useEffect(()=>{load()},[pid,ver])
  if(e)return <p className="err">{e}</p>
  if(!d)return <p className="muted">Loading…</p>
  const {stats:S,series:R,limits:L}=d,bp=S.bp,sg=S.sugar,doc=me.role==="doctor"
  const ads=d.reminders.map(r=>r.adh&&r.adh.pct).filter(x=>x!=null),adh=ads.length?Math.round(ads.reduce((a,b)=>a+b,0)/ads.length):null
  return <div className="stack">
    <div className="panel"><h3>Monitoring overview <span className="muted small">last 7 days · normal range shaded</span></h3>
      <div className="facts">
        <Card k="Latest BP" v={bp.latest?`${fmt(bp.latest)} mmHg`:"–"} sub={bp.latest?.at} f={bp.latest?.flag}/>
        <Card k="BP average (7d)" v={bp.avg7?bp.avg7.join("/"):"–"} sub={bp.in_range!=null?`${bp.in_range}% of readings in range (30d)`:"No readings"}/>
        <Card k="Latest sugar" v={sg.latest?`${sg.latest.v1} mg/dL`:"–"} sub={sg.latest?(sg.latest.note||"")+" "+sg.latest.at:""} f={sg.latest?.flag}/>
        <Card k="Sugar average (7d)" v={sg.avg7??"–"} sub={sg.in_range!=null?`${sg.in_range}% in range (30d)`:"No readings"}/>
        <Card k="Reminder adherence" v={adh!=null?adh+"%":"–"} sub="readings recorded vs. expected (7d)"/></div></div>
    {d.alerts.length>0&&<div className="panel"><h3>Flagged readings <span className="muted small">last 7 days</span></h3>
      {d.alerts.slice(0,8).map(a=><div className="row" key={a.id}><span><b>{KL[a.kind]} {fmt(a)} {a.unit}</b><small>{a.why} · {a.at}{a.note?` · ${a.note}`:""}</small></span><span className={"tag "+lvl(a.flag)}>{a.flag.toUpperCase()}</span></div>)}</div>}
    <div className="panel"><h3>Blood pressure <span className="muted small">{bp.n30} readings · 30 days</span></h3><Chart rows={R.bp.map(r=>({...r,sys:r.v1,dia:r.v2}))} lines={[{k:"sys",c:"#c0455a",n:"Systolic"},{k:"dia",c:"#176d91",n:"Diastolic"}]} bands={[[L.sys_lo,L.sys_hi],[L.dia_lo,L.dia_hi]]}/></div>
    <div className="panel"><h3>Blood sugar <span className="muted small">{sg.n30} readings · 30 days</span></h3><Chart rows={R.sugar.map(r=>({...r,v:r.v1}))} lines={[{k:"v",c:"#7a5bc7",n:"mg/dL"}]} bands={[[L.sugar_lo,L.sugar_hi]]}/></div>
    {["weight","pulse","spo2","temp"].filter(k=>R[k].length).map(k=><div className="panel" key={k}><h3>{KL[k]} <span className="muted small">{UN[k]}</span></h3><Chart h={150} rows={R[k].map(r=>({...r,v:r.v1}))} lines={[{k:"v",c:"#176d91",n:UN[k]}]}/></div>)}
    <div className="panel"><h3>Regular lab values</h3>{d.labs.length?<div className="scroll"><table><thead><tr><th>Test</th><th>Latest</th><th>Reference</th><th>Previous</th><th>Trend</th><th>Date</th></tr></thead><tbody>
      {d.labs.map(l=>{const t=l.prev?(l.last.v1>l.prev.v1?"▲":l.last.v1<l.prev.v1?"▼":"–"):"–";return <tr key={l.name}><td><b>{l.name}</b></td><td>{l.last.v1} {l.unit} {l.last.flag&&<span className={"tag "+lvl(l.last.flag)}>{l.last.flag.toUpperCase()}</span>}</td><td>{l.ref||"–"}</td><td>{l.prev?l.prev.v1:"–"}</td><td>{t}</td><td>{l.last.at.slice(0,10)}</td></tr>})}</tbody></table></div>:<p className="muted small">No lab values yet.</p>}</div>
    <div className="grid2"><div className="panel"><h3>Reminders</h3>{d.reminders.map(r=><div className="row" key={r.id}><span><b>{r.label}</b><small>{r.status==="proposed"?`Waiting for patient to set ${r.per_day} time(s)/day`:`${r.times.join(", ")}${r.until?` · until ${r.until}`:""}`}</small></span>
        <span style={{minWidth:90,textAlign:"right"}}>{r.adh&&r.adh.pct!=null?<><b>{r.adh.pct}%</b><div className="meter"><i style={{width:r.adh.pct+"%"}}/></div></>:<span className={"tag "+(r.status==="active"?"ok":"warn")}>{r.status.toUpperCase()}</span>}</span></div>)}{!d.reminders.length&&<p className="muted small">No reminders.</p>}</div>
      <div className="panel"><h3>Regular tests</h3>{d.orders.map(o=><div className="row" key={o.id}><span><b>{o.name}</b><small>every {o.every_days} days · last: {o.last||"never"} · due {o.due}</small></span><span><span className={"tag "+(o.status==="ok"?"ok":o.status==="overdue"?"lock":"warn")}>{o.status.toUpperCase()}</span>{doc&&<button className="link" onClick={()=>api(`/patients/${pid}/orders/${o.id}`,{method:"DELETE"}).then(load).catch(err)}> ✕</button>}</span></div>)}{!d.orders.length&&<p className="muted small">No regular tests ordered.</p>}</div></div>
    {doc&&<DoctorTools pid={pid} d={d} reload={load}/>}
    <p className="muted small">Readings are recorded by the patient or entered by a doctor. Highlighted values follow the limits above (editable per patient) and are not a diagnosis.</p>
  </div>
}

function DoctorTools({pid,d,reload}){
  const [rq,setRq]=useState({kind:"bp",per_day:3,days:7,label:"",text:""}),[lim,setLim]=useState({...d.limits}),[od,setOd]=useState({name:"",every_days:90}),[lb,setLb]=useState({name:"",value:"",unit:"",ref_lo:"",ref_hi:"",date:new Date().toISOString().slice(0,10)})
  const run=(fn,ok)=>async e=>{e.preventDefault();try{await fn();ok&&alert(ok);reload()}catch(x){err(x)}}
  const num=v=>v===""?null:Number(v)
  const LK=[["sys_hi","Systolic: alert at/above"],["sys_lo","Systolic: alert below"],["dia_hi","Diastolic: alert at/above"],["dia_lo","Diastolic: alert below"],["sugar_hi","Sugar: alert at/above"],["sugar_lo","Sugar: alert below"]]
  return <div className="panel"><h3>Doctor tools</h3>
    <form onSubmit={run(()=>api(`/patients/${pid}/request-monitoring`,{body:{...rq,per_day:+rq.per_day,days:+rq.days}}),"Request sent to the patient.")}><b>Ask the patient to monitor</b>
      <div className="bar"><select value={rq.kind} onChange={e=>setRq({...rq,kind:e.target.value})}>{Object.entries(KL).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select>
        {rq.kind==="dose"&&<input placeholder="Medicine name" value={rq.label} onChange={e=>setRq({...rq,label:e.target.value})}/>}
        <input type="number" min="1" max="6" style={{maxWidth:90}} value={rq.per_day} onChange={e=>setRq({...rq,per_day:e.target.value})} title="times per day"/><span className="muted small" style={{alignSelf:"center"}}>times/day for</span>
        <input type="number" min="1" max="90" style={{maxWidth:90}} value={rq.days} onChange={e=>setRq({...rq,days:e.target.value})}/><span className="muted small" style={{alignSelf:"center"}}>days</span></div>
      <input placeholder="Message to the patient (optional)" value={rq.text} onChange={e=>setRq({...rq,text:e.target.value})} style={{width:"100%",marginBottom:8}}/><button className="btn sm">Send request</button></form><hr/>
    <form onSubmit={run(()=>api(`/patients/${pid}/limits`,{method:"PUT",body:{data:lim}}),"Limits saved.")}><b>Alert limits for this patient</b>
      <div className="facts" style={{margin:"8px 0"}}>{LK.map(([k,t])=><label key={k}>{t}<input type="number" value={lim[k]} onChange={e=>setLim({...lim,[k]:e.target.value})}/></label>)}</div><button className="btn sm ghost">Save limits</button></form><hr/>
    <form onSubmit={run(()=>api(`/patients/${pid}/orders`,{body:{name:od.name,every_days:+od.every_days}}),"Regular test added.")}><b>Order a regular test</b>
      <div className="bar"><input required placeholder="Test name (e.g. HbA1c)" value={od.name} onChange={e=>setOd({...od,name:e.target.value})}/><input type="number" min="7" style={{maxWidth:110}} value={od.every_days} onChange={e=>setOd({...od,every_days:e.target.value})}/><span className="muted small" style={{alignSelf:"center"}}>days apart</span><button className="btn sm">Add</button></div></form><hr/>
    <form onSubmit={run(()=>api(`/patients/${pid}/labs`,{body:{name:lb.name,value:+lb.value,unit:lb.unit,ref_lo:num(lb.ref_lo),ref_hi:num(lb.ref_hi),date:lb.date}}),"Lab value added.")}><b>Add a lab value</b>
      <div className="bar"><input required placeholder="Test" value={lb.name} onChange={e=>setLb({...lb,name:e.target.value})}/><input required type="number" step="any" placeholder="Value" style={{maxWidth:100}} value={lb.value} onChange={e=>setLb({...lb,value:e.target.value})}/><input placeholder="Unit" style={{maxWidth:90}} value={lb.unit} onChange={e=>setLb({...lb,unit:e.target.value})}/>
        <input type="number" step="any" placeholder="Ref low" style={{maxWidth:90}} value={lb.ref_lo} onChange={e=>setLb({...lb,ref_lo:e.target.value})}/><input type="number" step="any" placeholder="Ref high" style={{maxWidth:90}} value={lb.ref_hi} onChange={e=>setLb({...lb,ref_hi:e.target.value})}/><input type="date" required value={lb.date} onChange={e=>setLb({...lb,date:e.target.value})}/><button className="btn sm">Add</button></div></form></div>
}

/* ---------- Messages ---------- */
export function Messages({pid,me,onChange}){
  const [d,setD]=useState(null),[t,setT]=useState(""),[to,setTo]=useState(""),[tt,setTt]=useState({}),end=useRef(null),pat=me.role==="patient"
  const load=()=>api(`/patients/${pid}/messages`).then(r=>{setD(r);setTo(x=>x||r.doctors[0]?.id||"")}).catch(()=>{})
  useEffect(()=>{load();const i=setInterval(load,15000);return()=>clearInterval(i)},[pid])
  useEffect(()=>{end.current?.scrollIntoView({block:"nearest"})},[d?.messages.length])
  const send=async e=>{e.preventDefault();if(!t.trim())return;try{await api(`/patients/${pid}/messages`,{body:{text:t,to}});setT("");load()}catch(x){err(x)}}
  const act=async(m,status)=>{try{await api(`/me/reminders/${m.rid}`,{body:{status,times:status==="active"?(tt[m.rid]||SUG[m.per_day]||SUG[3]):[]}});await load();onChange&&onChange()}catch(x){err(x)}}
  if(!d)return <p className="muted">Loading…</p>
  return <div className="panel"><h3>Messages</h3>
    <div className="msgs">{d.messages.map(m=>{const mine=m.sender===me.role;return <div key={m.id} className={"msg "+(mine?"me":"them")}><small>{m.sender==="doctor"?m.doctor:"Patient"} · {m.at}</small><div>{m.text}</div>
      {m.kind==="request"&&m.rid&&(m.rstatus==="proposed"?(pat?<div className="reqbox"><small>Set your reminder times ({m.per_day} per day):</small><div className="bar">{(tt[m.rid]||SUG[m.per_day]||SUG[3]).map((x,i)=><input key={i} type="time" style={{minWidth:110,flex:"0 0 auto"}} value={x} onChange={e=>{const a=[...(tt[m.rid]||SUG[m.per_day]||SUG[3])];a[i]=e.target.value;setTt({...tt,[m.rid]:a})}}/>)}</div>
        <button className="btn sm" onClick={()=>act(m,"active")}>Accept &amp; set reminders</button> <button className="btn sm ghost" onClick={()=>act(m,"stopped")}>Decline</button></div>:<small className="muted">Waiting for the patient to set reminder times.</small>)
        :<small className="muted">{m.rstatus==="active"?`✔ Reminders active${m.rtimes.length?` at ${m.rtimes.join(", ")}`:""}`:"Reminders stopped or finished."}</small>)}</div>})}
      {!d.messages.length&&<p className="muted small">No messages yet.</p>}<div ref={end}/></div>
    <form onSubmit={send}>{pat&&<div className="bar">{d.doctors.length?<select value={to} onChange={e=>setTo(e.target.value)}>{d.doctors.map(x=><option key={x.id} value={x.id}>To: {x.name}</option>)}</select>:<span className="muted small">No doctor has access to your record yet, so you can't send messages.</span>}</div>}
      <textarea rows="2" placeholder={pat?"Write to your doctor…":"Write to the patient…"} value={t} onChange={e=>setT(e.target.value)} maxLength={1000}/><button className="btn" disabled={pat&&!to}>Send</button></form></div>
}

/* ---------- Patient: today's checklist, in-app reminders, quick logging ---------- */
const hm=()=>{const n=new Date();return String(n.getHours()).padStart(2,"0")+":"+String(n.getMinutes()).padStart(2,"0")}
export function Today({ver=0,onChange}){
  const [rs,setRs]=useState([]),[due,setDue]=useState([]),[form,setForm]=useState(null),[add,setAdd]=useState(false),[res,setRes]=useState(null),fired=useRef(new Set())
  const load=()=>api("/me/today").then(setRs).catch(()=>{})
  useEffect(()=>{load()},[ver])
  useEffect(()=>{const tick=()=>{const now=hm(),day=new Date().toDateString()
    rs.forEach(r=>r.times.forEach(t=>{const k=r.id+t+day;if(t===now&&!fired.current.has(k)){fired.current.add(k);setDue(d=>[...d,{k,r,t}])
      if("Notification" in window&&Notification.permission==="granted")new Notification("MediCase reminder",{body:`Time for: ${r.label} (${t})`})}}))}
    tick();const i=setInterval(tick,15000);return()=>clearInterval(i)},[rs])
  const done=()=>{load();onChange&&onChange()}
  const takeDose=async r=>{try{await api("/me/measures",{body:{kind:"dose",v1:1,note:r.label}});setDue(d=>d.filter(x=>x.r.id!==r.id));done()}catch(e){err(e)}}
  const now=hm(),ahead=(()=>{const d=new Date(Date.now()+90*6e4);if(d.getDate()!==new Date().getDate())return "23:59";return String(d.getHours()).padStart(2,"0")+":"+String(d.getMinutes()).padStart(2,"0")})()
  return <div className="panel"><h3>Today <span className="muted small">your checks and medicines</span></h3>
    {due.map(x=><div className="banner" key={x.k}>⏰ Time for <b>{x.r.label}</b> ({x.t})<span>{x.r.kind==="dose"?<button className="btn sm" onClick={()=>takeDose(x.r)}>Taken</button>:<button className="btn sm" onClick={()=>{setForm({kind:x.r.kind});setDue(d=>d.filter(y=>y.k!==x.k))}}>Record now</button>} <button className="link" onClick={()=>setDue(d=>d.filter(y=>y.k!==x.k))}>Dismiss</button></span></div>)}
    {rs.map(r=><div className="row" key={r.id}><span><b>{r.label}</b><small>{r.until?`until ${r.until}`:"ongoing"}</small></span>
      <span className="slots">{r.times.map((t,i)=>{const reach=r.times.filter(x=>x<=ahead).length,st=i<Math.min(r.done,reach)?"done":t<=now?"missed":"next";return <span key={t} className={"slot "+st} title={st}>{st==="done"?"✔":st==="missed"?"!":"○"} {t}</span>})}
        {r.kind==="dose"?<button className="btn sm" onClick={()=>takeDose(r)}>Taken</button>:<button className="btn sm" onClick={()=>setForm({kind:r.kind})}>Record</button>}
        <button className="link" title="Stop this reminder" onClick={()=>confirm(`Stop the ${r.label} reminder?`)&&api(`/me/reminders/${r.id}`,{body:{status:"stopped"}}).then(done).catch(err)}>✕</button></span></div>)}
    {!rs.length&&<p className="muted small">No active reminders. When a doctor asks you to monitor something, accept it in Messages, or add your own below.</p>}
    <div className="bar"><button className="btn ghost sm" onClick={()=>setForm({kind:"bp"})}>+ Record a reading</button><button className="btn ghost sm" onClick={()=>setAdd(!add)}>+ Add my own reminder</button>
      {"Notification" in window&&Notification.permission==="default"&&<button className="btn ghost sm" onClick={()=>Notification.requestPermission().then(()=>load())}>Enable browser alerts</button>}</div>
    <p className="muted small">Reminders appear here and as browser alerts while MediCase is open in a tab. They are not sent as SMS or phone push messages.</p>
    {res&&<div className={"banner "+(res.flag==="urgent"?"bad":res.flag?"":"good")}>{res.flag?<><b>{res.why}.</b> {res.advice}</>:"Saved."}<button className="link" onClick={()=>setRes(null)}>OK</button></div>}
    {form&&<LogForm kind={form.kind} onDone={r=>{setForm(null);setRes(r);done()}} onCancel={()=>setForm(null)}/>}
    {add&&<AddReminder onDone={()=>{setAdd(false);done()}}/>}</div>
}

function LogForm({kind:k0,onDone,onCancel}){
  const [k,setK]=useState(k0),[a,setA]=useState(""),[b,setB]=useState(""),[n,setN]=useState(k0==="sugar"?"Fasting":""),[busy,setBusy]=useState(false)
  const go=async e=>{e.preventDefault();setBusy(true);try{onDone(await api("/me/measures",{body:{kind:k,v1:+a,v2:k==="bp"?+b:null,note:n}}))}catch(x){err(x)}setBusy(false)}
  return <form className="logform" onSubmit={go}><b>Record a reading</b><div className="bar">
    <select value={k} onChange={e=>{setK(e.target.value);setN(e.target.value==="sugar"?"Fasting":"")}}>{Object.entries(KL).filter(([x])=>x!=="dose").map(([x,v])=><option key={x} value={x}>{v}</option>)}</select>
    <input required type="number" step="any" style={{maxWidth:120}} placeholder={k==="bp"?"Top (systolic)":"Value"} value={a} onChange={e=>setA(e.target.value)}/>
    {k==="bp"&&<input required type="number" style={{maxWidth:120}} placeholder="Bottom (diastolic)" value={b} onChange={e=>setB(e.target.value)}/>}
    {k==="sugar"&&<select value={n} onChange={e=>setN(e.target.value)}>{["Fasting","Before meal","After meal","Bedtime","Random"].map(x=><option key={x}>{x}</option>)}</select>}
    <span className="muted small" style={{alignSelf:"center"}}>{UN[k]}</span><button className="btn sm" disabled={busy}>Save</button><button type="button" className="ghost" onClick={onCancel}>Cancel</button></div></form>
}

function AddReminder({onDone}){
  const [k,setK]=useState("bp"),[l,setL]=useState(""),[t,setT]=useState("08:00, 20:00")
  const go=async e=>{e.preventDefault();try{await api("/me/reminders",{body:{kind:k,label:l,times:t.split(",").map(x=>x.trim()).filter(Boolean)}});onDone()}catch(x){err(x)}}
  return <form className="logform" onSubmit={go}><b>New reminder</b><div className="bar"><select value={k} onChange={e=>setK(e.target.value)}>{Object.entries(KL).map(([x,v])=><option key={x} value={x}>{v}</option>)}</select>
    {k==="dose"&&<input required placeholder="Medicine name" value={l} onChange={e=>setL(e.target.value)}/>}<input required placeholder="Times, e.g. 08:00, 14:00, 20:00" value={t} onChange={e=>setT(e.target.value)}/><button className="btn sm">Add</button></div></form>
}

/* ---------- Doctor: needs-attention panel ---------- */
export function Alerts({open}){
  const [a,setA]=useState(null)
  useEffect(()=>{const f=()=>api("/alerts").then(setA).catch(()=>{});f();const i=setInterval(f,30000);return()=>clearInterval(i)},[])
  if(!a||(!a.flagged.length&&!a.unread.length))return null
  return <div className="panel"><h3>Needs attention <span className="muted small">last 3 days</span></h3>
    {a.flagged.map(x=><div className="row" key={x.id}><span><b>{x.name}</b> <span className="muted small">{x.id}</span><small>{x.count} flagged reading(s) · latest: {x.latest} · {x.at}</small></span><span><span className={"tag "+lvl(x.worst)}>{x.worst.toUpperCase()}</span> <button className="btn sm" onClick={()=>open(x.id,"dash")}>Dashboard</button></span></div>)}
    {a.unread.map(x=><div className="row" key={"u"+x.id}><span><b>{x.name}</b> <span className="muted small">{x.id}</span><small>{x.n} unread message(s)</small></span><button className="btn sm ghost" onClick={()=>open(x.id,"msgs")}>Open messages</button></div>)}</div>
}
