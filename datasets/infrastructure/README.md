# YOLO26 Infrastructure AI Dataset & Pipeline Specification

## 1. Scope & Objective
This dataset pipeline supports **sanctioned infrastructure/asset detection and count estimation** in skill training centres (SRS §FR-04 & PRD §10).

**Primary Question:**
> "What approved infrastructure/assets are visibly present in the monitoring snapshots, and approximately how many are visible?"

**Strict Architectural & Operational Constraints:**
- **Zero Functionality Claim**: Visual AI establishes apparent visual presence and count only. Normal CCTV frames cannot establish whether equipment is mechanically or electrically operational.
- **Strict Decoupling**: Completely independent from Attendance AI. Model weights, datasets, classes, and evaluation pipelines must never be conflated.
- **Privacy Assurance**: Detection targets physical furniture and equipment only. Zero face recognition, biometric tracking, or student identification.

---

## 2. Directory Layout
```
datasets/infrastructure/
├── README.md               # Pipeline documentation, annotation standards, and leakage guidelines
├── data.yaml               # Ultralytics YOLO26 dataset definition
├── raw/                    # Raw CCTV frames and training centre video captures
├── cleaned/                # De-duplicated and validated frames
├── annotated/              # Candidate annotations prior to split
├── train/
│   ├── images/             # 70% Training split images
│   └── labels/             # Normalized YOLO format labels (*.txt)
├── val/
│   ├── images/             # 20% Validation split images (hyperparameter tuning)
│   └── labels/             # Normalized YOLO format labels (*.txt)
└── test/
    ├── images/             # 10% Strictly held-out test split (untouched during training)
    └── labels/             # Ground truth test labels (*.txt)
```

---

## 3. Supported Infrastructure Classes & Annotation Guidelines

| Class ID | Class Name | Target Inventory Assets | Annotation Boundary Standard |
|---|---|---|---|
| `0` | `chair` | Office chairs, student chairs, revolving stools, wooden benches | Tight bounding box around entire chair including backrest and legs. Include partially occluded chairs if >25% visible. |
| `1` | `computer` | Desktop monitors, all-in-one PCs, laptops, workstations | Bounding box enclosing the monitor/screen and base. If separate tower is present adjacent, enclose both as one computer workstation or prioritize monitor. |
| `2` | `projector` | Ceiling-mounted projectors, tabletop digital projectors | Enclose projector body and lens casing. Ignore ceiling mounting pole. |
| `3` | `sewing machine` | Vocational sewing machines, stitching equipment | Enclose sewing machine head, needle arm, and mounting bed. |
| `4` | `workbench` | Electronics workbenches, carpentry tables, lab benches | Enclose bench table surface and visible framework. When multiple workbenches abut, segment into distinct units. |

---

## 4. Annotation Rules
1. **Format**: Standard YOLO 5-tuple per line:
   ```
   <class_id> <x_center> <y_center> <width> <height>
   ```
   Normalized to `[0.0, 1.0]` relative to image width and height.
2. **Multiple Instances**: If 10 computers are visible in a computer lab, create 10 separate annotations. Never group multiple computers into one bounding box.
3. **Occlusions**: If an asset is partially obstructed by a student or desk, annotate the visible portion plus estimated extent up to 50% occlusion. Exclude heavily occluded assets (<25% visible).
4. **Unsupported Equipment**: If an asset in the classroom does not belong to the supported classes (e.g. fire extinguisher, whiteboard), do NOT annotate it. It will be reported as `AI detection not configured`.

---

## 5. Dataset Diversity & CCTV Realistic Conditions
The dataset must reflect real-world CCTV conditions across Indian skilling centres:
- **Angles**: High wall mounts, corner angles, panoramic classroom views.
- **Lighting**: Direct sunlight, artificial fluorescent lighting, low light during power cuts/projector presentations.
- **Density**: Vacant labs (verifying 0 false positives) vs densely packed classrooms with chairs overlapping.
- **Resolution**: Both high-definition 1080p and typical compressed RTSP CCTV frames (720p/480p with compression artifacts).

---

## 6. Data Leakage Prevention Rules
Splitting across `train/`, `val/`, and `test/` must occur strictly at the **session / centre / camera level**:
- **Prohibited**: Frame `00:01` in `train` and frame `00:02` in `test` from the same recording.
- **Required**:
  - Centre Alpha Computer Lab → `train/`
  - Centre Beta Sewing Workshop → `val/`
  - Centre Gamma Mixed Training Lab → `test/`
