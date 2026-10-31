export const API=import.meta.env.VITE_API||"http://localhost:8000"
let TOKEN=""
export const setToken=t=>{TOKEN=t}
const fail=async r=>{const e=await r.json().catch(()=>({}));throw new Error(typeof e.detail==="string"?e.detail:r.status===422?"Please check the values you entered":r.statusText)}
export async function api(path,{body,blob,raw,method}={}){
  const r=await fetch(API+path,{method:method||(body?"POST":"GET"),headers:{"Content-Type":"application/json",Authorization:"Bearer "+TOKEN},body:body&&JSON.stringify(body)})
  if(!r.ok)await fail(r)
  return raw?r:blob?r.blob():r.json()
}
export async function upload(path,fd){const r=await fetch(API+path,{method:"POST",headers:{Authorization:"Bearer "+TOKEN},body:fd});if(!r.ok)await fail(r)}
