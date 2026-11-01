import {useState,useEffect} from "react"
import {api} from "./api.js"
const fmt=s=>new Date(s.replace(" ","T")).toLocaleString("en-IN",{weekday:"short",day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"})
const cls=s=>"tag "+(s==="scheduled"?"ok":s==="cancelled"?"lock":"")
const useList=path=>{const [a,setA]=useState(null),load=()=>api(path).then(setA).catch(()=>{});useEffect(()=>{load()},[]);return[a,load]}
const act=async(id,what,note,load)=>{try{await api(`/appointments/${id}/${what}`,{body:{note:note||""}});load()}catch(e){alert(e.message)}}

export function DoctorAppts({open}){
  const [a,load]=useList("/appointments"),blank={pid:"",at:"",reason:""},[f,setF]=useState(blank),set=k=>e=>setF({...f,[k]:e.target.value})
  const add=async e=>{e.preventDefault();try{await api(`/patients/${f.pid.trim().toUpperCase()}/appointments`,{body:{at:f.at,reason:f.reason}});setF(blank);load()}catch(x){alert(x.message)}}
  const Row=x=><div className="row" key={x.id}><span><b>{fmt(x.at)}</b> · <b>{x.name}</b> <span className="muted small">{x.pid}</span><small>{x.reason||"No reason given"}{x.by==="patient"?" · requested by the patient":""}</small></span>
    <span>{x.status==="requested"&&<button className="btn sm" onClick={()=>act(x.id,"confirm","",load)}>Confirm</button>} {x.status==="scheduled"&&<button className="btn sm" onClick={()=>act(x.id,"complete","",load)}>Done</button>} <button className="btn sm ghost" onClick={()=>open(x.pid,"docs")}>Record</button> <button className="btn sm ghost" onClick={()=>{const n=prompt(x.status==="requested"?"Reason for declining (the patient will see it):":"Reason for cancelling (the patient will see it):");if(n!==null)act(x.id,"cancel",n,load)}}>{x.status==="requested"?"Decline":"Cancel"}</button></span></div>
  return <div className="panel"><h3>Appointments</h3>{a&&<>
    <b className="small">Today ({a.today.length})</b>{a.today.map(Row)}{!a.today.length&&<p className="muted small">No appointments today.</p>}
    {a.requests.length>0&&<><b className="small">Requests from patients ({a.requests.length})</b>{a.requests.map(Row)}</>}
    <b className="small">Upcoming, next 30 days ({a.upcoming.length})</b>{a.upcoming.map(Row)}{!a.upcoming.length&&<p className="muted small">Nothing scheduled.</p>}</>}
    <form className="bar" onSubmit={add}><input style={{maxWidth:130,minWidth:110}} required placeholder="Patient ID" value={f.pid} onChange={set("pid")}/><input type="datetime-local" required value={f.at} onChange={set("at")}/><input placeholder="Reason (optional)" value={f.reason} onChange={set("reason")}/><button className="btn sm">Schedule</button></form></div>
}

export function PatientAppts({pid,docs=[]}){
  const [a,load]=useList("/me/appointments"),blank={did:"",at:"",reason:""},[f,setF]=useState(blank),set=k=>e=>setF({...f,[k]:e.target.value})
  const list=[...new Map(docs.map(d=>[d.did,d])).values()]
  const add=async e=>{e.preventDefault();try{await api(`/patients/${pid}/appointments`,{body:f});setF(blank);load()}catch(x){alert(x.message)}}
  return <div className="panel"><h3>My appointments</h3>{a&&<>
    {a.upcoming.map(x=><div className="row" key={x.id}><span><b>{fmt(x.at)}</b> · {x.doctor}<small>{x.reason||"No reason given"}</small></span><span><span className={cls(x.status)}>{x.status==="requested"?"WAITING FOR DOCTOR":x.status.toUpperCase()}</span> <button className="btn sm ghost" onClick={()=>{const n=prompt("Reason for cancelling (optional):");if(n!==null)act(x.id,"cancel",n,load)}}>Cancel</button></span></div>)}
    {!a.upcoming.length&&<p className="muted small">No upcoming appointments.</p>}
    {a.earlier.length>0&&<details><summary className="small muted">Earlier and cancelled</summary>{a.earlier.map(x=><div className="row" key={x.id}><span>{fmt(x.at)} · {x.doctor}<small>{x.reason}{x.note?` · ${x.note}`:""}</small></span><span className={cls(x.status)}>{x.status.toUpperCase()}</span></div>)}</details>}</>}
    <form className="bar" onSubmit={add}><select required value={f.did} onChange={set("did")}><option value="">Choose a doctor…</option>{list.map(d=><option key={d.did} value={d.did}>{d.doctor} · {d.speciality}</option>)}</select><input type="datetime-local" required value={f.at} onChange={set("at")}/><input placeholder="Reason (optional)" value={f.reason} onChange={set("reason")}/><button className="btn sm">Request</button></form>
    {!list.length&&<p className="muted small">You can request an appointment with doctors who have access to your record.</p>}</div>
}
