import {useState,useEffect} from "react"
import {api,API} from "./api.js"
const PFILES=[["birth_certificate","Birth certificate"],["photo_id","Government photo ID"],["apaar_card","APAAR ID card (copy or screenshot)"]]
const DFILES=[["degree_cert","Degree certificate (MBBS / MD / MS …)"],["reg_certificate","Medical council registration certificate"],["photo_id","Government photo ID (hide the Aadhaar number if you use it)"]]
const BLOOD=["A+","A-","B+","B-","AB+","AB-","O+","O-"]
const grid={display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(230px,1fr))",gap:"0 14px"}

export function Signup({back}){
  const [role,setRole]=useState("patient"),[v,setV]=useState({sex:"Male",blood:"O+"}),[files,setFiles]=useState({}),[pw2,setPw2]=useState(""),[err,setErr]=useState(""),[done,setDone]=useState(null),[busy,setBusy]=useState(false),[meta,setMeta]=useState({})
  useEffect(()=>{api("/meta").then(setMeta).catch(()=>{})},[])
  const set=k=>e=>setV({...v,[k]:e.target.value}),In=(k,l,o={})=><label key={k}>{l}<input required={o.opt?false:true} type={o.type||"text"} list={o.list} maxLength={o.max} value={v[k]||""} onChange={set(k)}/></label>
  const F=role==="patient"?PFILES:DFILES
  const switchRole=r=>{setRole(r);setFiles({});setErr("")}
  const go=async e=>{e.preventDefault();setErr("")
    const id=role==="patient"?v.apaar:v.aadhaar,digits=(id||"").replace(/[\s-]/g,"")
    if(!/^\d{12}$/.test(digits))return setErr(role==="patient"?"APAAR ID must be exactly 12 digits.":"Aadhaar number must be 12 digits.")
    if(v.password!==pw2)return setErr("Passwords do not match.")
    if(F.some(([k])=>!files[k]))return setErr("All documents are compulsory.")
    const fd=new FormData();Object.entries(v).forEach(([k,x])=>fd.append(k,x));F.forEach(([k])=>fd.append(k,files[k]));setBusy(true)
    try{const r=await fetch(`${API}/signup/${role}`,{method:"POST",body:fd});const j=await r.json().catch(()=>({}));if(!r.ok)throw new Error(typeof j.detail==="string"?j.detail:"Please check the values you entered");setDone(j)}catch(x){setErr(x.message)}setBusy(false)}
  if(done)return <div className="gate"><div className="box"><h2>Application received</h2><p>Your ID is <b>{done.id}</b>. Keep it safe.</p><p className="muted small">Your documents are now with the verification team. You can log in with this ID and your password once they approve your application.</p><button className="btn wide" onClick={back}>Back to login</button></div></div>
  return <div className="gate" style={{alignItems:"start"}}><form className="box" style={{maxWidth:780}} onSubmit={go}><h2>Create an account</h2><p className="muted small">Every account is verified by our team before it can be used.</p>
    <div className="tabs">{["patient","doctor"].map(r=><button type="button" key={r} className={role===r?"on":""} onClick={()=>switchRole(r)}>{r==="patient"?"I am a patient":"I am a doctor"}</button>)}</div>
    <datalist id="st">{Object.keys(meta).map(x=><option key={x}>{x}</option>)}</datalist><datalist id="ct">{Object.values(meta).flat().map(x=><option key={x}>{x}</option>)}</datalist>
    <div style={grid}>{In("name","Full name")}
      {role==="patient"?<>{In("dob","Date of birth",{type:"date"})}{In("apaar","APAAR ID (12 digits)",{max:14})}<label>Sex<select value={v.sex} onChange={set("sex")}><option>Male</option><option>Female</option><option>Other</option></select></label><label>Blood group<select value={v.blood} onChange={set("blood")}>{BLOOD.map(b=><option key={b}>{b}</option>)}</select></label>{In("allergies","Allergies (optional)",{opt:true})}</>
      :<>{In("speciality","Speciality (e.g. Cardiology)")}{In("degree","Highest degree (e.g. MBBS, MD)")}{In("council","Medical council (e.g. NMC, Rajasthan Medical Council)")}{In("reg_no","Medical registration number")}{In("hospital","Hospital or clinic")}{In("aadhaar","Aadhaar number (12 digits)",{max:14})}</>}
      {In("state","State",{list:"st"})}{In("city","City",{list:"ct"})}
      <label>Password<input required type="password" minLength={8} value={v.password||""} onChange={set("password")}/></label><label>Confirm password<input required type="password" value={pw2} onChange={e=>setPw2(e.target.value)}/></label></div>
    <h3 style={{marginTop:8}}>Compulsory documents</h3><p className="muted small">PDF, JPG, PNG or WebP, up to 5 MB each.{role==="doctor"&&" Your Aadhaar number is checked for format and only its last 4 digits are kept."}</p>
    <div style={grid}>{F.map(([k,l])=><label key={k}>{l}<input required type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" onChange={e=>setFiles({...files,[k]:e.target.files[0]})}/></label>)}</div>
    <p className="err">{err}</p><button className="btn" disabled={busy}>{busy?"Submitting…":"Submit for verification"}</button> <button type="button" className="ghost" onClick={back}>Back to login</button></form></div>
}

async function openKyc(id){const w=window.open("","_blank");try{const b=await api(`/admin/kyc/${id}`,{blob:true});w.location=URL.createObjectURL(b)}catch(e){w.close();alert(e.message)}}
export function Admin(){
  const [a,setA]=useState(null),load=()=>api("/admin/pending").then(setA).catch(e=>alert(e.message));useEffect(()=>{load()},[])
  const review=async(x,act)=>{let note="";if(act==="reject"){note=prompt("Reason for rejecting (the applicant will see it):");if(!note||!note.trim())return}try{await api(`/admin/review/${x.role}/${x.id}/${act}`,{body:{note}});load()}catch(e){alert(e.message)}}
  return <div className="panel"><h3>Verification queue {a&&`(${a.length})`}</h3><p className="muted small">Open every document and check it against the details before approving.</p>
    {a&&a.map(x=><div className="row" key={x.role+x.id} style={{alignItems:"flex-start"}}><span><b>{x.name}</b> <span className="tag">{x.role.toUpperCase()}</span> <span className="muted small">{x.id}</span><small>{x.info}</small>{x.docs.map(d=><button key={d.id} className="link" style={{marginRight:12}} onClick={()=>openKyc(d.id)}>📎 {d.label}</button>)}</span>
      <span><button className="btn sm" onClick={()=>review(x,"approve")}>Approve</button> <button className="btn sm ghost" onClick={()=>review(x,"reject")}>Reject</button></span></div>)}
    {a&&!a.length&&<p className="muted">No applications waiting.</p>}</div>
}
