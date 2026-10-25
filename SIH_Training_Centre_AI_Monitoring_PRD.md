# Product Requirements Document (PRD)
## AI-Powered Training Centre Compliance Monitoring

### 1. Product Vision

Create a prototype that converts existing CCTV/video footage from government-funded training centres into actionable compliance information.

The product estimates anonymous physical attendance, observes sanctioned infrastructure, compares observations with physically verified/admin-provided records, and raises evidence-backed alerts.

### 2. Product Promise

**From passive CCTV to actionable compliance intelligence — without identifying students.**

The prototype should prove three things:

1. AI can estimate physical presence from camera snapshots.
2. AI can observe relevant infrastructure.
3. The system can compare AI observations against trusted centre data and surface discrepancies.

---

# 3. Target Users

## Admin
Uploads centre infrastructure data and monitors centres.

## Authorized Centre User
Submits the physically verified attendance count and starts the monitoring session.

## Reviewer
For the prototype, reviews alerts through Pending, Verified and False Positive states.

---

# 4. Core User Journey

```text
Admin creates/selects Centre
        ↓
Admin uploads Inventory Excel
        ↓
Authorized user enters physical attendance
        ↓
Monitoring session starts
        ↓
Camera/video provides frames
        ↓
System extracts initial + periodic snapshots
        ↓
Attendance AI counts visible people
        ↓
Infrastructure AI detects assets
        ↓
Compliance engine compares results
        ↓
Alert generated if discrepancy is significant
        ↓
Dashboard shows result + evidence
        ↓
Reviewer marks alert Verified / False Positive
```

---

# 5. MVP / Prototype Features

## Feature 1 — Centre Dashboard

Display:
- Total centres.
- Centre status.
- Attendance status.
- Infrastructure status.
- Number of active alerts.

Do not build advanced analytics.

---

## Feature 2 — Physical Attendance

A simple form:

```text
Centre
Date
Session
Physical Attendance Count
```

No student names or IDs.

---

## Feature 3 — Camera/Video Monitoring

Prototype should support:
- Recorded video as the most reliable demo input.
- Camera/RTSP source where available.

The system captures:
- Initial snapshot.
- Periodic snapshots.

The interval should be configurable.

---

## Feature 4 — Attendance AI

Starting point:
**Yusepp/YOLOv8-Face**

The repository will be evaluated and tuned for classroom/CCTV conditions.

The output is:

```text
Detected count
Confidence information
Timestamp
Snapshot
```

No face identity recognition.

---

## Feature 5 — Infrastructure AI

Separate YOLO pipeline.

Prototype classes should remain limited to the assets necessary for the demonstration.

Example:

```text
Chair
Computer
Machine
Workbench
```

The actual class list is finalized after dataset inspection.

---

## Feature 6 — Inventory Excel

Admin uploads a simple Excel:

```text
Centre ID | Asset Type | Required Quantity | Zone
```

Example:

```text
C001 | Computer  | 20 | Classroom
C001 | Chair     | 40 | Classroom
C001 | Machine   | 10 | Workshop
C001 | Workbench | 5  | Workshop
```

---

## Feature 7 — Compliance Engine

### Attendance

```text
Physical Attendance
        vs
AI Observed Attendance
```

Calculate difference and apply configurable tolerance.

### Infrastructure

```text
Required Quantity
        vs
AI Detected Quantity
```

Generate discrepancy when the difference requires attention.

---

# 6. Alert Design

Alerts should be simple and evidence-backed.

### Attendance Alert

```text
Type: Attendance Discrepancy
Reported: 40
Observed: 28
Difference: 12
Evidence: Snapshot
Status: Pending
```

### Infrastructure Alert

```text
Type: Infrastructure Discrepancy
Asset: Machine
Expected: 10
Observed: 8
Difference: 2
Evidence: Snapshot
Status: Pending
```

### Alert statuses

- Pending
- Verified
- False Positive

---

# 7. Dashboard Structure

## Page 1 — Overview

Cards:

```text
Total Centres
Compliant
Attention Required
Active Alerts
```

Then a centre table.

## Page 2 — Centre Details

```text
Centre Information

Attendance
Physical Count
AI Observed Count
Difference
Status

Infrastructure
Asset
Expected
Observed
Status

Recent Alerts
```

## Page 3 — Alert Detail

```text
Alert Information
Expected vs Observed
Timestamp
Evidence Snapshot
Status Controls
```

---

# 8. AI Product Strategy

The prototype uses two independent computer-vision pipelines.

### Pipeline A — Attendance

```text
Snapshot
 ↓
Tuned YOLOv8-Face-based detector
 ↓
Count
 ↓
Aggregate observations
 ↓
Attendance estimate
```

### Pipeline B — Infrastructure

```text
Snapshot
 ↓
Custom infrastructure YOLO
 ↓
Class-wise counts
 ↓
Infrastructure observation
```

Separate pipelines allow each model to be optimized for its own task.

---

# 9. Privacy Product Requirement

The system must not require identity recognition.

It should answer:

> "How many people are visible?"

not:

> "Who are these people?"

Evidence images should be anonymized where practical.

Raw continuous video should not be unnecessarily transmitted to a central cloud system.

---

# 10. Low-Bandwidth Strategy

Instead of:

```text
CCTV → Continuous video → Cloud
```

prototype architecture demonstrates:

```text
CCTV
 ↓
Local/edge frame extraction
 ↓
Periodic snapshots
 ↓
AI processing
 ↓
Counts + metadata + evidence
 ↓
Backend/dashboard
```

The exact edge hardware is not required for the prototype.

---

# 11. Technology Stack

| Layer | Stack |
|---|---|
| Frontend | Next.js, React, TypeScript |
| UI | Tailwind CSS |
| Charts | Recharts |
| Backend | Java, Spring Boot |
| API | REST |
| Database | MySQL |
| Excel | Apache POI |
| AI service | Python |
| Computer Vision | OpenCV |
| Detection | Ultralytics YOLO |
| Attendance base | YOLOv8-Face GitHub repository |
| Infrastructure | Custom YOLO model |
| ML framework | PyTorch |
| Data processing | NumPy/Pandas |
| Version control | Git/GitHub |

---

# 12. Product Architecture

```text
                CAMERA / VIDEO
                      ↓
                   OpenCV
                      ↓
              PERIODIC SNAPSHOTS
                      ↓
             ┌────────┴────────┐
             ↓                 ↓
      ATTENDANCE AI       INFRASTRUCTURE AI
      YOLOv8-Face         Custom YOLO
             ↓                 ↓
        Person Count       Asset Counts
             ↓                 ↓
             └────────┬────────┘
                      ↓
              COMPLIANCE ENGINE
                 ↑          ↑
                 │          │
          Physical Count   Excel
                 │          │
                 └────┬─────┘
                      ↓
                  ALERTS
                      ↓
                SPRING BOOT
                      ↓
                   MYSQL
                      ↓
                  NEXT.JS
                  DASHBOARD
```

---

# 13. Prototype Success Metrics

The product should demonstrate:

### Technical
- Successful snapshot extraction.
- Successful AI inference.
- Reliable count output on test footage.
- Infrastructure detection.
- Successful Excel processing.
- Successful comparison.
- Alert generation.
- Evidence retrieval.

### ML
Report actual:
- Precision.
- Recall.
- F1.
- mAP where applicable.
- Counting MAE.

### Product
A judge should be able to understand the complete flow in under a few minutes.

---

# 14. Deliberately Excluded From MVP

Do not add these unless required later:

- Student identity recognition.
- Mobile app.
- SMS/WhatsApp.
- Government API.
- Complex permissions.
- Multi-camera synchronization.
- Advanced live streaming.
- Predictive analytics.
- Blockchain.
- Large-scale cloud architecture.
- Automated government reporting.

---

# 15. Definition of Done

The prototype is complete when:

> A user can select a centre, submit physical attendance, upload expected infrastructure, start monitoring from a video/camera source, see periodic snapshots processed by two AI pipelines, see observed counts, see comparison results, receive an evidence-backed alert when a discrepancy exists, and review the alert from the dashboard.

---

# 16. Product Principle

**Accuracy and complete workflow > number of features.**

Do not build a large dashboard around an untested AI model.

First make the AI pipeline work reliably, then connect it to the compliance engine and present it through a simple dashboard.
