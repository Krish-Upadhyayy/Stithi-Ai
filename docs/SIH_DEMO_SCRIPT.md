# SIH Presentation Demo Script (5–7 Minute Flow)

**Project Name:** AI Training Centre Monitoring System  
**Category:** Smart Automation / Video Analytics / Governance Compliance  
**Target Evaluators:** Smart India Hackathon (SIH) Jury & Ministry of Skill Development and Entrepreneurship (MSDE)  
**Target Duration:** 5 to 7 Minutes  

---

## Preparation & Prerequisites Checklist (T-Minus 5 Minutes)

1. **Backend Running:**
   ```bash
   cd backend && source .venv/bin/activate
   uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
   ```
2. **Frontend Running:**
   ```bash
   cd frontend
   npm run dev  # Accessible at http://localhost:3000
   ```
3. **Controlled Demo State Seeding (Optional):**
   ```bash
   python scripts/seed_demo.py --execute
   ```
   *Seeds `demo_admin@sih.gov.in` / `DemoAdmin123!` and `[DEMO] National Skilling Centre Delhi-01`.*
4. **Demo Video Ready:**
   `data/input/demo_classroom_sample.mp4` (or any sample MP4 from a training classroom).

---

## Minute-by-Minute Presentation Script

### 0:00 – 0:30 | The Governance Problem
**Visual:** Slide or Dashboard landing screen (`/`).  
**Presenter Speaking:**  
> *"Respected Jury members, across thousands of government-funded skill development centres under PMKVY and state skill missions, billions of rupees are disbursed annually based on self-reported attendance registers and paper inventory declarations.*  
>  
> *Manual inspections are infrequent, cost-prohibitive, and prone to manipulation. While thousands of centres already have mandated CCTV cameras installed, these video feeds sit recorded on local DVRs without any automated compliance checks. The government urgently needs verifiable, objective monitoring of:*  
> 1. *Trainee physical attendance,*  
> 2. *Sanctioned equipment presence,*  
> 3. *Real-time compliance without violating privacy."*

---

### 0:30 – 1:00 | The Solution
**Visual:** Show Login Page (`/login`) & Dashboard Overview (`/dashboard`).  
**Presenter Speaking:**  
> *"To solve this, we present the **AI Training Centre Monitoring System**.*  
>  
> *Our solution transforms passive CCTV video into an active, privacy-preserving compliance audit trail. Crucially, our system does not rely on student face recognition or intrusive biometric identity tracking. Instead, it extracts periodic snapshot frames, runs fine-tuned YOLO26 computer vision models for anonymous presence detection and equipment availability, compares observations against sanctioned baselines, and flags discrepancy alerts for human officer review."*

---

### 1:00 – 1:30 | System Architecture & Privacy Core
**Visual:** Architecture Diagram or Navbar AI Status badge.  
**Presenter Speaking:**  
> *"Our end-to-end processing pipeline operates in strict decoupled stages:*  
>  
> $$\text{CCTV Video} \longrightarrow \text{Periodic Snapshots} \longrightarrow \begin{matrix} \text{YOLO26 Attendance} \\ \text{YOLO26 Infrastructure} \end{matrix} \longrightarrow \text{Compliance Engine} \longrightarrow \text{Evidence Alerts} \longrightarrow \text{Human Review}$$  
>  
> *Under India's Digital Personal Data Protection (DPDP) Act, mass facial recognition in public classrooms creates immense legal and privacy liability. Our system is privacy-by-design: attendance is estimated solely via anonymous aggregate headcounts, and evidence snapshots are strictly audit-logged."*

---

### 1:30 – 2:30 | Centre Profile, Cameras & Inventory Baseline
**Visual:** Navigate to `/centres` $\rightarrow$ Click into `[DEMO] National Skilling Centre Delhi-01` (`/centres/1`).  
**Presenter Speaking:**  
> *"Here on the Centre Management screen, administrators manage sanctioned institutions. For this centre:*  
> - *We have configured classroom cameras linked to DVR streams or MP4 video files.*  
> - *Under **Sanctioned Inventory Baseline**, you see approved government allocations: 20 Computers, 25 Chairs, 4 Workbenches, and 2 Fire Extinguishers, uploaded directly via official government Excel spreadsheets.*  
>  
> *Notice our transparency principle: visual equipment detection indicates apparent presence on camera—we never make unsubstantiated claims that an item is electrically or mechanically operational without hands-on testing."*

---

### 2:30 – 3:30 | Monitoring Session Creation & Snapshot Extraction
**Visual:** Navigate to `/monitoring` $\rightarrow$ Click `New Session` $\rightarrow$ Select Centre & Camera.  
**Presenter Speaking:**  
> *"Now we simulate a daily monitoring session:*  
> 1. *The training centre supervisor enters the officially declared physical attendance: **18 Trainees**.*  
> 2. *We create the session and upload the day's session video (`demo_classroom_sample.mp4`).*  
> 3. *Our video engine validates the video container, extracts metadata (duration, FPS, resolution), and samples periodic snapshot frames at configurable intervals.*  
>  
> *Clicking into Session Details, you can see all extracted snapshot frames captured directly from the camera feed."*

---

### 3:30 – 4:15 | AI Inference Execution (Attendance + Infrastructure)
**Visual:** On Session Detail (`/monitoring/{id}`), click `Run Attendance AI`, then `Run Infra AI`.  
**Presenter Speaking:**  
> *"Now we trigger our specialized AI pipelines:*  
>  
> 1. ***YOLO26 Attendance AI**: The model processes each frame, detecting human trainee presence bounding boxes. Crucially, no student identity or face vector is extracted. The engine computes robust aggregate metrics like median and mean headcount across frames.*  
> 2. ***YOLO26 Infrastructure AI**: Runs our distinct object detection pipeline to observe visible sanctioned assets—chairs, desks, computers, and safety gear.*  
>  
> *Both models run asynchronously with empirical inference latencies."*

---

### 4:15 – 5:00 | Compliance Engine Evaluation
**Visual:** Click `Evaluate Compliance` $\rightarrow$ Scroll to Attendance Timeline and Inventory Comparison.  
**Presenter Speaking:**  
> *"Once observations are recorded, our deterministic **Compliance Engine** executes:*  
>  
> - ***Attendance Evaluation**: The centre reported **18** trainees. The AI model observed a median of **12** trainees. With our standard tolerance of $\pm 2$, this difference of **6** trainees exceeds tolerance, resulting in an **Attendance Discrepancy** status.*  
> - ***Infrastructure Evaluation**: The baseline expected **20 Computers** and **25 Chairs**. The visual detector observed **15 Computers**. This is flagged as a **Potential Infrastructure Discrepancy**.*  
>  
> *Everything is backed by mathematical variance formulas, not opaque heuristic guesses."*

---

### 5:00 – 5:45 | Evidence-Backed Alert Generation
**Visual:** Click `Generate Alerts` $\rightarrow$ Navigate to Compliance Alerts (`/alerts`) $\rightarrow$ Click into Alert.  
**Presenter Speaking:**  
> *"Discrepancies automatically generate high-priority **Evidence-backed Alerts**.*  
>  
> *Let us open the generated alert. Notice the audit trail:*  
> - *Expected value vs. AI observed value.*  
> - *Timestamped snapshot frames showing the exact visual state when the discrepancy occurred.*  
> - *Reviewers can toggle bounding box annotations to inspect visual presence.*  
> - *The alert status begins in **PENDING** state. No automated punitive action is taken against the training centre without human authorization."*

---

### 5:45 – 6:15 | Human Review Workflow
**Visual:** On `/alerts/{id}`, select Decision: `VERIFIED` or `FALSE POSITIVE`, enter reviewer comment, and submit.  
**Presenter Speaking:**  
> *"Our system enforces mandatory human-in-the-loop oversight:*  
>  
> *A designated government inspector or audit reviewer examines the evidence:*  
> - *If students were temporarily outside on a scheduled break or camera angle was occluded, the reviewer can mark the alert as **FALSE POSITIVE** with explanatory notes.*  
> - *If genuine attendance inflation occurred, the reviewer marks it as **VERIFIED** and escalates it.*  
>  
> *Let us mark this as **VERIFIED** with note: 'Significant headcount shortfall confirmed on visual inspection.' The audit log records the reviewer's ID, timestamp, and comments."*

---

### 6:15 – 7:00 | Centralized Governance Dashboard & Conclusion
**Visual:** Navigate back to `/dashboard`.  
**Presenter Speaking:**  
> *"Returning to the central dashboard, state and national authorities have full real-time visibility:*  
>  
> - *Total monitored centres and operational cameras,*  
> - *Total sessions completed,*  
> - *Active alerts classified by severity and status (Pending vs. Verified vs. False Positive),*  
> - *Compliance distribution charts and recent audit activity feed.*  
>  
> *In summary, our system provides a scalable, DPDP-compliant, evidence-backed monitoring platform that protects public skilling funds while respecting student privacy.*  
>  
> *Thank you, and we welcome your questions!"*

---

## Anticipated Jury Questions & Recommended Responses

1. **Q: Why not use facial recognition for exact attendance?**  
   *A: Facial recognition on public training centre trainees violates privacy norms, requires large biometric enrollment databases, creates high vulnerability under India's DPDP Act, and fails with varying camera angles and lighting. Periodic aggregate headcount using YOLO26 achieves compliance auditing without individual surveillance.*

2. **Q: Does visual detection mean equipment is working?**  
   *A: No. We explicitly state in our SRS and UI: visual presence detection only establishes apparent visual availability. It does not certify electrical or mechanical operability, which requires physical inspection.*

3. **Q: What if the CCTV is offline or low resolution?**  
   *A: The system flags missing or corrupt video as `INSUFFICIENT DATA` rather than a compliance failure, preventing false penalties against centres experiencing technical faults.*
