# Therapist Matcher

[![Python 3.x](https://img.shields.io/badge/python-3.x-blue.svg)](https://www.python.org/) [![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B.svg)](https://streamlit.io/)

**Match patients to the right therapist. Fast.**

A schedule-aware matching engine that filters therapists by insurance, specialties, modality, location, and availability—so intake staff can find the best fit in seconds instead of scrolling spreadsheets.

---

## What It Does

Paste a patient inquiry or set filters. Get ranked matches with **exact** (all criteria met) and **near** (1–2 differences) results. See day-by-day schedules, open slots, and a calendar view with real dates—then drill into times when multiple therapists are available on the same day.

| Feature | Description |
|--------|-------------|
| **Smart parsing** | Paste email/text → auto-extract insurance, conditions, modality, location, age |
| **Exact + near matches** | Exact = all criteria met. Near = close fits with clear miss reasons |
| **Schedule filtering** | Preferred days (Mon–Fri) and time of day (Morning / Afternoon / Evening) |
| **Calendar view** | Exact dates, week navigation, expandable slots for multiple therapists |
| **Visual differentiation** | ✓ Exact match vs ~ Near match in calendar and list |
| **IntakeQ-ready** | Designed for Phase 2: select therapist/date/time → push booking to IntakeQ |

---

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Filters & Criteria

| Filter | Options |
|--------|---------|
| Patient Age | 0–100 (or skip) |
| Insurance | Any, Straight Medicaid, Medicare, Fidelis, Healthfirst, NWD, BCBS, Cigna, Optum, Aetna, 1199 |
| Conditions | Anxiety, trauma, OCD, ADHD, depression, couples, substance use, eating disorders, autism, LGBTQ+, bipolar, BPD, grief, stress, dissociation, relationships, self-esteem |
| Modality | Any, In-Person Only, Telehealth Only |
| Location | Commack, Jericho, Ronkonkoma (when In-Person) |
| EMDR | Yes / No |
| Preferred Days | Mon–Fri (multiselect) |
| Preferred Time | Morning (9–12), Afternoon (12–5), Evening (5pm+), Any |

---

## Time Ranges

| Time of Day | Range |
|-------------|-------|
| **Morning** | 9:00 AM – 11:59 AM |
| **Afternoon** | 12:00 PM – 4:59 PM |
| **Evening** | 5:00 PM onwards |

---

## Project Structure

```
therapist-matcher/
├── app.py           # Streamlit app + matching logic
├── therapists.csv   # Therapist roster (insurance, schedule, conditions)
├── requirements.txt
└── README.md
```

---

## Phase Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 1.5** | ✅ Current | Stub availability slots, calendar view, preferred schedule filter |
| **Phase 2** | 🔜 Coming | Real-time IntakeQ availability, booking push to IntakeQ |

---

## Data

Therapist data lives in `therapists.csv`. Open slots are **stub data** (deterministic per therapist+day); Phase 2 will replace these with live IntakeQ availability.

---

## Tech Stack

- **Streamlit** – Web UI
- **Pandas** – Data + filtering
- **Python 3.x** – Backend logic
