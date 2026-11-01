import {DoctorAppts,PatientAppts} from "./Appointments.jsx"
import {useState,useEffect} from "react"
import {api,upload,setToken} from "./api.js"
import {Dashboard,Messages,Today,Alerts} from "./Monitor.jsx"
const KINDS=["Birth","Vaccination","Illness","Surgery","Prescription","Report","Discharge","X-ray","Scan","Other"]

export default function App(){
  const [me,setMe]=useState(null)
  if(!me)return <Login onLogin={u=>{setToken(u.token);setMe(u)}}/>
  return <div className="app"><header><b>✚ MediCase</b><span>{me.name} · {me.role}{me.city?` · ${me.city}`:""}</span><button className="ghost" onClick={()=>{setToken("");setMe(null)}}>Log out</button></header>
    {me.role==="doctor"?<Doctor me={me}/>:<Patient me={me}/>}</div>
}

function Login({onLogin}){
  const [role,setRole]=useState("doctor"),[id,setId]=useState(""),[pw,setPw]=useState(""),[err,setErr]=useState("")
  const go=async e=>{e.preventDefault();try{onLogin(await api("/login",{body:{role,id,password:pw}}))}catch(x){setErr(x.message)}}
  return <div className="gate"><form className="box" onSubmit={go}><h2>✚ MediCase</h2><p className="muted">Smarter Records. Better Continuity. Secure Care.</p>
    <div className="tabs">{["doctor","patient"].map(r=><button type="button" key={r} className={role===r?"on":""} onClick={()=>{setRole(r);setErr("")}}>{r==="doctor"?"Doctor":"Patient"} login</button>)}</div>
    <label>{role==="doctor"?"Doctor ID":"Patient ID"}<input value={id} onChange={e=>setId(e.target.value)} required/></label>
    <label>Password<input type="password" value={pw} onChange={e=>setPw(e.target.value)} required/></label>
    <p className="err">{err}</p><button className="btn wide">Log in</button>
    <p className="muted small">Demo: DR1001 / doc123 · MC1001 / pat123. Synthetic data only.</p></form></div>
}

function Doctor({me}){
  const [meta,setMeta]=useState({}),[f,setF]=useState({q:"",state:"",city:""}),[rows,setRows]=useState([]),[open,setOpen]=useState(null)
  useEffect(()=>{api("/meta").then(setMeta)},[])
  useEffect(()=>{if(open)return;const t=setTimeout(()=>api("/patients?"+new URLSearchParams(f)).then(setRows).catch(()=>{}),250);return()=>clearTimeout(t)},[f,open])
  if(open)return <Record pid={open.pid} start={open.view} me={me} back={()=>setOpen(null)}/>
  const go=(pid,view)=>setOpen({pid,view})
  return <><DoctorAppts open={go}/><Alerts open={go}/><div className="panel"><h3>Patient directory</h3>
    <p className="muted small">Search patients across states. A full record opens only with the patient's consent (or a logged emergency override).</p>
    <div className="bar"><input placeholder="Search name, patient ID or ABHA…" value={f.q} onChange={e=>setF({...f,q:e.target.value})}/>
      <select value={f.state} onChange={e=>setF({...f,state:e.target.value,city:""})}><option value="">All states</option>{Object.keys(meta).map(s=><option key={s}>{s}</option>)}</select>
      <select value={f.city} onChange={e=>setF({...f,city:e.target.value})}><option value="">All cities</option>{(f.state?meta[f.state]||[]:Object.values(meta).flat()).map(c=><option key={c}>{c}</option>)}</select></div>
    <div className="scroll"><table><thead><tr><th>Patient</th><th>ID</th><th>City</th><th>State</th><th>ABHA</th><th>Access</th><th></th></tr></thead><tbody>
      {rows.map(p=><tr key={p.id}><td><b>{p.name}</b></td><td>{p.id}</td><td>{p.city}</td><td>{p.state}</td><td>{p.abha}</td>
        <td><span className={"tag "+(p.access?"ok":"lock")}>{p.access?"OPEN":"LOCKED"}</span></td><td><button className="btn sm" onClick={()=>go(p.id,"docs")}>{p.access?"Open record":"View"}</button></td></tr>)}
      {!rows.length&&<tr><td colSpan="7" className="muted">No matching patients.</td></tr>}</tbody></table></div></div></>
}

function Locked({pid,back,reload,msg}){
  const [code,setCode]=useState(""),run=async fn=>{try{await fn();reload()}catch(e){alert(e.message)}}
  return <div className="panel center"><button className="ghost left" onClick={back}>← Back</button><div className="big">🔒</div><h3>{pid}</h3><p className="muted">{msg}.<br/>Ask the patient for consent, use the share code from their login, or use the emergency override (logged and shown to the patient).</p>
    <div className="bar c"><button className="btn" onClick={()=>run(async()=>{await api(`/patients/${pid}/request`,{method:"POST"});alert("Consent request sent to the patient.")})}>Request patient consent</button>
      <button className="btn ghost" onClick={()=>{const r=prompt("Reason for emergency override (logged, visible to the patient):");if(r&&r.trim())run(()=>api(`/patients/${pid}/override`,{body:{reason:r}}))}}>Emergency override</button></div>
    <div className="bar c"><input placeholder="6-digit share code" value={code} onChange={e=>setCode(e.target.value)}/><button className="btn" onClick={()=>run(()=>api(`/patients/${pid}/code`,{body:{code}}))}>Open with code</button></div></div>
}

function Record({pid,me,back,start,ver=0,unread=0,onChange}){
  const [d,setD]=useState(null),[err,setErr]=useState(""),[sel,setSel]=useState(new Set()),[show,setShow]=useState({}),[busy,setBusy]=useState(false),[sum,setSum]=useState(null),[inc,setInc]=useState(false),[tab,setTab]=useState("All"),[view,setView]=useState(start||"docs"),[vit,setVit]=useState(false)
  const load=()=>{setErr("");api("/patients/"+pid).then(r=>{setD(r);setSel(new Set(r.documents.map(x=>x.id)))}).catch(e=>setErr(e.message))}
  useEffect(load,[pid])
  if(err)return me.role==="doctor"?<Locked pid={pid} back={back} reload={load} msg={err}/>:<p className="err">{err}</p>
  if(!d)return <p className="muted">Loading…</p>
  const {patient:p,documents:docs}=d,grp=GROUPS.find(g=>g[0]===tab),list=docs.filter(x=>!grp[1]||grp[1].includes(x.kind)),gal=tab==="X-ray & scans"
  const toggle=ids=>{const n=new Set(sel),all=ids.length&&ids.every(i=>n.has(i));ids.forEach(i=>all?n.delete(i):n.add(i));setSel(n)}
  const pdf=async()=>{setBusy(true);try{const r=await api(`/patients/${pid}/pdf`,{body:{ids:[...sel],summary:inc,vitals:vit},raw:true}),b=await r.blob();if(r.headers.get("X-Skipped")>0)alert(r.headers.get("X-Skipped")+" attached file(s) could not be merged and were left out of the PDF.");const a=document.createElement("a");a.href=URL.createObjectURL(b);a.download=`${pid}_records.pdf`;a.click()}catch(e){alert(e.message)}setBusy(false)}
  return <div className="stack">{back&&<button className="ghost left" onClick={back}>← Back to patients</button>}
    <div className="panel"><h3>{p.name} <span className="muted small">{p.id} · {p.city}, {p.state}</span></h3>
      <div className="facts">{[["ABHA",p.abha],["Born",p.dob],["Sex",p.sex],["Blood group",p.blood],["Allergies",p.allergies],["Documents",docs.length]].map(([k,v])=><div key={k}><small>{k}</small><b>{v}</b></div>)}</div></div>
    <div className="chips tabs2">{[["docs","Documents"],["dash","Dashboard"],["msgs","Messages"+(unread?` (${unread})`:"")]].map(([k,n])=><button key={k} className={view===k?"on":""} onClick={()=>setView(k)}>{n}</button>)}</div>
    {view==="dash"&&<Dashboard pid={pid} me={me} ver={ver}/>}{view==="msgs"&&<Messages pid={pid} me={me} onChange={onChange}/>}
    {view==="docs"&&<><div className="panel"><h3>Create a PDF</h3><p className="muted small">Choose what to include: pick a whole category, several categories, or individual documents below.</p>
      <div className="chips">{KINDS.map(k=>{const ids=docs.filter(x=>x.kind===k).map(x=>x.id);return ids.length?<button key={k} className={ids.every(i=>sel.has(i))?"on":""} onClick={()=>toggle(ids)}>{k} ({ids.length})</button>:null})}
        <button onClick={()=>setSel(new Set(docs.map(x=>x.id)))}>Select all</button><button onClick={()=>setSel(new Set())}>Clear</button></div>
      <label className="chk"><input type="checkbox" checked={inc} onChange={e=>setInc(e.target.checked)}/> Include the record summary in the PDF</label><label className="chk"><input type="checkbox" checked={vit} onChange={e=>setVit(e.target.checked)}/> Include the home-monitoring summary (BP and sugar averages)</label><button className="btn" disabled={!sel.size||busy} onClick={pdf}>{busy?"Creating PDF…":`Download PDF (${sel.size} document${sel.size===1?"":"s"})`}</button></div>
    <div className="panel"><h3>Record summary</h3><p className="muted small">Conditions, medicines, surgeries and recent reports at a glance.</p><button className="btn ghost" onClick={async()=>{try{setSum(await api(`/patients/${pid}/summary`,{method:"POST"}))}catch(e){alert(e.message)}}}>Generate summary</button>{sum&&<><pre>{sum.summary}</pre><small className="muted">{sum.source==="AI"?"Written by AI from the record.":"Built automatically from the record."} Always check against the documents.</small></>}</div>
    <AddDoc pid={pid} me={me} done={load}/>
    <div className="panel"><h3>Documents · birth to today</h3>
      <div className="chips">{GROUPS.map(([n,ks])=><button key={n} className={tab===n?"on":""} onClick={()=>setTab(n)}>{n} ({docs.filter(x=>!ks||ks.includes(x.kind)).length})</button>)}</div>
      {gal?<div className="gallery">{list.map(x=><div className="card" key={x.id}><div className="thumb" onClick={()=>x.has_file&&openFile(x.id)}>{x.mime&&x.mime.startsWith("image")?<Thumb id={x.id}/>:<div className="ph">{x.has_file?"PDF":"No file"}</div>}</div>
        <label className="chk"><input type="checkbox" checked={sel.has(x.id)} onChange={()=>toggle([x.id])}/> {x.title}</label><small className="muted">{x.kind} · {x.date}{x.doctor?` · ${x.doctor}`:""}</small></div>)}</div>
      :list.map(x=><div className="doc" key={x.id}><input type="checkbox" checked={sel.has(x.id)} onChange={()=>toggle([x.id])}/><div><span className={"tag k-"+x.kind}>{x.kind.toUpperCase()}</span> <small className="muted">{x.date}{x.doctor?` · ${x.doctor}`:""}</small>
        <b className="t">{x.title}</b>{x.has_file&&<button className="link" onClick={()=>openFile(x.id)}>📎 Open {x.fname||"file"}</button>}
        {x.body&&<> <button className="link" onClick={()=>setShow({...show,[x.id]:!show[x.id]})}>{show[x.id]?"Hide notes":"Notes"}</button>{show[x.id]&&<pre>{x.body}</pre>}</>}</div></div>)}
      {!list.length&&<p className="muted">Nothing in this section yet.</p>}</div></>}</div>
}

function Patient({me}){
  const [a,setA]=useState(null),[k,setK]=useState(0),bump=()=>{setK(x=>x+1);load()},load=()=>api("/me/access").then(setA).catch(()=>{}),post=p=>api(p,{method:"POST"}).then(load)
  useEffect(()=>{load()},[])
  return <div className="stack"><Today ver={k} onChange={bump}/><PatientAppts pid={me.id} docs={a?a.granted:[]}/>{a&&<div className="grid2">
    <div className="panel"><h3>Share with a doctor in another city</h3><p className="muted small">Generate a one-time code and give it to your doctor along with your ID ({me.id}).</p>
      <button className="btn" onClick={()=>post("/me/code")}>Generate share code</button>{a.code&&<span className="code">{a.code}</span>}</div>
    <div className="panel"><h3>Consent requests ({a.pending.length})</h3>{a.pending.map(c=><div className="row" key={c.id}><span>{c.doctor}<small>{c.speciality} · {c.city}</small></span><span><button className="btn sm" onClick={()=>post(`/me/consent/${c.id}/approve`)}>Approve</button> <button className="btn sm ghost" onClick={()=>post(`/me/consent/${c.id}/deny`)}>Deny</button></span></div>)}{!a.pending.length&&<p className="muted small">No pending requests.</p>}</div>
    <div className="panel"><h3>Doctors with access</h3>{a.granted.map(c=><div className="row" key={c.id}><span>{c.doctor}<small>{c.speciality} · {c.city}</small></span><button className="btn sm ghost" onClick={()=>post(`/me/consent/${c.id}/revoke`)}>Revoke</button></div>)}{!a.granted.length&&<p className="muted small">No doctor has access.</p>}</div>
    <div className="panel"><h3>Who viewed my record</h3>{a.log.map((l,i)=><div className="row" key={i}><span>{l.who}<small>{l.what} · {l.at}</small></span></div>)}{!a.log.length&&<p className="muted small">No access yet.</p>}</div></div>}
    <Record pid={me.id} me={me} ver={k} unread={a?a.unread:0} onChange={bump}/></div>
}

const GROUPS=[["All",null],["Prescriptions",["Prescription"]],["Lab reports",["Report"]],["X-ray & scans",["X-ray","Scan"]],["Surgery & discharge",["Surgery","Discharge"]],["History",["Birth","Vaccination","Illness"]],["Other",["Other"]]]
async function openFile(id){const w=window.open("","_blank");try{const b=await api(`/documents/${id}/file`,{blob:true});w.location=URL.createObjectURL(b)}catch(e){w.close();alert(e.message)}}
function Thumb({id}){const [u,setU]=useState("");useEffect(()=>{let url;api(`/documents/${id}/file`,{blob:true}).then(b=>{url=URL.createObjectURL(b);setU(url)}).catch(()=>{});return()=>url&&URL.revokeObjectURL(url)},[id]);return u?<img src={u} alt=""/>:<div className="ph">Loading…</div>}

function AddDoc({pid,me,done}){
  const kinds=me.role==="doctor"?KINDS.filter(k=>k!=="Birth"):["Report","X-ray","Scan","Prescription","Other"],blank={kind:kinds[0],title:"",date:new Date().toISOString().slice(0,10),body:""}
  const [f,setF]=useState(blank),[file,setFile]=useState(null),[n,setN]=useState(0),[busy,setBusy]=useState(false),set=k=>e=>setF({...f,[k]:e.target.value})
  const go=async e=>{e.preventDefault();if(!file&&!f.body.trim())return alert("Attach a file or write the details in the note.");if(file&&file.size>10*1024*1024)return alert("File is larger than 10 MB.")
    const fd=new FormData();Object.entries(f).forEach(([k,v])=>fd.append(k,v));if(file)fd.append("file",file);setBusy(true)
    try{await upload(`/patients/${pid}/documents`,fd);setF(blank);setFile(null);setN(n+1);done()}catch(x){alert(x.message)}setBusy(false)}
  return <form className="panel" onSubmit={go}><h3>Add to this record</h3><p className="muted small">Attach a file (PDF, JPG, PNG or WebP, up to 10 MB), or just write a note. You can do both.</p>
    <div className="bar"><select value={f.kind} onChange={set("kind")}>{kinds.map(k=><option key={k}>{k}</option>)}</select><input type="date" required value={f.date} onChange={set("date")}/><input required placeholder="Title (e.g. Chest X-ray, Follow-up note)" value={f.title} onChange={set("title")}/></div>
    <input key={n} type="file" accept=".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/*" onChange={e=>setFile(e.target.files[0]||null)}/>
    <textarea rows="3" placeholder="Note or details (required if there is no file)" value={f.body} onChange={set("body")}/><button className="btn" disabled={busy}>{busy?"Saving…":"Save"}</button></form>
}
