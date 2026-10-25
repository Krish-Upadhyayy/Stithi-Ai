# YOLO26 Attendance Presence Dataset & Pipeline Specification

## 1. Scope & Objective
This dataset pipeline supports **anonymous aggregate presence estimation** for classroom and training-centre monitoring under the SIH Skill Monitoring System (SRS §FR-03 & PRD §9).

**Objective:**
> "Estimate how many people are visibly present in the training-centre snapshot."

**Strict Privacy Constraints:**
- **Zero student identity recognition**: No facial identification, facial embeddings, or biometric profiling.
- **Zero student metadata**: No names, student IDs, roll numbers, or personal records are collected or stored.
- **Single generic presence class**: `person` (Class ID `0`).

---

## 2. Directory Layout
```
datasets/attendance/
├── README.md               # Dataset documentation, privacy guidelines, and ingestion manual
├── data.yaml               # Ultralytics YOLO dataset configuration
├── raw/                    # Original CCTV video recordings and uncurated frame captures
├── cleaned/                # Curated and de-duplicated candidate frames
├── annotated/              # Exported annotations prior to train/val/test splitting
├── train/
│   ├── images/             # 70% Training split images
│   └── labels/             # YOLO format labels (*.txt)
├── val/
│   ├── images/             # 20% Validation split images (hyperparameter/threshold tuning)
│   └── labels/             # YOLO format labels (*.txt)
└── test/
    ├── images/             # 10% Strictly held-out test split (untouched during training)
    └── labels/             # Ground-truth labels (*.txt)
```

---

## 3. Dataset Variation & Coverage Matrix

The dataset reflects realistic deployment conditions across skilling training centres:

### Camera Geometries
- **Front-Facing Classroom View**: Wall-mounted or lectern-oriented cameras capturing student rows.
- **Side-Angle View**: Corner-mounted CCTV cameras showing diagonal perspectives.
- **Wide-Angle & Panoramic**: Ceiling-mounted wide focal length cameras with moderate peripheral distortion.
- **Varied Camera Heights**: 2.2m to 3.5m mounting heights.
- **Varying Distances**: Front row students (1–3m) vs back row attendees (8–15m).

### Lighting Conditions
- **Bright Daytime**: Natural ambient light through large windows.
- **Artificial Lighting**: Fluorescent tubes and warm LED overhead lights.
- **Low-Light / Twilight**: Sessions conducted with partial illumination or power transitions.
- **Uneven Lighting**: High-contrast areas (e.g. sunlight pools and shadowed back corners).
- **Backlighting**: Windows behind attendees casting silhouettes.

### Occupancy & Density
- **Empty Room**: 0 persons (crucial for verifying zero false-positive background response).
- **Sparse**: 1 to 5 persons.
- **Partially Occupied**: 6 to 15 persons.
- **Normally Occupied**: 16 to 30 persons.
- **Crowded / Dense**: 30+ attendees with adjacent desk seating.

### Human Appearance & Poses
- **Poses**: Seated at desks, standing at podiums, walking between aisles.
- **Orientations**: Front-facing, side-profile, and back-facing individuals.
- **Occlusions**: Partially visible bodies behind monitors, desks, or adjacent classmates.
- **Attire**: Diverse attire, head coverings, uniforms, and casual wear.

### Video / Image Quality
- **High Resolution**: 1080p (1920×1080) clean frames.
- **Compressed CCTV**: Typical RTSP stream frames (720p, 480p, H.264 compression artifacts).
- **Motion Blur**: Real-world transient motion during movement.

---

## 4. Ethical Compliance & Data Privacy

1. **Permitted Data Sources**:
   - Consent-based physical snapshots taken at authorized training centres.
   - Publicly available, ethically licensed CCTV classroom datasets (e.g., CC-BY / Open Access research datasets).
2. **De-identification**:
   - Faces are treated purely as spatial bounding boxes for presence counting.
   - Annotations never correlate a box with any human identity.
3. **Storage Security**:
   - Raw image data and labels are excluded from Git version control via `.gitignore`.
   - Access is restricted to authorized ML pipelines and administrative reviewers.

---

## 5. Annotation Specification

### Standard YOLO Format
Annotations use one `.txt` file per image with matching basename (`<image_id>.txt` alongside `<image_id>.jpg`):

```
<class_id> <x_center> <y_center> <width> <height>
```
All coordinates are normalized relative to image dimensions `[0.0, 1.0]`:
- `class_id`: Always `0` (`person`)
- `x_center`: Center X coordinate / image_width
- `y_center`: Center Y coordinate / image_height
- `width`: Bounding box width / image_width
- `height`: Bounding box height / image_height

---

## 6. Annotation Tool Integration (CVAT / Roboflow)

The pipeline ingests standard YOLO exports:

### CVAT (Computer Vision Annotation Tool)
1. Create a task with label `person`.
2. Annotate bounding boxes around visible human presences.
3. Export Annotations -> **YOLO 1.1**.
4. Unpack into `datasets/attendance/annotated/`.

### Roboflow
1. Upload classroom frames and define single class `person`.
2. Export dataset format -> **YOLOv8 / Ultralytics YOLO**.
3. Place files in `datasets/attendance/train`, `val`, and `test`.

---

## 7. Data Leakage Prevention Rules

**Crucial Mandate:**
Splits are partitioned strictly at the **session / video / camera level**, never by adjacent temporal video frames.

- **Incorrect Split (Leakage)**:
  - Video A 00:01 → train
  - Video A 00:02 → val
  - Video A 00:03 → test
- **Correct Split (Zero Leakage)**:
  - Session 101 (Centre Alpha, Morning) → `train/`
  - Session 102 (Centre Alpha, Afternoon) → `train/`
  - Session 103 (Centre Beta, Morning) → `val/`
  - Session 104 (Centre Gamma, Wide Angle) → `test/`

The validation script `scripts/attendance/validate_dataset.py` verifies both filename collisions and session prefix overlaps.
