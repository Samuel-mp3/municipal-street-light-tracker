# Municipal Street Light Fault Register & Repair Tracker

> **Problem Statement**: Municipal street light failures are logged manually without central tracking, leading to unrecorded repair dates, repeat complaints for identical poles, and zero visibility into high-failure wards.
> **Objective**: Build an end-to-end municipal complaint register and predictive tracking application that records street light faults, calculates repair turnaround times on the server, predicts repair delay hazards using Machine Learning, and presents real-time section analytics.

---

## Technology Stack

- **Frontend**: HTML5, CSS3 (Custom Civic Design System + Glassmorphism), Bootstrap 5, Font Awesome 6 Icons, JavaScript (ES6+), Chart.js 4
- **Backend**: Python 3.11+, Flask (Modular Architecture with Flask Blueprints)
- **Database**: SQLite3 with auto-migration and CSV seeding
- **Machine Learning**: `scikit-learn` (`RandomForestClassifier`), `pandas`, `numpy`, `pickle`
- **Containerization**: Docker (optimized multi-stage caching), Docker Compose

---

## 🌟 Level 2 On-Spot Assessment Changes (Completed)

### Change 1 — Added New Category / Class (8 Marks)
- **New Category Added**: `Solar Panel Breakdown` (7th Fault Category class added to `data/dataset.csv`).
- **Pipeline Retraining**: Re-ran preprocessing, `LabelEncoder` fitting, and model retraining without breaking.
- **Model Test Accuracy Achieved**: **95.65%**

### Change 2 — Model Abstention & Confidence Cut-Off (12 Marks)
- **Cut-Off Threshold**: Set at **65.0%** confidence.
- **Abstention Mechanism**: When prediction probability is below the 65.0% cut-off, the model says **"I am not sure — Set Aside for Human Verification"** instead of guessing.
- **Borderline Case Handling**: Borderline inputs are automatically set aside with an Amber UI badge and warning banner for human expert verification.

---

## Installation & Setup Instructions

### Prerequisites
- Python 3.10 or higher
- Git
- Docker & Docker Compose *(optional for container deployment)*

### Option 1: Local Python Environment

1. **Clone Repository & Navigate to Workspace**:
   ```bash
   git clone https://github.com/your-org/municipal-street-light-tracker.git
   cd municipal-street-light-tracker
   ```

2. **Create Virtual Environment & Install Dependencies**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate

   pip install -r requirements.txt
   ```

3. **Train Machine Learning Model & Seed Database**:
   ```bash
   python train_model.py
   ```

4. **Launch Flask Server**:
   ```bash
   python app.py
   ```
   *Access the web dashboard at `http://127.0.0.1:5000`*

---

### Option 2: Docker Containerization

1. **Build and Run with Docker Compose**:
   ```bash
   docker-compose up --build
   ```
   *The containerized application will start on `http://localhost:5000`*

---

## Default Login Credentials

- **Username**: `admin`
- **Password**: `admin123`

---

## Folder Structure

```
municipal_street_light_tracker/
├── app.py                     # Main Flask Application Entry Point
├── config.py                  # Application Configuration Settings
├── database.py                # SQLite Database Helper & Derived Metric Logic
├── train_model.py             # ML Model Training & Preprocessing Pipeline
├── requirements.txt           # Python Package Dependencies
├── Dockerfile                 # Layer-cached Docker Containerization Script
├── docker-compose.yml         # Multi-container Deployment Manifest
├── .dockerignore              # Docker Ignore Exclusions
├── .env.example               # Environment Configuration Template
├── README.md                  # Complete System Documentation
├── data/
│   ├── dataset.csv            # Seed Dataset (100+ Records with Awkward/Dirty Data)
│   ├── schema.sql             # Relational Database Schema
│   └── model.pkl              # Serialized ML Classifier & Encoders
├── blueprints/
│   ├── __init__.py
│   ├── auth.py                # Admin Authentication Blueprint
│   ├── dashboard.py           # Metrics & Chart APIs Blueprint
│   ├── complaints.py          # Complaint CRUD & Validation Blueprint
│   ├── prediction.py          # ML Prediction Endpoint Blueprint
│   └── reports.py             # Ward & Monthly Analytics Blueprint
├── templates/
│   ├── base.html              # Core Civic Layout Template
│   ├── login.html             # Admin Sign-In Screen
│   ├── dashboard.html          # Executive Dashboard View
│   ├── complaint_register.html# Server-Validated Complaint Form
│   ├── complaint_list.html    # Filterable Datatable View
│   ├── complaint_details.html # Complaint Dossier & Edit View
│   ├── prediction.html        # Interactive ML Risk Predictor View
│   ├── reports.html           # Ward-wise & Monthly Reports View
│   ├── 404.html               # Not Found Error Page
│   └── 500.html               # Server Error Page
└── static/
    ├── css/
    │   └── style.css          # Custom Civic Design Tokens & Styling
    └── js/
        ├── main.js            # Sidebar & Toast Animations
        ├── dashboard.js       # Chart.js Executive Graphs
        └── reports.js         # Chart.js Dynamic Report Visualizations
```

---

## Database Schema & Data Dictionary

### Table: `complaints`

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | System internal primary key |
| `fault_id` | TEXT | UNIQUE, NOT NULL | Auto-generated ID (`FLT-2026-XXXX`) |
| `pole_id` | TEXT | NOT NULL | Physical pole identifier tag (e.g. `POL-104`) |
| `ward` | TEXT | NOT NULL | Municipal administrative ward (`Ward 1` to `Ward 10`) |
| `street` | TEXT | NOT NULL | Street name / landmark |
| `reported_date` | DATE | NOT NULL | Date complaint was logged |
| `fault_type` | TEXT | NOT NULL | Fault category (e.g. `Transformer Failure`, `Bulb Replacement`) |
| `status` | TEXT | NOT NULL DEFAULT 'Pending' | Repair state (`Pending`, `In Progress`, `Repaired`, `Rejected`) |
| `repaired_date` | DATE | NULLABLE | Date physical repair was completed |
| `need_attention`| INTEGER| DEFAULT 0 | Historical outcome tag for ML training |
| `priority` | TEXT | DEFAULT 'Medium' | Calculated priority (`Critical`, `High`, `Medium`) |

---

## How Derived Figures Are Calculated

Every calculated metric is computed **strictly on the backend server** in `database.py` to ensure consistency:

1. **Pending Days (`pending_days`)**:
   - **For Repaired Complaints**:
     $$\text{Pending Days} = \text{Repaired Date} - \text{Reported Date}$$
   - **For Pending / In Progress Complaints**:
     $$\text{Pending Days} = \text{Current Date} - \text{Reported Date}$$
   - **Edge Cases**: Returns `0` if dates are invalid or missing.

2. **Average Repair Time (`avg_repair_time`)**:
   - Calculated across all resolved complaints:
     $$\text{Avg Repair Time} = \frac{\sum_{i=1}^{N} \text{Pending Days}_i}{N}$$

---

## Machine Learning Model Architecture

- **Prediction Target**: `Need Immediate Attention` ($1$ = High Risk / Delayed Repair Likelihood, $0$ = Standard Repair Priority).
- **Strict Data Leakage Prevention**: Features are strictly restricted to inputs available at the exact moment a complaint is logged:
  - `ward` (Encoded via `LabelEncoder`)
  - `fault_type` (Encoded via `LabelEncoder`)
  - `reported_month` (Extracted from `reported_date`)
  - `reported_dayofweek` (Extracted from `reported_date`)
  - `historical_pole_complaints` (Repeat report frequency count for `pole_id`)
- **Classifier**: `RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)`
- **Confidence Scoring & Alerting**:
  - Probability score computed via `clf.predict_proba()`
  - **Low-Confidence Alert**: If $\text{Confidence} < 65.0\%$, the UI displays:
    > *"Prediction confidence is low. Manual verification recommended."*

---

## Sample Screenshots Description

1. **Login Page (`/login`)**:
   - Clean government portal layout with glassmorphism admin card, username/password fields, and quick demo login credentials hint.

2. **Executive Dashboard (`/`)**:
   - Top metric summary cards displaying Total Complaints, Pending Complaints, Repaired Complaints, and Server-Calculated Average Repair Time.
   - Interactive Chart.js graphs showing Ward Distribution and Fault Category breakdown.
   - Actionable list of Urgent High-Risk Complaints needing immediate attention.

3. **Register Complaint (`/complaints/register`)**:
   - Form featuring auto-generated `Fault ID`, pole tag input, ward selector, street field, reported date picker, and server-side validation error alerts.

4. **Complaint Register Datatable (`/complaints`)**:
   - Full master datatable with search bar, multi-select filters (Ward, Fault Type, Status), sortable column headers, derived `Pending Days` badges, pagination controls, and CSV export.

5. **Complaint Dossier (`/complaints/<id>`)**:
   - Detailed inspection card showing repeat report history count for the pole, location details, repair status workflow, and server-calculated elapsed pending days box.

6. **ML Delay Risk Predictor (`/prediction`)**:
   - Interactive ML evaluation tool. Displays prediction status badge, animated confidence score progress bar, feature driver weights, and low-confidence warning alert banners.

7. **Reports & Analytics (`/reports`)**:
   - Tabbed reporting suite containing Ward-wise tables, Fault Type frequency matrices, Monthly trend curves, and print-ready PDF export options.

---

## Future Improvements

1. Integration with GIS mapping (Leaflet / OpenStreetMap) for spatial fault heatmaps on municipal maps.
2. SMS / Email alerts to municipal field electrical engineers when a critical transformer fault is logged.
3. Mobile-first PWA for field repair technicians to update repair status with photographic proof.
