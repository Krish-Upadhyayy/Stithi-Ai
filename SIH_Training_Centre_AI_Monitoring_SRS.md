# Software Requirements Specification (SRS)
## AI-Powered, Privacy-Preserving Training Centre Monitoring Prototype

**Version:** 1.0  
**Project Type:** Smart India Hackathon (SIH) Prototype  
**Status:** Prototype Scope  
**Primary Goal:** Demonstrate an end-to-end working system that uses camera snapshots, AI-based detection, physical attendance data, and admin-uploaded infrastructure data to identify compliance discrepancies.

---

## 1. Purpose

The system is a prototype for monitoring government-funded training/skilling centres using computer vision.

The prototype will:

1. Receive camera/video input from a training centre.
2. Extract periodic screenshots/frames rather than continuously transmitting full video.
3. Use a tuned YOLOv8-based face/person detection pipeline for anonymous attendance estimation.
4. Use a separate YOLO-based infrastructure detection pipeline.
5. Compare AI observations with physically verified attendance and admin-uploaded sanctioned infrastructure data.
6. Generate discrepancy alerts with evidence snapshots.
7. Display centre-wise compliance information on a web dashboard.

The prototype is not intended to be a production government deployment.

---

## 2. Problem Statement

Periodic physical inspections of geographically distributed training centres can miss discrepancies between reported attendance and actual physical presence. Approved infrastructure may also be unavailable, missing, or not visible during inspections.

The proposed system turns passive camera footage into actionable compliance information while avoiding facial identification.

---

## 3. Scope

### 3.1 In Scope

- Admin login/basic authentication.
- Training centre creation/selection.
- Physical attendance count entry.
- Camera/video input.
- Periodic screenshot extraction.
- Initial + periodic snapshots during a monitoring session.
- YOLOv8-Face based detection adapted/tuned for the project.
- Anonymous counting of visible people.
- Multiple attendance observations and an aggregate observed count.
- Configurable attendance tolerance.
- Admin Excel upload for expected infrastructure.
- Excel validation.
- Separate YOLO infrastructure detection pipeline.
- Prototype infrastructure classes such as Chair, Computer, Machine and Workbench, subject to dataset availability.
- Expected vs detected infrastructure comparison.
- Alert generation.
- Evidence snapshot associated with alerts.
- Alert states: Pending, Verified, False Positive.
- Centre dashboard.
- Basic compliance summary.
- Basic model evaluation metrics.
- Privacy-preserving design.

### 3.2 Out of Scope

- Facial recognition or student identity matching.
- Student names/biometric database.
- Government API integration.
- Mobile application.
- SMS/WhatsApp notifications.
- Complex role-based access control.
- Multi-camera synchronization.
- Advanced live-stream analytics dashboard.
- Production-grade distributed infrastructure.
- Automated government reporting.
- Predictive analytics.
- Blockchain.
- Full mechanical verification of whether equipment is operational.
- Large-scale cloud deployment.

---

## 4. Users

### 4.1 Admin
- Manage centres.
- Upload sanctioned infrastructure Excel.
- Configure basic monitoring parameters.
- View dashboard and alerts.

### 4.2 Centre/Authorized User
- Enter the physically verified attendance count.
- Start a monitoring session.
- View monitoring result in the prototype.

### 4.3 Reviewer
For the prototype, reviewer functionality is represented through alert status actions:
- Pending
- Verified
- False Positive

---

## 5. High-Level Architecture

```text
Camera / Recorded Video
        |
        v
OpenCV Frame Capture
        |
        +----------------------+
        |                      |
        v                      v
Attendance Pipeline     Infrastructure Pipeline
        |                      |
YOLOv8-Face / Person      Custom YOLO Model
Detection                    |
        |                      |
Person Count             Asset Counts
        |                      |
        +----------+-----------+
                   |
                   v
          Compliance Engine
                   ^
                   |
       +-----------+-----------+
       |                       |
Physical Attendance     Admin Excel Inventory
       |                       |
       +-----------+-----------+
                   |
                   v
          Discrepancy Engine
                   |
                   v
             Alert Engine
                   |
                   v
            Spring Boot API
                   |
                   v
               MySQL
                   |
                   v
          Next.js Dashboard
```

---

## 6. Technology Requirements

### Frontend
- Next.js
- React
- TypeScript
- Tailwind CSS
- Recharts where charts are needed

### Backend
- Java
- Spring Boot
- REST APIs
- Apache POI for Excel processing

### AI/Computer Vision
- Python
- Ultralytics YOLO
- PyTorch
- OpenCV
- NumPy
- Pandas where useful

### Models
1. YOLOv8-Face repository as the starting point for attendance detection.
2. A separate custom YOLO model for infrastructure detection.

### Database
- MySQL

### Development
- Git
- GitHub
- IntelliJ IDEA
- VS Code
- Postman

### Optional/Prototype Support
- Docker
- ByteTrack only if tracking becomes necessary.

---

## 7. Functional Requirements

### FR-01 Authentication
The system shall provide basic admin authentication for the prototype.

### FR-02 Centre Management
The admin shall be able to create/view/select training centres.

Minimum centre information:
- Centre ID
- Centre name
- Location text
- Status

### FR-03 Physical Attendance
The authorized user shall enter one physically verified attendance count for a monitoring session.

Fields:
- Centre
- Date
- Session
- Physical attendance count
- Timestamp

The system shall not require student identities.

### FR-04 Camera/Video Input
The system shall support prototype camera/video input.

Priority:
1. Recorded video file for reliable demo.
2. Camera/RTSP input where available.

The architecture should allow camera input to be replaced without redesigning the compliance layer.

### FR-05 Snapshot Extraction
The system shall:
- Capture an initial snapshot when monitoring begins.
- Capture periodic snapshots during the monitoring session.
- Store timestamps.
- Associate each snapshot with a centre and monitoring session.

The interval shall be configurable.

### FR-06 Attendance AI
The attendance pipeline shall:
- Receive a snapshot.
- Detect visible faces/people using the tuned YOLOv8-Face-based implementation.
- Count detections.
- Store count and confidence information.
- Avoid identity recognition.

The implementation must not create a student identity database.

### FR-07 Attendance Aggregation
The system shall collect multiple AI observations and produce an observed attendance estimate.

A prototype aggregation method may use the median of valid snapshot counts to reduce the impact of an unusually low/high frame.

Example:

```text
38, 39, 37, 38, 40
Median = 38
```

The aggregation method shall be configurable in code.

### FR-08 Attendance Comparison
The system shall compare:
- Physical attendance
- AI observed attendance

The system shall calculate:

```text
difference = physical_attendance - observed_attendance
absolute_difference = abs(difference)
```

A configurable tolerance shall determine whether the result is normal or a discrepancy.

### FR-09 Infrastructure Excel Upload
The admin shall upload an Excel file containing expected/sanctioned infrastructure.

Minimum fields:

| Field | Required |
|---|---|
| Centre ID | Yes |
| Asset Type | Yes |
| Required Quantity | Yes |

Optional:
- Zone
- Description

### FR-10 Excel Validation
The system shall reject or clearly report:
- Missing required columns.
- Blank centre ID.
- Blank asset type.
- Invalid/non-numeric quantity.
- Negative quantity.
- Invalid centre reference.

### FR-11 Infrastructure AI
A separate YOLO model shall detect prototype infrastructure classes.

Initial candidate classes:
- Chair
- Computer
- Machine
- Workbench

Final classes depend on available training data and actual centre requirements.

### FR-12 Infrastructure Comparison
The system shall compare expected quantities from Excel with detected quantities.

Example:

```text
Expected Machines = 10
Detected Machines = 8
Difference = 2
```

The system shall use wording such as:
- "Detected"
- "Observed"
- "Not detected in evidence"

It shall not claim definitive mechanical failure merely from a visual detection.

### FR-13 Alerts
The system shall create an alert when:
- Attendance exceeds the configured discrepancy threshold.
- Expected infrastructure is materially different from observed/detected infrastructure.

Alert fields:
- Centre
- Alert type
- Severity
- Description
- Timestamp
- Related snapshot
- Expected value
- Observed value
- Status

### FR-14 Alert Status
Each alert shall support:
- Pending
- Verified
- False Positive

### FR-15 Evidence
Alerts shall display the relevant snapshot/evidence image.

Where practical, visible faces should be anonymized/blurred before evidence is stored or displayed.

### FR-16 Dashboard
The dashboard shall show:
- Total centres.
- Centre status.
- Attendance status.
- Infrastructure status.
- Alert count.
- Recent alerts.
- Evidence.

### FR-17 Centre Details
Selecting a centre shall show:
- Physical attendance.
- AI observed attendance.
- Attendance difference.
- Infrastructure expected vs observed.
- Alerts.
- Evidence snapshots.
- Basic monitoring history.

### FR-18 Evaluation
The prototype shall provide or document actual measured AI evaluation metrics:
- Precision
- Recall
- F1
- mAP where applicable
- Counting error/MAE

No fabricated accuracy numbers shall be displayed.

---

## 8. Non-Functional Requirements

### NFR-01 Privacy
- No face recognition.
- No student identity matching.
- Use anonymous presence/count detection.
- Avoid unnecessary storage/transmission of raw continuous video.
- Evidence should be anonymized where practical.

### NFR-02 Low Bandwidth
The design shall prioritize periodic snapshots and metadata rather than continuous cloud video upload.

### NFR-03 Accuracy
Model accuracy on representative classroom/workshop footage is more important than adding numerous UI features.

### NFR-04 Maintainability
Frontend, backend and AI service shall be separated.

### NFR-05 Usability
A judge should be able to complete the core demo flow without technical intervention.

### NFR-06 Explainability
Every alert should have:
- Expected value
- Observed value
- Difference
- Timestamp
- Evidence snapshot

---

## 9. Data Model

Suggested core entities:

### User
- id
- name
- email
- password_hash
- role

### Centre
- id
- centre_code
- name
- location
- status

### Camera
- id
- centre_id
- name
- source_type
- source_path_or_url
- active

### MonitoringSession
- id
- centre_id
- physical_attendance
- start_time
- end_time
- status

### Snapshot
- id
- session_id
- timestamp
- path/url
- source

### AttendanceObservation
- id
- snapshot_id
- detected_count
- confidence_summary

### InventoryItem
- id
- centre_id
- asset_type
- required_quantity
- zone

### InfrastructureObservation
- id
- snapshot_id
- asset_type
- detected_quantity
- confidence_summary

### Alert
- id
- centre_id
- session_id
- type
- severity
- expected_value
- observed_value
- difference
- snapshot_id
- status
- created_at

---

## 10. Core API Areas

Prototype REST API areas:

```text
/auth
/centres
/cameras
/attendance
/sessions
/snapshots
/inventory
/ai
/alerts
/dashboard
```

The exact endpoint naming may be refined during implementation.

---

## 11. Prototype AI Workflow

### Attendance

```text
Video/Camera
    ↓
OpenCV
    ↓
Snapshot
    ↓
YOLOv8-Face-based detector
    ↓
Detected faces/people
    ↓
Count
    ↓
Store observation
    ↓
Aggregate multiple observations
    ↓
Compare with physical attendance
```

### Infrastructure

```text
Snapshot
    ↓
Infrastructure YOLO
    ↓
Asset detections
    ↓
Count by class
    ↓
Compare with Excel baseline
    ↓
Generate discrepancy
```

---

## 12. Accuracy Strategy

The GitHub YOLOv8-Face implementation is a starting point, not the final model.

Work shall include:
1. Run baseline model.
2. Test on representative images.
3. Identify failure cases.
4. Collect/prepare project-specific data.
5. Annotate data.
6. Fine-tune.
7. Validate on a held-out test set.
8. Compare baseline vs tuned model.
9. Integrate only after acceptable prototype performance.

Dataset conditions should include:
- Different camera angles.
- Different lighting.
- Occlusion.
- Crowded classrooms.
- Sparse classrooms.
- Empty classrooms.
- Low-resolution frames.
- Students looking in different directions.

---

## 13. Error Handling

The system shall handle:
- Invalid Excel.
- Missing camera/video.
- Unreadable frame.
- AI model failure.
- No detections.
- Low-confidence detections.
- Database/API failure.

An AI failure should not silently appear as a valid attendance result.

---

## 14. Prototype Acceptance Criteria

The prototype is considered successful when a demo can:

1. Select a training centre.
2. Enter physical attendance.
3. Upload centre inventory Excel.
4. Start monitoring using a recorded video or camera source.
5. Automatically extract snapshots.
6. Run attendance detection.
7. Run infrastructure detection.
8. Produce counts.
9. Compare counts with baseline data.
10. Generate an alert when appropriate.
11. Show the alert on the dashboard.
12. Show supporting evidence.
13. Change alert status to Verified or False Positive.
14. Demonstrate privacy-preserving counting.
15. Report real measured model evaluation results.

---

## 15. Future Scope

Not required for the prototype:
- Multi-camera synchronization.
- Government database/API integration.
- Edge hardware deployment.
- Advanced tracking.
- Camera tamper detection.
- Equipment utilization analysis.
- Automated notifications.
- Large-scale deployment.
- Advanced role management.
- Historical analytics and trend prediction.

---

## 16. Guiding Principle

> Build a small, complete, accurate proof of concept rather than a large collection of incomplete features.

The AI detection pipeline and the end-to-end compliance workflow are the highest-priority components.
