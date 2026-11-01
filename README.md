# MediCase v6 (React + FastAPI + database)

Doctor and patient logins, a synthetic multi-state record dataset, consent-based access, document uploads, PDF export,
and (new in v6) **home monitoring**: doctor-requested BP/sugar checks, patient reminders, messaging, alerts and a dashboard.

## Run
Backend (Python 3.10+):
    cd backend
    pip install -r requirements.txt
    python seed.py                  # creates medicase.db (re-run after every upgrade; it rebuilds the database)
    uvicorn app:app --reload        # API on http://localhost:8000 (docs at /docs)

Frontend (Node 18+):
    cd frontend
    npm install
    npm run dev                     # http://localhost:5173  (set VITE_API if the API is elsewhere)

PostgreSQL: `pip install psycopg2-binary`, set `DATABASE_URL=postgresql+psycopg2://user:password@localhost/medicase` before `python seed.py` and `uvicorn`. Also set a real `SECRET`.

## Demo logins
Doctor `DR1001` / `doc123` (DR1001..DR1036). Patient `MC1001` / `pat123` (MC1001..MC1150).
**Try this:** log in as DR1001 -> "Needs attention" shows MC1001 (high BP/sugar today + unread message) -> open Dashboard -> use *Ask the patient to monitor*.
Log out, log in as MC1001 -> Today panel -> Messages -> accept the request and set times -> Record a reading -> see it on the Dashboard.

## What it does
**Records and access (v1-v5)** - statewide patient search (name, ID, ABHA-style number), consent requests, patient share codes, logged 24h emergency override,
document sections (prescriptions, lab reports, X-ray/scan gallery, surgery/discharge, history), real file upload (PDF/JPG/PNG/WebP, 10 MB, type checked by content),
record summary (automatic, or AI with `ANTHROPIC_API_KEY`), PDF export of any selection, patient access log.

**Home monitoring (v6)**
- *Doctor requests monitoring*: choose BP, sugar, weight, pulse, SpO2, temperature or a medicine, times per day (1-6) and number of days, plus a note. It arrives as a message.
- *Patient reminders*: the patient accepts and sets the clock times (default 3 times a day for BP), or declines; patients can also create their own reminders. The doctor is told automatically.
- *Today panel*: checklist of today's slots (done / missed / upcoming), one-tap "Taken" for medicines, in-app banner and optional browser notification at reminder time.
- *Recording*: BP (systolic/diastolic), sugar (fasting / before meal / after meal / bedtime / random), weight, pulse, SpO2, temperature, medicine taken. Input is validated; future times are rejected.
- *Safety feedback*: after saving, the patient sees if the value is high/low; very abnormal values show "get medical help if you feel unwell". The doctor sees the reading.
- *Dashboard* (doctor and patient): latest values, 7-day and 30-day averages, % of readings in range, 30-day charts with the normal range shaded and out-of-range points coloured, flagged readings list, reminder adherence (readings recorded vs expected, last 7 days), numeric lab trends (latest, previous, arrow), regular tests due/overdue.
- *Alert limits*: sensible defaults (BP 140/90 high, below 90/60 low; sugar 180 high, below 70 low) that the doctor can change per patient. Very-abnormal cut-offs are fixed.
- *Regular tests*: doctor orders e.g. HbA1c every 90 days; status becomes due soon / overdue from the last matching report or lab value.
- *Lab values*: doctors add numeric results with reference range; they feed the dashboard trends. Generated lab reports are structured PDFs (test, result, unit, reference, H/L flag).
- *Doctor "Needs attention"*: patients with flagged readings in the last 3 days, and unread patient messages.
- *Messages*: doctor <-> patient thread per doctor (only doctors with access). Patients can only message doctors they have given access.
- *PDF export* can include a home-monitoring summary table.
- Every doctor view of a patient's record or dashboard appears in the patient's access log.

**Security fixes in v6** - tokens expire after 12 hours; share codes use a secure random generator, expire after 30 minutes and lock out after 5 wrong tries per 15 minutes; duplicate consent rows are prevented; PDF export tells you if an attached file could not be merged.

## New in v7
- **Appointments:** the doctor home screen has an Appointments panel (today, patient requests, next 30 days). Doctors schedule by patient ID (they need access to the record), confirm or decline patient requests, mark visits done, or cancel with a reason. Patients see their appointments, request one with any doctor who has access, and cancel. Every change sends a message to the other side, and double-booking a doctor's time is blocked. Demo: DR1001 has appointments today, tomorrow and one patient request (run `python seed.py` again).
- **Files are optional:** a document can be a file, a text note, or both. A note alone is fine.

## Real images
Put open-licence images in `backend/real_images/xray` and `backend/real_images/scan`, then run `python seed.py` (see the README in that folder). Without them, synthetic placeholders are used.

## Dataset (synthetic)
3 states, 12 cities, 36 doctors, 150 patients, ~1,450 documents, ~2,500 readings/lab values. All names and records are generated by `seed.py`; no real person is represented.

## Limits (be aware)
- Reminders work **only while MediCase is open in a browser tab**. They are not SMS, WhatsApp or phone push. That needs a service such as Firebase Cloud Messaging, Twilio or WhatsApp Business plus a scheduler.
- Alert thresholds are general defaults, not medical advice; a doctor must set them per patient. The app does not diagnose.
- Dashboard values are patient-entered, not device-verified. No Bluetooth/glucometer/BP-cuff integration.
- Real ABDM/ABHA integration (verification, consent manager, FHIR) is not included.
- Not production-ready: HMAC tokens (no JWT/refresh), unsalted SHA-256 passwords, no encryption at rest, CORS open to all, files stored in the database, share-code attempt counter is in memory (resets on restart, single process).
  Real patient data would also need DPDP Act compliance (consent, data-processing agreements, retention, breach process).
