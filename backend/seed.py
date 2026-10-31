"""Builds a SYNTHETIC dataset (3 states) and loads it into the database. No real people or records."""
import random,re,math,glob,datetime as dt
from app import *
import io
from PIL import Image,ImageDraw
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5,A4
R=random.Random(7);T=dt.date(2026,10,30)
ST={"Rajasthan":(["Jaipur","Udaipur","Jodhpur","Kota"],["Aarav","Diya","Kabir","Anaya","Ishaan","Meera","Rohan","Sneha","Vikram","Pooja","Dev","Kavya"],["Sharma","Rathore","Joshi","Meena","Choudhary","Bhati","Gehlot","Purohit"]),
"Gujarat":(["Ahmedabad","Surat","Vadodara","Rajkot"],["Hiral","Jay","Mansi","Chirag","Nisha","Parth","Riddhi","Kunal","Dhruv","Bhavna","Yash","Foram"],["Patel","Shah","Desai","Mehta","Trivedi","Parmar","Solanki","Vyas"]),
"Maharashtra":(["Mumbai","Pune","Nagpur","Nashik"],["Aditya","Sakshi","Omkar","Priya","Tejas","Shruti","Rahul","Neha","Siddharth","Pallavi","Amey","Gauri"],["Deshmukh","Kulkarni","Patil","Joshi","Pawar","More","Jadhav","Bhosale"])}
SPEC=["General Medicine","Paediatrics","Cardiology","Orthopaedics","Gynaecology","ENT","Dermatology","Endocrinology","Pulmonology","Gastroenterology","Neurology","Ophthalmology"]
CONDS=[("Type 2 diabetes","Metformin","500 mg twice daily after meals","HbA1c",["6.8 %","7.4 %","8.1 %"]),("Hypertension","Amlodipine","5 mg once daily","ECG",["Normal sinus rhythm","Mild left ventricular strain"]),("Asthma","Budesonide inhaler","200 mcg, 2 puffs twice daily","Spirometry",["FEV1 82 % of predicted","FEV1 71 % of predicted"]),("Hypothyroidism","Levothyroxine","50 mcg every morning","TSH",["2.8 mIU/L","6.4 mIU/L"]),("Migraine","Sumatriptan","50 mg at onset, max 2 per day","MRI brain",["No acute abnormality"]),("Iron-deficiency anaemia","Ferrous ascorbate","100 mg once daily","CBC",["Hb 9.8 g/dL","Hb 11.6 g/dL"]),("GERD","Pantoprazole","40 mg before breakfast","Upper GI endoscopy",["Mild oesophagitis","Normal study"]),("Osteoarthritis (knee)","Diclofenac gel","Apply twice daily","X-ray knee",["Joint space narrowing, grade 2"]),("Typhoid","Cefixime","200 mg twice daily for 10 days","Widal test",["Titre 1:160 positive"]),("Dengue","Paracetamol","500 mg every 6 hours","Platelet count",["96,000 per microlitre","148,000 per microlitre"])]
SURG=["Appendectomy","Cholecystectomy","Cataract surgery","Inguinal hernia repair","Knee arthroscopy","Tonsillectomy","Caesarean section"]
def D(a,b):return a+dt.timedelta(days=R.randrange(max((b-a).days,1)+1))
def iso(d):return d.isoformat()
FILEKINDS={"Prescription","Report","Surgery","Discharge"}
NUMT={"HbA1c":("HbA1c","%",4.0,5.6),"TSH":("TSH","mIU/L",0.4,4.0),"CBC":("Hemoglobin","g/dL",12.0,16.0),"Platelet count":("Platelets","per uL",150000,410000)}
def num(res):return float(re.search(r"[\d,]+\.?\d*",res).group().replace(",",""))
def mkpdf(title,date,body,who,pname,pid,rows=None):
    """Synthetic document. With rows -> structured lab report (test / result / unit / reference range / flag)."""
    b=io.BytesIO();c=canvas.Canvas(b,pagesize=A4 if rows else A5);w,h=A4 if rows else A5
    c.setFont("Helvetica-Bold",14);c.drawString(30,h-42,"MediCase Diagnostics" if rows else "MediCase - Prescription / Record")
    c.setFont("Helvetica",8);c.setFillGray(.45);c.drawString(30,h-55,"SYNTHETIC DEMO DOCUMENT - not a real patient or laboratory");c.setFillGray(0)
    c.line(30,h-62,w-30,h-62);c.setFont("Helvetica-Bold",11);c.drawString(30,h-82,title[:70])
    c.setFont("Helvetica",9);c.drawString(30,h-98,f"Patient: {pname} ({pid})");c.drawString(30,h-111,f"Date: {date}     Doctor: {who}")
    y=h-140
    if rows:
        for x,t in ((30,"TEST"),(210,"RESULT"),(290,"UNIT"),(350,"REFERENCE"),(460,"FLAG")):c.setFont("Helvetica-Bold",9);c.drawString(x,y,t)
        c.line(30,y-4,w-30,y-4);y-=20
        for t,r,u,ref,f in rows:
            c.setFont("Helvetica-Bold" if f else "Helvetica",9)
            for x,v in ((30,t),(210,r),(290,u),(350,ref),(460,f)):c.drawString(x,y,str(v)[:34])
            y-=18
        y-=10;c.setFont("Helvetica",8);c.drawString(30,y,"H = above reference range, L = below. Interpret with clinical findings.")
    else:
        c.setFont("Helvetica",9)
        for ln in body.split("\n"):c.drawString(30,y,ln[:90]);y-=14
    c.setFont("Helvetica",8);c.drawString(30,40,f"Reported by {who}");c.save();return b.getvalue()
def pick_img(kind):
    """Uses real public-dataset images if you put them in backend/real_images/xray or /scan; otherwise a synthetic picture."""
    fs=[f for f in glob.glob(f"real_images/{'xray' if kind=='X-ray' else 'scan'}/*") if f.lower().endswith((".jpg",".jpeg",".png",".webp"))]
    if not fs:return scan_img(kind),False
    im=Image.open(R.choice(fs)).convert("RGB");im.thumbnail((1024,1024));o=io.BytesIO();im.save(o,"JPEG",quality=82);return o.getvalue(),True
def scan_img(kind):
    im=Image.new("L",(420,520),10);d=ImageDraw.Draw(im)
    if kind=="X-ray":
        d.ellipse((70,80,350,480),fill=38);d.rectangle((205,80,215,480),fill=105)
        for i in range(9):d.arc((120-i*3,130+i*32,300+i*3,200+i*32),200,340,fill=R.randint(120,170),width=3)
    else:
        for i in range(10):d.ellipse((60+i*14,70+i*16,360-i*14,450-i*16),outline=60+i*14,width=3)
    d.text((10,10),"SYNTHETIC DEMO - NOT A REAL SCAN",fill=190)
    o=io.BytesIO();im.save(o,"JPEG",quality=70);return o.getvalue()
def seed_db(drop_first=False):
    if drop_first:
        Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    TODAY=dt.date.today();NOW=dt.datetime.now();stamp=lambda x:x.strftime("%Y-%m-%d %H:%M")
    def gen(pid,kind,times,days,fn,notes=None,adh=.88,unit=""):
        """Home readings at the reminder times (with small jitter), skipping some to mimic real adherence; never in the future."""
        for i in range(days-1,-1,-1):
            d=TODAY-dt.timedelta(days=i)
            for j,t in enumerate(times):
                h,m=map(int,t.split(":"));x=dt.datetime.combine(d,dt.time(h,m))+dt.timedelta(minutes=R.randint(-25,25))
                if x>NOW or R.random()>adh:continue
                v1,v2=fn(i,j);s.add(Measure(patient_id=pid,kind=kind,v1=round(v1),v2=round(v2) if v2 else None,unit=unit,at=stamp(x),note=(notes[j] if notes else ""),src="patient"))
    def talk(pid,did,sender,text,when,kind="chat",rid=None,read=1):
        s.add(Msg(patient_id=pid,doctor_id=did,sender=sender,text=text,at=stamp(when),kind=kind,rid=rid,read=read))
    s=SL();dn=pn=0
    for sti,(cities,fn,ln) in ST.items():
        local=[]
        for i in range(12):
            dn+=1;d=Doctor(id=f"DR{1000+dn}",name=f"Dr. {R.choice(fn)} {R.choice(ln)}",speciality=SPEC[i],state=sti,city=cities[i%4],pw=H("doc123"));s.add(d);local.append(d)
        for i in range(50):
            pn+=1;demo=pn==1;city="Jaipur" if demo else R.choice(cities);sti_=sti
            dob=dt.date(1968,4,12) if demo else D(dt.date(1946,1,1),dt.date(2024,6,30));age=(T-dob).days//365;pid=f"MC{1000+pn}"
            pname=f"{R.choice(fn)} {R.choice(ln)}";sex=R.choice(["Male","Female"])
            s.add(Patient(id=pid,name=pname,dob=iso(dob),sex=sex,blood=R.choice(["A+","B+","O+","AB+","A-","B-","O-"]),allergies=R.choice(["None known","None known","Penicillin","Sulfa drugs","Dust","Peanuts","Aspirin"]),state=sti,city=city,pw=H("pat123"),abha=f"{R.randint(10,99)}-{R.randint(1000,9999)}-{R.randint(1000,9999)}-{R.randint(1000,9999)}"))
            near=[d for d in local if d.city==city] or local
            def add(kind,title,date,body,img=None,rows=None):
                d=R.choice(near);f=m=fn_=None;slug=title.replace(" ","_").replace(":","")
                if img:f,m,fn_=img,"image/jpeg",slug+".jpg"
                elif kind in FILEKINDS:f,m,fn_=mkpdf(title,iso(date),body,d.name,pname,pid,rows),"application/pdf",slug+".pdf"
                s.add(Document(patient_id=pid,doctor_id=d.id,kind=kind,title=title,date=iso(date),body=body,file=f,mime=m,fname=fn_))
            add("Birth","Birth record",dob,f"Born at {city}. Weight {R.uniform(2.5,3.8):.1f} kg. {R.choice(['Normal delivery','Caesarean delivery'])}. APGAR score {R.choice([8,9,9,10])}.")
            add("Vaccination","Childhood immunisation",dob+dt.timedelta(days=45),"BCG, OPV, Hepatitis B and DPT first doses given. Schedule followed through age 5.")
            names=[]
            if age>=5:
                for c,drug,dose,test,res in ([CONDS[0],CONDS[1]] if demo else R.sample(CONDS,R.randint(1,2))):
                    names.append(c);on=D(max(dob,T-dt.timedelta(days=3650)),T-dt.timedelta(days=60))
                    add("Illness",c,on,f"Diagnosed with {c}. Lifestyle advice given and follow-up planned.")
                    for _ in range(R.randint(1,3)):
                        add("Prescription",f"Prescription: {drug}",D(on,T),f"Rx: {drug}\nDose: {dose}\nDuration: {R.choice(['1 month','3 months','6 months'])}\nAdvice: {R.choice(['Review after 4 weeks','Repeat tests before next visit','Avoid self-medication'])}")
                    for _ in range(R.randint(1,2)):
                        rd=D(on,T);r=R.choice(res)
                        if test in NUMT:
                            nm,un,lo,hi=NUMT[test];v=num(r);f=" H" if v>hi else " L" if v<lo else "";fl=f.strip()
                            add("Report",f"{test} report",rd,f"Test: {test}\nResult: {r}\nRemarks: Interpret with clinical findings.",rows=[(nm,f"{v:g}",un,f"{lo:g} - {hi:g}",fl)])
                            s.add(Measure(patient_id=pid,kind="lab:"+nm,v1=v,unit=un,at=iso(rd)+" 09:00",note=f"{lo:g}-{hi:g}",src="lab"))
                            for k in (1,2,3):  # earlier follow-up values so the trend chart has history
                                pd_=rd-dt.timedelta(days=75*k)
                                if pd_>=on:s.add(Measure(patient_id=pid,kind="lab:"+nm,v1=round(v*R.uniform(.9,1.14),1),unit=un,at=iso(pd_)+" 09:00",note=f"{lo:g}-{hi:g}",src="lab"))
                        else:
                            add("Report",f"{test} report",rd,f"Test: {test}\nResult: {r}\nRemarks: Interpret with clinical findings.",rows=[(test,r[:34],"","","")])
            if age>=12 and R.random()<.35:
                sx=R.choice(SURG);dd=D(dob+dt.timedelta(days=4000),T-dt.timedelta(days=30))
                add("Surgery",sx,dd,f"Procedure: {sx}. Performed under {R.choice(['general','spinal','local'])} anaesthesia. No intra-operative complications.")
                add("Discharge",f"Discharge summary: {sx}",min(dd+dt.timedelta(days=3),T),"Admitted 3 days. Discharged stable. Wound care advised; follow-up in 2 weeks.")
            if age>=5 and (demo or R.random()<.45):
                im,real=pick_img("X-ray");add("X-ray",R.choice(["Chest X-ray","Knee X-ray","Spine X-ray"]),D(dob+dt.timedelta(days=1800),T),"Radiology image (public dataset sample, not this patient's own scan)." if real else "Radiology image (synthetic).",img=im)
            if age>=15 and (demo or R.random()<.25):
                im,real=pick_img("Scan");add("Scan",R.choice(["MRI brain","CT abdomen","Ultrasound abdomen"]),D(dob+dt.timedelta(days=5400),T),"Scan image (public dataset sample, not this patient's own scan)." if real else "Scan image (synthetic).",img=im)
            cons=[local[0]] if demo else R.sample(near,min(len(near),R.randint(1,2)))
            for d in cons:s.add(Consent(patient_id=pid,doctor_id=d.id,status="granted"))
            # ---------- home monitoring: reminders, readings, messages, regular tests ----------
            doc=cons[0];hyp="Hypertension" in names;dia="Type 2 diabetes" in names
            def request(kind,label,times,per_day):
                """Doctor asks -> patient accepts and sets times (as in the app). A few stay pending so the accept flow can be tried."""
                pending=(not demo) and R.random()<.15;st="proposed" if pending else "active"
                r=Reminder(patient_id=pid,kind=kind,label=label,times="" if pending else ",".join(times),per_day=per_day,start=iso(TODAY-dt.timedelta(days=30 if not pending else 0)),until=iso(TODAY+dt.timedelta(days=60)),by=doc.id,status=st);s.add(r);s.flush()
                t0=dt.datetime.combine(TODAY-dt.timedelta(days=30 if not pending else 1),dt.time(9,10))
                talk(pid,doc.id,"doctor",f"Please check your {label.lower()} {per_day} time(s) a day and record it here.",t0,"request",r.id,read=1 if not pending else 0)
                if not pending:talk(pid,doc.id,"patient",f"Accepted: {label} reminders at {', '.join(times)}.",t0+dt.timedelta(minutes=20))
                return not pending
            if hyp and request("bp","Blood pressure",["08:00","14:00","20:00"],3):
                sb=R.randint(124,156) if not demo else 134;db_=sb-R.randint(40,50) if not demo else 84;amp=R.uniform(2,6)
                gen(pid,"bp",["08:00","14:00","20:00"],30,lambda i,j:(sb+amp*math.sin(i/4)+R.gauss(0,5)+(14 if R.random()<.03 else 0)-(3 if j==1 else 0),db_+amp/2*math.sin(i/4)+R.gauss(0,3)),adh=.92 if demo else R.uniform(.55,.97),unit="mmHg")
            if dia and request("sugar","Blood sugar",["07:30","21:00"],2):
                fb=R.randint(98,150) if not demo else 128
                gen(pid,"sugar",["07:30","21:00"],30,lambda i,j:(fb+R.gauss(0,12) if j==0 else fb+55+R.gauss(0,25),None),notes=["Fasting","After meal"],adh=.9 if demo else R.uniform(.5,.97),unit="mg/dL")
            if R.random()<.3 and age>=15:
                wb=R.uniform(48,92)
                for wk in range(8):
                    x=dt.datetime.combine(TODAY-dt.timedelta(days=7*(7-wk)),dt.time(7,15))
                    if x<=NOW:s.add(Measure(patient_id=pid,kind="weight",v1=round(wb+R.gauss(0,.6)-wk*.1,1),unit="kg",at=stamp(x),src="patient"))
            if hyp or dia:
                if hyp:s.add(Order(patient_id=pid,doctor_id=doc.id,name="ECG",every_days=R.choice([180,365]),start=iso(TODAY-dt.timedelta(days=100))))
                if dia:s.add(Order(patient_id=pid,doctor_id=doc.id,name="HbA1c",every_days=90,start=iso(TODAY-dt.timedelta(days=100))))
                if R.random()<.35:talk(pid,doc.id,"patient","Doctor, I felt a little dizzy yesterday evening. Should I change anything?",NOW-dt.timedelta(hours=R.randint(2,30)),read=0)
                if R.random()<.35:talk(pid,doc.id,"doctor","Thanks for keeping your records up to date. Continue the same medicines and keep recording.",NOW-dt.timedelta(days=2),read=1)
            if demo:  # demo patient: make the dashboard and alerts interesting right away
                s.add(Measure(patient_id=pid,kind="bp",v1=164,v2=104,unit="mmHg",at=stamp(NOW-dt.timedelta(minutes=40)),src="patient"))
                s.add(Measure(patient_id=pid,kind="sugar",v1=214,unit="mg/dL",at=stamp(NOW-dt.timedelta(hours=1)),note="After meal",src="patient"))
                talk(pid,doc.id,"patient","Good morning doctor, my BP was higher than usual today and I have a mild headache.",NOW-dt.timedelta(minutes=35),read=0)
                talk(pid,doc.id,"doctor","Please also check your pulse twice a day this week and tell me if the headache gets worse.",NOW-dt.timedelta(hours=20),read=0)
    s.commit();print(f"Seeded {dn} doctors, {pn} patients, {s.query(Document).count()} documents, {s.query(Measure).count()} readings/lab values, {s.query(Reminder).count()} reminders, {s.query(Msg).count()} messages in {URL}");print("Demo logins: DR1001 / doc123  and  MC1001 / pat123  (MC1001 has diabetes + hypertension monitoring and DR1001 has access)");s.close()

if __name__ == "__main__":
    seed_db(drop_first=True)
