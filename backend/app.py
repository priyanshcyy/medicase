import os,io,re,hmac,json,time,secrets,base64,hashlib,datetime as dt
from xml.sax.saxutils import escape
from fastapi import FastAPI,Depends,HTTPException,Header,UploadFile,File,Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import create_engine,Column,Integer,Float,String,Text,ForeignKey,LargeBinary,select,or_,func
from sqlalchemy.orm import declarative_base,sessionmaker,defer
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from PIL import Image as PI
from reportlab.platypus import Image as RLImage,SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether

URL=os.getenv("DATABASE_URL","sqlite:///./medicase.db")  # PostgreSQL: postgresql+psycopg2://user:pw@localhost/medicase
SECRET=os.getenv("SECRET","dev-secret-change-me").encode()
eng=create_engine(URL,connect_args={"check_same_thread":False} if URL.startswith("sqlite") else {})
SL=sessionmaker(eng);Base=declarative_base()
H=lambda s:hashlib.sha256(s.encode()).hexdigest()

class Doctor(Base):
    __tablename__="doctors";id=Column(String,primary_key=True);name=Column(String);speciality=Column(String);state=Column(String);city=Column(String);pw=Column(String)
class Patient(Base):
    __tablename__="patients";id=Column(String,primary_key=True);name=Column(String);dob=Column(String);sex=Column(String);blood=Column(String);allergies=Column(String);state=Column(String,index=True);city=Column(String,index=True);pw=Column(String);code=Column(String,default="");code_exp=Column(String,default="");abha=Column(String,index=True)
class Document(Base):
    __tablename__="documents";id=Column(Integer,primary_key=True);patient_id=Column(String,ForeignKey("patients.id"),index=True);doctor_id=Column(String,ForeignKey("doctors.id"));kind=Column(String);title=Column(String);date=Column(String);body=Column(Text);fname=Column(String);mime=Column(String);file=Column(LargeBinary)
class Consent(Base):
    __tablename__="consents";id=Column(Integer,primary_key=True);patient_id=Column(String,index=True);doctor_id=Column(String,index=True);status=Column(String);until=Column(String,default="")
class Log(Base):
    __tablename__="logs";id=Column(Integer,primary_key=True);patient_id=Column(String,index=True);who=Column(String);what=Column(String);at=Column(String)
class Measure(Base):
    __tablename__="measures";id=Column(Integer,primary_key=True);patient_id=Column(String,index=True);kind=Column(String,index=True);v1=Column(Float);v2=Column(Float);unit=Column(String,default="");at=Column(String,index=True);note=Column(String,default="");src=Column(String,default="patient")
class Reminder(Base):
    __tablename__="reminders";id=Column(Integer,primary_key=True);patient_id=Column(String,index=True);kind=Column(String);label=Column(String);times=Column(String,default="");per_day=Column(Integer,default=1);start=Column(String);until=Column(String,default="");by=Column(String);status=Column(String,default="proposed")
class Msg(Base):
    __tablename__="messages";id=Column(Integer,primary_key=True);patient_id=Column(String,index=True);doctor_id=Column(String,index=True);sender=Column(String);text=Column(Text);at=Column(String);kind=Column(String,default="chat");rid=Column(Integer);read=Column(Integer,default=0)
class Order(Base):
    __tablename__="orders";id=Column(Integer,primary_key=True);patient_id=Column(String,index=True);doctor_id=Column(String);name=Column(String);every_days=Column(Integer);start=Column(String)
class Limit(Base):
    __tablename__="limits";patient_id=Column(String,primary_key=True);data=Column(Text,default="{}")
class Appt(Base):
    __tablename__="appointments";id=Column(Integer,primary_key=True);patient_id=Column(String,index=True);doctor_id=Column(String,index=True);at=Column(String,index=True);reason=Column(String,default="");status=Column(String,default="scheduled");by=Column(String,default="doctor");note=Column(String,default="")
Base.metadata.create_all(eng)

def now(d=0):return (dt.datetime.now()+dt.timedelta(days=d)).strftime("%Y-%m-%d %H:%M")
def mint(r,u):
    b=base64.urlsafe_b64encode(json.dumps({"r":r,"u":u,"e":int(time.time())+12*3600}).encode()).decode()
    return b+"."+hmac.new(SECRET,b.encode(),"sha256").hexdigest()
def who(authorization:str=Header("")):
    try:
        b,sig=authorization.replace("Bearer ","").split(".")
        if not hmac.compare_digest(sig,hmac.new(SECRET,b.encode(),"sha256").hexdigest()):raise ValueError
        d=json.loads(base64.urlsafe_b64decode(b))
        if d.get("e",0)<time.time():raise ValueError
        return d
    except Exception:
        raise HTTPException(401,"Please log in again")
def db():
    s=SL()
    try:yield s
    finally:s.close()
def need(u,r):
    if u["r"]!=r:raise HTTPException(403,"Not allowed")
def granted(s,did):
    n=now()
    return {c.patient_id for c in s.scalars(select(Consent).where(Consent.doctor_id==did,Consent.status.in_(["granted","emergency"]))) if c.status=="granted" or c.until>n}
def allowed(s,u,pid):
    return u["u"]==pid if u["r"]=="patient" else pid in granted(s,u["u"])
def log(s,pid,w,what):s.add(Log(patient_id=pid,who=w,what=what,at=now()))
def label(s,u):
    o=s.get(Doctor if u["r"]=="doctor" else Patient,u["u"]);return f"{o.name} ({o.id})"
def pub(p):return {k:getattr(p,k) for k in("id","name","abha","dob","sex","blood","allergies","state","city")}
def docs_of(s,pid):
    dn={d.id:d.name for d in s.scalars(select(Doctor))}
    q=select(Document).options(defer(Document.file)).where(Document.patient_id==pid).order_by(Document.date.desc(),Document.id.desc())
    return [{"id":d.id,"kind":d.kind,"title":d.title,"date":d.date,"doctor":dn.get(d.doctor_id,"Patient upload"),"body":d.body,"has_file":d.mime is not None,"fname":d.fname,"mime":d.mime} for d in s.scalars(q)]
def patient_or_404(s,pid):
    p=s.get(Patient,pid)
    if not p:raise HTTPException(404,"Patient not found")
    return p

app=FastAPI(title="MediCase API")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_headers=["*"],allow_methods=["*"],expose_headers=["X-Skipped"])
class Login(BaseModel):role:str;id:str;password:str
class Code(BaseModel):code:str
class Reason(BaseModel):reason:str
class Sel(BaseModel):ids:list[int]=[];summary:bool=False;vitals:bool=False
class NewDoc(BaseModel):kind:str;title:str;date:str;body:str=""

@app.post("/login")
def login(b:Login,s=Depends(db)):
    if b.role not in("doctor","patient"):raise HTTPException(400,"Bad role")
    o=s.get(Doctor if b.role=="doctor" else Patient,b.id.strip().upper())
    if not o or o.pw!=H(b.password):raise HTTPException(401,"Wrong ID or password")
    return {"token":mint(b.role,o.id),"role":b.role,"id":o.id,"name":o.name,"state":o.state,"city":o.city}

@app.get("/meta")
def meta(s=Depends(db)):
    m={}
    for st,c in s.execute(select(Patient.state,Patient.city).distinct()):m.setdefault(st,[]).append(c)
    return {k:sorted(v) for k,v in sorted(m.items())}

@app.get("/patients")
def plist(q:str="",state:str="",city:str="",u=Depends(who),s=Depends(db)):
    need(u,"doctor")
    st=select(Patient).order_by(Patient.name).limit(60)
    if q:st=st.where(or_(Patient.name.ilike(f"%{q}%"),Patient.id.ilike(f"%{q}%"),Patient.abha.ilike(f"%{q}%")))
    if state:st=st.where(Patient.state==state)
    if city:st=st.where(Patient.city==city)
    ok=granted(s,u["u"])
    return [{**pub(p),"access":p.id in ok} for p in s.scalars(st)]

@app.get("/patients/{pid}")
def record(pid:str,u=Depends(who),s=Depends(db)):
    p=patient_or_404(s,pid)
    if not allowed(s,u,pid):raise HTTPException(403,"Patient consent required to open this record")
    if u["r"]=="doctor":
        log(s,pid,label(s,u),"Viewed full record");s.commit()
    return {"patient":pub(p),"documents":docs_of(s,pid)}

@app.post("/patients/{pid}/pdf")
def pdf(pid:str,b:Sel,u=Depends(who),s=Depends(db)):
    p=patient_or_404(s,pid)
    if not allowed(s,u,pid):raise HTTPException(403,"Patient consent required")
    docs=[d for d in reversed(docs_of(s,pid)) if not b.ids or d["id"] in b.ids]
    if not docs:raise HTTPException(400,"Select at least one document")
    st=getSampleStyleSheet();buf=io.BytesIO()
    info=Table([["Name",p.name,"Patient ID",p.id],["Date of birth",p.dob,"Sex / Blood",f"{p.sex} / {p.blood}"],["Location",f"{p.city}, {p.state}","Allergies",p.allergies],["ABHA number",p.abha,"",""]],colWidths=[75,150,75,150])
    info.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.4,colors.lightgrey),("FONTSIZE",(0,0),(-1,-1),9),("BACKGROUND",(0,0),(0,-1),colors.whitesmoke),("BACKGROUND",(2,0),(2,-1),colors.whitesmoke)]))
    el=[Paragraph("MediCase - Patient Record",st["Title"]),Paragraph(f"Generated {now()} by {escape(label(s,u))} | {len(docs)} document(s) | synthetic demo data",st["Italic"]),Spacer(1,10),info,Spacer(1,14)]
    if b.summary:
        el+=[Paragraph("Clinical summary",st["Heading3"]),Paragraph(escape(summarize(p,docs)[0]).replace("\n","<br/>"),st["BodyText"]),Spacer(1,10)]
    if b.vitals:
        d=dash(s,pid);bp,sg=d["stats"]["bp"],d["stats"]["sugar"]
        vt=[["Measure","Last 7 days","Last 30 days","In range (30d)"],
            ["Blood pressure (mmHg)","/".join(map(str,bp["avg7"])) if bp["avg7"] else "-","/".join(map(str,bp["avg30"])) if bp["avg30"] else "-",f"{bp['in_range']}%" if bp["in_range"] is not None else "-"],
            ["Blood sugar (mg/dL)",sg["avg7"] or "-",sg["avg30"] or "-",f"{sg['in_range']}%" if sg["in_range"] is not None else "-"],
            ["Flagged readings (7 days)",len(d["alerts"]),"",""]]
        t=Table(vt,colWidths=[150,100,100,100]);t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.4,colors.lightgrey),("FONTSIZE",(0,0),(-1,-1),9),("BACKGROUND",(0,0),(-1,0),colors.whitesmoke)]))
        el+=[Paragraph("Home monitoring summary",st["Heading3"]),t,Spacer(1,6),Paragraph("Patient-recorded values; not a diagnosis.",st["Italic"]),Spacer(1,10)]
    fl={x.id:(x.file,x.mime) for x in s.scalars(select(Document).where(Document.id.in_([d["id"] for d in docs])))}
    attach=[]
    for d in docs:
        f,m=fl.get(d["id"],(None,None))
        part=[Paragraph(f"<b>{escape(d['title'])}</b>",st["Heading3"]),Paragraph(f"{d['kind']} | {d['date']} | {escape(d['doctor'])}",st["Italic"]),Spacer(1,3)]
        if m and m.startswith("image"):
            w,h=PI.open(io.BytesIO(f)).size;k=min(320/w,320/h,1);part.append(RLImage(io.BytesIO(f),width=w*k,height=h*k))
        elif m:
            attach.append(f);part.append(Paragraph(f"Attached document: {escape(d['fname'] or 'file')} (included after this index).",st["BodyText"]))
        if d["body"] and (not m or m.startswith("image")):part.append(Paragraph(escape(d["body"]).replace("\n","<br/>"),st["BodyText"]))
        el.append(KeepTogether(part+[Spacer(1,8)]))
    SimpleDocTemplate(buf,pagesize=A4,title=f"{pid} records").build(el)
    out=buf.getvalue()
    skipped=0
    if attach:
        from pypdf import PdfReader,PdfWriter
        wr=PdfWriter()
        for pg in PdfReader(io.BytesIO(out)).pages:wr.add_page(pg)
        for src in attach:
            try:
                for pg in PdfReader(io.BytesIO(src)).pages:wr.add_page(pg)
            except Exception:
                skipped+=1
        o=io.BytesIO();wr.write(o);out=o.getvalue()
    log(s,pid,label(s,u),f"Exported PDF ({len(docs)} documents)");s.commit()
    return Response(out,media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="{pid}_records.pdf"',"X-Skipped":str(skipped)})

@app.post("/patients/{pid}/request")
def request_consent(pid:str,u=Depends(who),s=Depends(db)):
    need(u,"doctor");patient_or_404(s,pid)
    if not s.scalar(select(Consent).where(Consent.patient_id==pid,Consent.doctor_id==u["u"],Consent.status=="pending")):
        s.add(Consent(patient_id=pid,doctor_id=u["u"],status="pending"));log(s,pid,label(s,u),"Requested consent");s.commit()
    return {"ok":True}

TRIES={}
@app.post("/patients/{pid}/code")
def use_code(pid:str,b:Code,u=Depends(who),s=Depends(db)):
    need(u,"doctor");p=patient_or_404(s,pid)
    k=(u["u"],pid);ts=[t for t in TRIES.get(k,[]) if t>time.time()-900]
    if len(ts)>=5:raise HTTPException(429,"Too many wrong codes. Try again in 15 minutes.")
    if not p.code or not p.code_exp or p.code_exp<now() or not hmac.compare_digest(p.code,b.code.strip()):
        TRIES[k]=ts+[time.time()];raise HTTPException(400,"Invalid, expired or already used code")
    if not s.scalar(select(Consent).where(Consent.patient_id==pid,Consent.doctor_id==u["u"],Consent.status=="granted")):
        s.add(Consent(patient_id=pid,doctor_id=u["u"],status="granted"))
    p.code="";log(s,pid,label(s,u),"Opened with patient share code");s.commit()
    return {"ok":True}

@app.post("/patients/{pid}/override")
def override(pid:str,b:Reason,u=Depends(who),s=Depends(db)):
    need(u,"doctor");patient_or_404(s,pid)
    if not b.reason.strip():raise HTTPException(400,"A reason is required")
    s.add(Consent(patient_id=pid,doctor_id=u["u"],status="emergency",until=now(1)));log(s,pid,label(s,u),"EMERGENCY OVERRIDE (24h): "+b.reason.strip());s.commit()
    return {"ok":True}

@app.get("/me/access")
def my_access(u=Depends(who),s=Depends(db)):
    need(u,"patient");p=s.get(Patient,u["u"])
    dn={d.id:d for d in s.scalars(select(Doctor))}
    cs=s.scalars(select(Consent).where(Consent.patient_id==p.id,Consent.status.in_(["pending","granted"]))).all()
    f=lambda c:{"id":c.id,"did":c.doctor_id,"doctor":dn[c.doctor_id].name,"city":dn[c.doctor_id].city,"speciality":dn[c.doctor_id].speciality}
    lg=s.scalars(select(Log).where(Log.patient_id==p.id).order_by(Log.id.desc()).limit(15))
    return {"code":p.code if p.code_exp>=now() else "","unread":s.scalar(select(func.count(Msg.id)).where(Msg.patient_id==p.id,Msg.sender=="doctor",Msg.read==0)),"pending":[f(c) for c in cs if c.status=="pending"],"granted":[f(c) for c in cs if c.status=="granted"],"log":[{"who":l.who,"what":l.what,"at":l.at} for l in lg]}

@app.post("/me/code")
def new_code(u=Depends(who),s=Depends(db)):
    need(u,"patient")
    p=s.get(Patient,u["u"]);p.code=str(100000+secrets.randbelow(900000));p.code_exp=(dt.datetime.now()+dt.timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M");s.commit();return {"code":p.code,"expires":p.code_exp}

@app.post("/me/consent/{cid}/{act}")
def consent_act(cid:int,act:str,u=Depends(who),s=Depends(db)):
    need(u,"patient");c=s.get(Consent,cid)
    if not c or c.patient_id!=u["u"] or act not in("approve","deny","revoke"):raise HTTPException(404,"Not found")
    if act=="approve":
        dup=s.scalar(select(Consent).where(Consent.patient_id==c.patient_id,Consent.doctor_id==c.doctor_id,Consent.status=="granted"))
        if dup:s.delete(c)
        else:c.status="granted"
    else:s.delete(c)
    s.commit();return {"ok":True}

KINDS=["Birth","Vaccination","Illness","Surgery","Prescription","Report","Discharge","X-ray","Scan","Other"]

def summarize(p,docs):
    """AI summary if ANTHROPIC_API_KEY is set (name and ID are never sent); otherwise an automatic summary built from the record."""
    docs=sorted(docs,key=lambda d:d["date"]);age=(dt.date.today()-dt.date.fromisoformat(p.dob)).days//365
    g=lambda k:[d for d in docs if d["kind"]==k]
    key=os.getenv("ANTHROPIC_API_KEY")
    if key:
        try:
            import httpx
            ctx="\n".join(f"[{d['date']}] {d['kind']}: {d['title']} - {d['body']}" for d in docs[-60:])
            prompt=f"Write a concise clinical summary (under 150 words, plain text, short lines) for a doctor reviewing this patient. Use only the facts given; do not diagnose or invent anything.\nPatient: {age}y {p.sex}, blood {p.blood}, allergies {p.allergies}.\nRecords:\n{ctx}"
            r=httpx.post("https://api.anthropic.com/v1/messages",headers={"x-api-key":key,"anthropic-version":"2023-06-01"},json={"model":os.getenv("AI_MODEL","claude-sonnet-5-5"),"max_tokens":600,"messages":[{"role":"user","content":prompt}]},timeout=40)
            r.raise_for_status();return r.json()["content"][0]["text"],"AI"
        except Exception:
            pass
    meds={d["title"].replace("Prescription: ",""):d["date"] for d in g("Prescription")}
    L=lambda xs:"; ".join(xs) or "none recorded"
    return "\n".join([f"{age}-year-old {p.sex.lower()}, blood group {p.blood}. Allergies: {p.allergies}.",
      "Conditions: "+L(sorted({d["title"] for d in g("Illness")})),
      "Medicines prescribed: "+L([f"{m} (last {dd})" for m,dd in meds.items()]),
      "Surgeries: "+L([f"{d['title']} ({d['date']})" for d in g("Surgery")]),
      "Recent reports: "+L([f"{d['title']} ({d['date']})" for d in g("Report")[-3:]])]),"auto"

def sniff(b):
    if b[:4]==b"%PDF":return "application/pdf"
    if b[:3]==b"\xff\xd8\xff":return "image/jpeg"
    if b[:8]==b"\x89PNG\r\n\x1a\n":return "image/png"
    if b[:4]==b"RIFF" and b[8:12]==b"WEBP":return "image/webp"
    return None

@app.post("/patients/{pid}/documents")
def add_doc(pid:str,kind:str=Form(...),title:str=Form(...),date:str=Form(...),body:str=Form(""),file:UploadFile|None=File(None),u=Depends(who),s=Depends(db)):
    patient_or_404(s,pid)
    if not allowed(s,u,pid):raise HTTPException(403,"Patient consent required")
    if kind not in ([k for k in KINDS if k!="Birth"] if u["r"]=="doctor" else ["Report","X-ray","Scan","Prescription","Other"]):raise HTTPException(400,"This type is not allowed for you")
    try:dt.date.fromisoformat(date)
    except ValueError:raise HTTPException(400,"Enter a valid date")
    if not title.strip():raise HTTPException(400,"Title is required")
    data=mime=fn=None
    if file and file.filename:
        data=file.file.read(10*1024*1024+1)
        if len(data)>10*1024*1024:raise HTTPException(400,"File is larger than 10 MB")
        mime=sniff(data)
        if not mime:raise HTTPException(400,"Upload a PDF, JPG, PNG or WebP file")
        fn=re.sub(r"[^\w.\- ]","_",file.filename)[:80]
    elif not body.strip():raise HTTPException(400,"Attach a file or write the details in the note")
    s.add(Document(patient_id=pid,doctor_id=u["u"] if u["r"]=="doctor" else None,kind=kind,title=title.strip(),date=date,body=body.strip()[:5000],file=data,mime=mime,fname=fn))
    log(s,pid,label(s,u),f"{'Uploaded' if data else 'Added note'} {kind}: {title.strip()}");s.commit();return {"ok":True}

@app.get("/documents/{did}/file")
def get_file(did:int,u=Depends(who),s=Depends(db)):
    d=s.get(Document,did)
    if not d or not d.file:raise HTTPException(404,"No file attached")
    if not allowed(s,u,d.patient_id):raise HTTPException(403,"Patient consent required")
    return Response(d.file,media_type=d.mime,headers={"Content-Disposition":f'inline; filename="{d.fname or "file"}"'})

@app.post("/patients/{pid}/summary")
def summary(pid:str,u=Depends(who),s=Depends(db)):
    p=patient_or_404(s,pid)
    if not allowed(s,u,pid):raise HTTPException(403,"Patient consent required")
    txt,src=summarize(p,docs_of(s,pid));log(s,pid,label(s,u),"Generated record summary");s.commit()
    return {"summary":txt,"source":src}


# ======================= v6: home monitoring, reminders, messages, dashboard =======================
KL={"bp":"Blood pressure","sugar":"Blood sugar","weight":"Weight","pulse":"Pulse","spo2":"Oxygen saturation","temp":"Temperature","dose":"Medicine"}
UNIT={"bp":"mmHg","sugar":"mg/dL","weight":"kg","pulse":"bpm","spo2":"%","temp":"C","dose":""}
SPAN={"bp":(60,260),"sugar":(20,700),"weight":(2,300),"pulse":(25,220),"spo2":(50,100),"temp":(30,45),"dose":(1,1)}
VITALS=("bp","sugar","pulse","spo2","temp")
LIMD={"sys_hi":140,"sys_lo":90,"dia_hi":90,"dia_lo":60,"sugar_hi":180,"sugar_lo":70}  # alert AT/ABOVE *_hi and BELOW *_lo. Doctor can change per patient.
TM=re.compile(r"([01]\d|2[0-3]):[0-5]\d")

def flag(m,lim):
    """Returns (level, reason). level: None | low | high | urgent. Urgent cut-offs are fixed; the rest use the doctor's limits."""
    k,a,b=m.kind,m.v1,m.v2
    if k=="bp":
        if a>=180 or b>=120:return "urgent","Very high blood pressure"
        if a>=lim["sys_hi"] or b>=lim["dia_hi"]:return "high","High blood pressure"
        if a<lim["sys_lo"] or b<lim["dia_lo"]:return "low","Low blood pressure"
    elif k=="sugar":
        if a<54:return "urgent","Very low blood sugar"
        if a>=300:return "urgent","Very high blood sugar"
        if a>=lim["sugar_hi"]:return "high","High blood sugar"
        if a<lim["sugar_lo"]:return "low","Low blood sugar"
    elif k=="pulse":
        if a>130 or a<40:return "urgent","Pulse far outside the usual range"
        if a>110:return "high","Fast pulse"
        if a<50:return "low","Slow pulse"
    elif k=="spo2":
        if a<90:return "urgent","Very low oxygen saturation"
        if a<94:return "low","Low oxygen saturation"
    elif k=="temp":
        if a>=39.5:return "urgent","Very high temperature"
        if a>=38:return "high","Fever"
    elif k.startswith("lab:") and m.note and "-" in m.note:
        try:
            lo,hi=[float(x) for x in m.note.split("-",1)]
            if a>hi:return "high","Above reference range"
            if a<lo:return "low","Below reference range"
        except ValueError:pass
    return None,""

def lim_of(s,pid):
    r=s.get(Limit,pid);d=dict(LIMD)
    if r:d.update(json.loads(r.data or "{}"))
    return d
def mrow(m,lim):
    f,t=flag(m,lim);return {"id":m.id,"kind":m.kind,"at":m.at,"v1":m.v1,"v2":m.v2,"unit":m.unit,"note":m.note,"src":m.src,"flag":f,"why":t}
def avg(xs):return round(sum(xs)/len(xs),1) if xs else None
def times_of(r):return [t for t in (r.times or "").split(",") if t]
def clean_times(ts):
    ts=sorted({t.strip() for t in ts})
    if not 1<=len(ts)<=6 or not all(TM.fullmatch(t) for t in ts):raise HTTPException(400,"Give 1 to 6 times in HH:MM format")
    return ts

def adherence(s,r):
    """Share of expected readings actually recorded in the last 7 days (or since the reminder started)."""
    today=dt.date.today();ts=times_of(r)
    if r.status!="active" or not ts:return None
    start=max(today-dt.timedelta(days=6),dt.date.fromisoformat(r.start));end=min(today,dt.date.fromisoformat(r.until)) if r.until else today
    if end<start:return None
    q=select(Measure).where(Measure.patient_id==r.patient_id,Measure.kind==r.kind,Measure.at>=start.isoformat(),Measure.at<end.isoformat()+"~")
    if r.kind=="dose":q=q.where(Measure.note==r.label)
    per={}
    for m in s.scalars(q):per[m.at[:10]]=per.get(m.at[:10],0)+1
    n=len(ts);days=(end-start).days+1;hm=dt.datetime.now().strftime("%H:%M")
    exp=n*(days-1)+(sum(1 for t in ts if t<=hm) if end==today else n)
    got=sum(min(c,n) for c in per.values())
    return {"pct":min(100,round(100*got/exp)) if exp else None,"taken":got,"expected":exp}

def dash(s,pid):
    lim=lim_of(s,pid);today=dt.date.today();c30=(today-dt.timedelta(days=29)).isoformat();c7=(today-dt.timedelta(days=6)).isoformat()
    ms=s.scalars(select(Measure).where(Measure.patient_id==pid).order_by(Measure.at,Measure.id)).all()
    rows=[mrow(m,lim) for m in ms]
    series={k:[r for r in rows if r["kind"]==k and r["at"][:10]>=c30] for k in VITALS+("weight",)}
    def st(k):
        xs=series[k];x7=[r for r in xs if r["at"][:10]>=c7]
        if k=="bp":f=lambda L:[avg([r["v1"] for r in L]),avg([r["v2"] for r in L])] if L else None
        else:f=lambda L:avg([r["v1"] for r in L])
        return {"n30":len(xs),"avg7":f(x7),"avg30":f(xs),"in_range":round(100*sum(1 for r in xs if not r["flag"])/len(xs)) if xs else None,"latest":xs[-1] if xs else None}
    stats={k:st(k) for k in series}
    labs={}
    for r in rows:
        if r["kind"].startswith("lab:"):labs.setdefault(r["kind"][4:],[]).append(r)
    lab=[{"name":n,"unit":v[-1]["unit"],"ref":v[-1]["note"],"last":v[-1],"prev":v[-2] if len(v)>1 else None,"points":v[-12:]} for n,v in sorted(labs.items())]
    alerts=[r for r in reversed(rows) if r["flag"] and r["at"][:10]>=c7 and r["kind"] in VITALS][:15]
    rem=[]
    for r in s.scalars(select(Reminder).where(Reminder.patient_id==pid,Reminder.status.in_(["proposed","active"])).order_by(Reminder.id.desc())):
        ended=bool(r.until) and r.until<today.isoformat()
        rem.append({"id":r.id,"kind":r.kind,"label":r.label,"times":times_of(r),"per_day":r.per_day,"until":r.until,"status":"ended" if ended else r.status,"adh":None if ended else adherence(s,r)})
    docs=s.scalars(select(Document).options(defer(Document.file)).where(Document.patient_id==pid,Document.kind=="Report")).all()
    orders=[]
    for o in s.scalars(select(Order).where(Order.patient_id==pid).order_by(Order.id)):
        nm=o.name.lower()
        done=[d.date for d in docs if nm in d.title.lower()]+[m.at[:10] for m in ms if m.kind.lower()=="lab:"+nm]
        last=max(done) if done else None;due=dt.date.fromisoformat(last or o.start)+dt.timedelta(days=o.every_days);left=(due-today).days
        orders.append({"id":o.id,"name":o.name,"every_days":o.every_days,"last":last,"due":due.isoformat(),"status":"overdue" if left<0 else "due soon" if left<=3 else "ok","days_left":left})
    return {"limits":lim,"stats":stats,"series":series,"labs":lab,"alerts":alerts,"reminders":rem,"orders":orders}

def doctors_with_access(s,pid):
    n=now();ids={c.doctor_id for c in s.scalars(select(Consent).where(Consent.patient_id==pid,Consent.status.in_(["granted","emergency"]))) if c.status=="granted" or c.until>n}
    return [{"id":d.id,"name":d.name} for d in s.scalars(select(Doctor).where(Doctor.id.in_(ids)))] if ids else []

class Meas(BaseModel):kind:str;v1:float;v2:float|None=None;note:str="";at:str=""
class Req(BaseModel):kind:str;per_day:int=3;days:int=7;label:str="";text:str=""
class MsgIn(BaseModel):text:str;to:str=""
class RemIn(BaseModel):kind:str;label:str="";times:list[str]
class RemUp(BaseModel):status:str;times:list[str]=[]
class LimIn(BaseModel):data:dict
class OrdIn(BaseModel):name:str;every_days:int
class LabIn(BaseModel):name:str;value:float;unit:str="";ref_lo:float|None=None;ref_hi:float|None=None;date:str

ADVICE="If you feel unwell (chest pain, severe headache, confusion, breathlessness, fainting), get medical help now."
@app.post("/me/measures")
def add_measure(b:Meas,u=Depends(who),s=Depends(db)):
    need(u,"patient")
    if b.kind not in KL:raise HTTPException(400,"Unknown measurement type")
    lo,hi=SPAN[b.kind]
    if b.kind=="bp":
        if b.v2 is None or not(60<=b.v1<=260 and 30<=b.v2<=160) or b.v2>=b.v1:raise HTTPException(400,"Enter top (systolic) and bottom (diastolic) numbers, e.g. 120 and 80")
    elif not lo<=b.v1<=hi:raise HTTPException(400,f"{KL[b.kind]} must be between {lo} and {hi}")
    if b.kind=="dose" and not b.note.strip():raise HTTPException(400,"Medicine name is required")
    at=now()
    if b.at:
        try:
            x=dt.datetime.strptime(b.at,"%Y-%m-%d %H:%M")
            if x>dt.datetime.now()+dt.timedelta(minutes=5):raise HTTPException(400,"Time cannot be in the future")
            at=b.at
        except ValueError:raise HTTPException(400,"Use the format YYYY-MM-DD HH:MM")
    m=Measure(patient_id=u["u"],kind=b.kind,v1=b.v1,v2=b.v2 if b.kind=="bp" else None,unit=UNIT[b.kind],at=at,note=b.note.strip()[:60],src="patient");s.add(m)
    log(s,u["u"],label(s,u),f"Recorded {KL[b.kind]}");s.commit()
    f,t=flag(m,lim_of(s,u["u"]))
    return {"ok":True,"flag":f,"why":t,"advice":(ADVICE if f=="urgent" else "Your doctor can see this reading.") if f else ""}

@app.get("/me/today")
def today_(u=Depends(who),s=Depends(db)):
    need(u,"patient");td=dt.date.today().isoformat();out=[]
    for r in s.scalars(select(Reminder).where(Reminder.patient_id==u["u"],Reminder.status=="active").order_by(Reminder.id)):
        if r.until and r.until<td:continue
        q=select(func.count(Measure.id)).where(Measure.patient_id==u["u"],Measure.kind==r.kind,Measure.at.like(td+"%"))
        if r.kind=="dose":q=q.where(Measure.note==r.label)
        out.append({"id":r.id,"kind":r.kind,"label":r.label,"times":times_of(r),"done":s.scalar(q),"until":r.until,"by":r.by})
    return out

@app.get("/me/reminders")
def my_reminders(u=Depends(who),s=Depends(db)):
    need(u,"patient")
    return [{"id":r.id,"kind":r.kind,"label":r.label,"times":times_of(r),"per_day":r.per_day,"status":r.status,"until":r.until} for r in s.scalars(select(Reminder).where(Reminder.patient_id==u["u"],Reminder.status.in_(["proposed","active"])))]

@app.post("/me/reminders")
def new_reminder(b:RemIn,u=Depends(who),s=Depends(db)):
    need(u,"patient")
    if b.kind not in KL:raise HTTPException(400,"Unknown type")
    if b.kind=="dose" and not b.label.strip():raise HTTPException(400,"Medicine name is required")
    ts=clean_times(b.times)
    s.add(Reminder(patient_id=u["u"],kind=b.kind,label=b.label.strip()[:60] if b.kind=="dose" else KL[b.kind],times=",".join(ts),per_day=len(ts),start=dt.date.today().isoformat(),by="patient",status="active"));s.commit();return {"ok":True}

@app.post("/me/reminders/{rid}")
def update_reminder(rid:int,b:RemUp,u=Depends(who),s=Depends(db)):
    need(u,"patient");r=s.get(Reminder,rid)
    if not r or r.patient_id!=u["u"]:raise HTTPException(404,"Not found")
    if b.status not in("active","stopped"):raise HTTPException(400,"Bad status")
    if b.status=="active":
        ts=clean_times(b.times);today=dt.date.today()
        if r.until:  # keep the doctor's requested duration, counted from the day the patient accepts
            span=max((dt.date.fromisoformat(r.until)-dt.date.fromisoformat(r.start)).days,1);r.until=(today+dt.timedelta(days=span)).isoformat()
        r.times=",".join(ts);r.per_day=len(ts);r.start=today.isoformat();r.status="active"
        if r.by!="patient":
            s.add(Msg(patient_id=r.patient_id,doctor_id=r.by,sender="patient",text=f"Accepted: {r.label} reminders at {', '.join(ts)}.",at=now(),kind="chat",read=0))
    else:
        r.status="stopped"
        if r.by!="patient":s.add(Msg(patient_id=r.patient_id,doctor_id=r.by,sender="patient",text=f"Declined / stopped the {r.label} reminders.",at=now(),kind="chat",read=0))
    s.commit();return {"ok":True}

@app.post("/patients/{pid}/request-monitoring")
def request_monitoring(pid:str,b:Req,u=Depends(who),s=Depends(db)):
    need(u,"doctor");patient_or_404(s,pid)
    if not allowed(s,u,pid):raise HTTPException(403,"Patient consent required")
    if b.kind not in KL:raise HTTPException(400,"Unknown type")
    if b.kind=="dose" and not b.label.strip():raise HTTPException(400,"Medicine name is required")
    if not 1<=b.per_day<=6 or not 1<=b.days<=90:raise HTTPException(400,"Choose 1-6 times a day for 1-90 days")
    lbl=b.label.strip()[:60] if b.kind=="dose" else KL[b.kind]
    r=Reminder(patient_id=pid,kind=b.kind,label=lbl,per_day=b.per_day,start=dt.date.today().isoformat(),until=(dt.date.today()+dt.timedelta(days=b.days)).isoformat(),by=u["u"],status="proposed");s.add(r);s.flush()
    verb="take" if b.kind=="dose" else "check and record your"
    txt=f"Please {verb} {lbl.lower() if b.kind!='dose' else lbl} {b.per_day} time(s) a day for {b.days} days."+(" "+b.text.strip() if b.text.strip() else "")
    s.add(Msg(patient_id=pid,doctor_id=u["u"],sender="doctor",text=txt,at=now(),kind="request",rid=r.id))
    log(s,pid,label(s,u),f"Asked patient to monitor {lbl}");s.commit();return {"ok":True}

@app.get("/patients/{pid}/messages")
def get_msgs(pid:str,u=Depends(who),s=Depends(db)):
    patient_or_404(s,pid)
    if not allowed(s,u,pid):raise HTTPException(403,"Patient consent required")
    q=select(Msg).where(Msg.patient_id==pid).order_by(Msg.at,Msg.id)
    if u["r"]=="doctor":q=q.where(Msg.doctor_id==u["u"])
    dn={d.id:d.name for d in s.scalars(select(Doctor))};rows=s.scalars(q).all();out=[]
    for m in rows:
        if m.sender!=u["r"] and not m.read:m.read=1
        r=s.get(Reminder,m.rid) if m.rid else None
        out.append({"id":m.id,"sender":m.sender,"doctor":dn.get(m.doctor_id,""),"doctor_id":m.doctor_id,"text":m.text,"at":m.at,"kind":m.kind,"rid":m.rid,
            "rstatus":r.status if r else None,"per_day":r.per_day if r else None,"rlabel":r.label if r else None,"rtimes":times_of(r) if r else []})
    s.commit()
    return {"messages":out,"doctors":doctors_with_access(s,pid) if u["r"]=="patient" else []}

@app.post("/patients/{pid}/messages")
def send_msg(pid:str,b:MsgIn,u=Depends(who),s=Depends(db)):
    patient_or_404(s,pid)
    if not allowed(s,u,pid):raise HTTPException(403,"Patient consent required")
    t=b.text.strip()
    if not t:raise HTTPException(400,"Write a message first")
    if len(t)>1000:raise HTTPException(400,"Message is too long (max 1000 characters)")
    if u["r"]=="doctor":did=u["u"]
    else:
        did=b.to
        if did not in {d["id"] for d in doctors_with_access(s,pid)}:raise HTTPException(400,"Choose a doctor who has access to your record")
    s.add(Msg(patient_id=pid,doctor_id=did,sender=u["r"],text=t,at=now(),kind="chat",read=0));s.commit();return {"ok":True}

@app.get("/patients/{pid}/dashboard")
def dashboard(pid:str,u=Depends(who),s=Depends(db)):
    patient_or_404(s,pid)
    if not allowed(s,u,pid):raise HTTPException(403,"Patient consent required")
    if u["r"]=="doctor":log(s,pid,label(s,u),"Viewed monitoring dashboard");s.commit()
    return dash(s,pid)

@app.put("/patients/{pid}/limits")
def set_limits(pid:str,b:LimIn,u=Depends(who),s=Depends(db)):
    need(u,"doctor");patient_or_404(s,pid)
    if not allowed(s,u,pid):raise HTTPException(403,"Patient consent required")
    d={}
    for k,v in b.data.items():
        if k not in LIMD:raise HTTPException(400,f"Unknown limit {k}")
        try:d[k]=float(v)
        except (TypeError,ValueError):raise HTTPException(400,f"{k} must be a number")
    m={**LIMD,**d}
    if m["sys_lo"]>=m["sys_hi"] or m["dia_lo"]>=m["dia_hi"] or m["sugar_lo"]>=m["sugar_hi"]:raise HTTPException(400,"Each low limit must be below its high limit")
    r=s.get(Limit,pid)
    if r:r.data=json.dumps(d)
    else:s.add(Limit(patient_id=pid,data=json.dumps(d)))
    log(s,pid,label(s,u),"Changed alert limits");s.commit();return {"ok":True}

@app.post("/patients/{pid}/orders")
def add_order(pid:str,b:OrdIn,u=Depends(who),s=Depends(db)):
    need(u,"doctor");patient_or_404(s,pid)
    if not allowed(s,u,pid):raise HTTPException(403,"Patient consent required")
    if not b.name.strip():raise HTTPException(400,"Test name is required")
    if not 7<=b.every_days<=730:raise HTTPException(400,"Repeat every 7 to 730 days")
    s.add(Order(patient_id=pid,doctor_id=u["u"],name=b.name.strip()[:60],every_days=b.every_days,start=dt.date.today().isoformat()))
    log(s,pid,label(s,u),f"Ordered regular test: {b.name.strip()}");s.commit();return {"ok":True}

@app.delete("/patients/{pid}/orders/{oid}")
def del_order(pid:str,oid:int,u=Depends(who),s=Depends(db)):
    need(u,"doctor")
    if not allowed(s,u,pid):raise HTTPException(403,"Patient consent required")
    o=s.get(Order,oid)
    if not o or o.patient_id!=pid:raise HTTPException(404,"Not found")
    s.delete(o);s.commit();return {"ok":True}

@app.post("/patients/{pid}/labs")
def add_lab(pid:str,b:LabIn,u=Depends(who),s=Depends(db)):
    need(u,"doctor");patient_or_404(s,pid)
    if not allowed(s,u,pid):raise HTTPException(403,"Patient consent required")
    try:dt.date.fromisoformat(b.date)
    except ValueError:raise HTTPException(400,"Enter a valid date")
    if not b.name.strip():raise HTTPException(400,"Test name is required")
    note=f"{b.ref_lo}-{b.ref_hi}" if b.ref_lo is not None and b.ref_hi is not None else ""
    s.add(Measure(patient_id=pid,kind="lab:"+b.name.strip()[:40],v1=b.value,unit=b.unit.strip()[:20],at=b.date+" 09:00",note=note,src="doctor"))
    log(s,pid,label(s,u),f"Added lab value: {b.name.strip()}");s.commit();return {"ok":True}

@app.get("/alerts")
def alerts(u=Depends(who),s=Depends(db)):
    need(u,"doctor");ok=granted(s,u["u"])
    if not ok:return {"flagged":[],"unread":[]}
    cut=now(-3);nm={p.id:p.name for p in s.scalars(select(Patient).where(Patient.id.in_(ok)))}
    lims={}
    flagged={}
    for m in s.scalars(select(Measure).where(Measure.patient_id.in_(ok),Measure.at>=cut,Measure.kind.in_(VITALS)).order_by(Measure.at)):
        lim=lims.get(m.patient_id) or lims.setdefault(m.patient_id,lim_of(s,m.patient_id));f,t=flag(m,lim)
        if f:
            e=flagged.setdefault(m.patient_id,{"id":m.patient_id,"name":nm[m.patient_id],"count":0,"worst":None,"latest":"","at":""})
            e["count"]+=1;e["latest"]=f"{t}: {m.v1:g}"+(f"/{m.v2:g}" if m.v2 else "")+f" {m.unit}";e["at"]=m.at
            if f=="urgent" or e["worst"]!="urgent":e["worst"]=f
    unread=[{"id":pid,"name":nm.get(pid,pid),"n":n} for pid,n in s.execute(select(Msg.patient_id,func.count(Msg.id)).where(Msg.doctor_id==u["u"],Msg.sender=="patient",Msg.read==0).group_by(Msg.patient_id))]
    return {"flagged":sorted(flagged.values(),key=lambda e:(e["worst"]!="urgent",-e["count"])),"unread":unread}


# ---------------- appointments ----------------
class ApptIn(BaseModel):at:str;reason:str="";did:str=""
class ApptAct(BaseModel):note:str=""
def parse_at(v):
    try:d=dt.datetime.strptime(v.replace("T"," ")[:16],"%Y-%m-%d %H:%M")
    except ValueError:raise HTTPException(400,"Enter a valid date and time")
    if d<dt.datetime.now():raise HTTPException(400,"Choose a time in the future")
    if d>dt.datetime.now()+dt.timedelta(days=365):raise HTTPException(400,"Choose a date within the next year")
    return d.strftime("%Y-%m-%d %H:%M")
def tell(s,pid,did,sender,text):s.add(Msg(patient_id=pid,doctor_id=did,sender=sender,text=text,at=now(),kind="chat",read=0))
def clash(s,did,at,skip=0):return s.scalar(select(Appt).where(Appt.doctor_id==did,Appt.at==at,Appt.status=="scheduled",Appt.id!=skip))

@app.post("/patients/{pid}/appointments")
def book(pid:str,b:ApptIn,u=Depends(who),s=Depends(db)):
    patient_or_404(s,pid)
    if not allowed(s,u,pid):raise HTTPException(403,"Patient consent required")
    at=parse_at(b.at);reason=b.reason.strip()[:200]
    if u["r"]=="doctor":
        did,status,by=u["u"],"scheduled","doctor"
        if clash(s,did,at):raise HTTPException(409,"You already have an appointment at that time")
        tell(s,pid,did,"doctor",f"Appointment scheduled for {at}. {reason}".strip())
    else:
        did,status,by=b.did.strip().upper(),"requested","patient"
        if not s.get(Doctor,did) or pid not in granted(s,did):raise HTTPException(400,"Choose a doctor who has access to your record")
        tell(s,pid,did,"patient",f"I would like an appointment on {at}. {reason}".strip())
    s.add(Appt(patient_id=pid,doctor_id=did,at=at,reason=reason,status=status,by=by));log(s,pid,label(s,u),f"Appointment {status} for {at}");s.commit();return {"ok":True}

@app.post("/appointments/{aid}/{act}")
def appt_act(aid:int,act:str,b:ApptAct,u=Depends(who),s=Depends(db)):
    a=s.get(Appt,aid)
    if not a or act not in("confirm","cancel","complete"):raise HTTPException(404,"Not found")
    isdoc=u["r"]=="doctor" and a.doctor_id==u["u"];ispat=u["r"]=="patient" and a.patient_id==u["u"]
    if not(isdoc or ispat):raise HTTPException(403,"Not allowed")
    if a.status in("cancelled","completed"):raise HTTPException(400,"This appointment is already "+a.status)
    note=b.note.strip()[:200];sender="doctor" if isdoc else "patient"
    if act=="confirm":
        if not isdoc or a.status!="requested":raise HTTPException(400,"Nothing to confirm")
        if clash(s,a.doctor_id,a.at,a.id):raise HTTPException(409,"You already have an appointment at that time")
        a.status="scheduled";tell(s,a.patient_id,a.doctor_id,"doctor",f"Your appointment on {a.at} is confirmed.")
    elif act=="complete":
        if not isdoc or a.status!="scheduled":raise HTTPException(400,"Only a scheduled appointment can be completed")
        a.status="completed"
    else:
        verb="declined" if (isdoc and a.status=="requested") else "cancelled"
        a.status="cancelled";a.note=note
        tell(s,a.patient_id,a.doctor_id,sender,(f"Your appointment on {a.at} was {verb} by the doctor." if isdoc else f"I have cancelled my appointment on {a.at}.")+(f" Reason: {note}" if note else ""))
    s.commit();return {"ok":True}

@app.get("/appointments")
def appts(u=Depends(who),s=Depends(db)):
    need(u,"doctor");today=now()[:10];end=(dt.date.today()+dt.timedelta(days=31)).isoformat()
    rows=s.scalars(select(Appt).where(Appt.doctor_id==u["u"],Appt.status.in_(["requested","scheduled"]),Appt.at>=today,Appt.at<end).order_by(Appt.at)).all()
    pn={p.id:p.name for p in s.scalars(select(Patient).where(Patient.id.in_({r.patient_id for r in rows})))}
    f=lambda r:{"id":r.id,"pid":r.patient_id,"name":pn.get(r.patient_id,""),"at":r.at,"reason":r.reason,"status":r.status,"by":r.by}
    return {"today":[f(r) for r in rows if r.status=="scheduled" and r.at[:10]==today],"requests":[f(r) for r in rows if r.status=="requested"],"upcoming":[f(r) for r in rows if r.status=="scheduled" and r.at[:10]>today]}

@app.get("/me/appointments")
def my_appts(u=Depends(who),s=Depends(db)):
    need(u,"patient");today=now()[:10]
    rows=s.scalars(select(Appt).where(Appt.patient_id==u["u"]).order_by(Appt.at)).all()
    dn={d.id:d.name for d in s.scalars(select(Doctor))}
    f=lambda r:{"id":r.id,"doctor":dn.get(r.doctor_id,""),"at":r.at,"reason":r.reason,"status":r.status,"note":r.note}
    up=[f(r) for r in rows if r.status in("requested","scheduled") and r.at[:10]>=today];ids={x["id"] for x in up}
    return {"upcoming":up,"earlier":[f(r) for r in reversed(rows) if r.id not in ids][:8]}
