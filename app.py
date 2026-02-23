"""
Therapist Matching Engine - Phase 1.5
Explicit day-by-day modality breakdown, stub availability slots,
calendar view toggle (List / Calendar).
Phase 2: real-time IntakeQ availability.
"""

import hashlib
import re
import streamlit as st
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Therapist Matcher",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

INSURANCE_COLUMNS = {
    "str8_med": "Straight Medicaid",
    "medicare": "Medicare",
    "fidelis": "Fidelis",
    "healthfirst": "Healthfirst",
    "nwd": "NWD",
    "bcbs": "BCBS",
    "cigna": "Cigna",
    "optum": "Optum",
    "aetna": "Aetna",
    "eleven99": "1199",
}

NEARBY_LOCATIONS = {
    "Commack": ["Jericho"],
    "Jericho": ["Commack"],
    "Ronkonkoma": ["Commack"],
}

STATUS_ICONS = {
    "available": "🟢",
    "full": "🔴",
    "not_taking": "⛔",
}
STATUS_LABELS = {
    "available": "Taking New Clients",
    "full": "Currently Full",
    "not_taking": "Not Taking New Clients",
}

MODALITY_VALUES = {"In-Person", "Telehealth", "Hybrid"}
MODALITY_BADGE = {"In-Person": "🏢", "Telehealth": "💻", "Hybrid": "🔄"}

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
ALL_TIMES = ["9:00 AM", "10:00 AM", "11:00 AM", "12:00 PM",
             "1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM", "5:00 PM"]

KEYWORD_ALIASES = {
    "anxiety": ["anxiety", "anx", "anxious", "worry", "panic"],
    "depression": ["depression", "dep", "depressed", "depressive"],
    "trauma": ["trauma", "ptsd", "traumatic"],
    "ocd": ["ocd", "obsessive", "compulsive"],
    "adhd": ["adhd", "add", "attention deficit"],
    "couples": ["couples", "couple", "marriage", "marital"],
    "substance use": ["su", "substance", "addiction", "alcohol", "drinking", "drug"],
    "eating disorders": ["eating disorder", "ed", "anorexia", "bulimia", "binge"],
    "autism": ["autism", "asd", "autistic", "spectrum"],
    "self-esteem": ["self-esteem", "self esteem", "self worth"],
    "grief": ["grief", "loss", "bereavement", "passed away", "death"],
    "stress": ["stress", "stressed", "burnout"],
    "lgbtq+": ["lgbtq", "lgbtq+", "transgender", "nonbinary", "queer", "gay", "lesbian"],
    "bipolar": ["bipolar"],
    "bpd": ["bpd", "borderline"],
    "relationships": ["relationships", "relationship", "interpersonal"],
    "dissociation": ["dissociation", "disso", "dissociative"],
}


# ---------------------------------------------------------------------------
# Schedule helpers
# ---------------------------------------------------------------------------

def get_therapist_schedule(row: dict) -> dict:
    """
    Returns a dict mapping each workday to its modality.
    Example: {"Mon": "In-Person", "Tue": "Telehealth", "Wed": "In-Person", ...}
    - In-Person: in_person_days (or all weekdays if blank) -> In-Person
    - Telehealth: all weekdays -> Telehealth
    - Hybrid: in_person_days -> In-Person, remaining weekdays -> Telehealth
    """
    modality = row.get("modality", "Telehealth")
    raw = row.get("in_person_days", "") or ""
    in_person_days = [d.strip() for d in raw.split(",") if d.strip() in WEEKDAYS]

    schedule = {}
    if modality == "In-Person":
        work_days = in_person_days if in_person_days else WEEKDAYS
        for d in work_days:
            schedule[d] = "In-Person"
    elif modality == "Telehealth":
        for d in WEEKDAYS:
            schedule[d] = "Telehealth"
    elif modality == "Hybrid":
        for d in WEEKDAYS:
            schedule[d] = "In-Person" if d in in_person_days else "Telehealth"
    return schedule


def get_stub_slots(therapist_name: str, day: str) -> list:
    """
    Deterministic fake open time slots per therapist+day.
    Consistent across reruns — simulates IntakeQ Phase 2 data.
    """
    seed = int(hashlib.md5(f"{therapist_name}_{day}".encode()).hexdigest()[:8], 16)
    if seed % 5 == 0:
        return []
    count = (seed % 3) + 1
    start = seed % (len(ALL_TIMES) - count)
    return ALL_TIMES[start: start + count]


def get_all_stub_slots(row: dict) -> dict:
    """Returns {day: (modality, [slots])} for days that have open slots."""
    schedule = get_therapist_schedule(row)
    result = {}
    for day in WEEKDAYS:
        day_modality = schedule.get(day)
        if not day_modality:
            continue
        slots = get_stub_slots(row["therapist"], day)
        if slots:
            result[day] = (day_modality, slots)
    return result


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

@st.cache_data
def load_data() -> pd.DataFrame:
    csv_path = Path(__file__).parent / "therapists.csv"
    df = pd.read_csv(csv_path)

    for col in INSURANCE_COLUMNS.keys():
        df[col] = df[col].fillna("").astype(str).str.strip().str.lower() == "yes"

    df["emdr"] = df["emdr"].fillna("").astype(str).str.strip().str.lower() == "yes"
    df["min_age"] = pd.to_numeric(df["min_age"], errors="coerce").fillna(0).astype(int)
    df["modality"] = df["modality"].fillna("Telehealth").astype(str).str.strip()
    df["modality"] = df["modality"].apply(
        lambda v: v if v in MODALITY_VALUES else "Telehealth"
    )

    for col in ["conditions", "approaches", "exclusions", "location", "notes",
                "in_person_days", "last_updated", "updated_by"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    return df


# ---------------------------------------------------------------------------
# Inquiry Parser
# ---------------------------------------------------------------------------

def parse_inquiry(text: str) -> dict:
    text_lower = text.lower()
    extracted = {
        "insurance": "Any",
        "specialties": [],
        "require_emdr": False,
        "modality": "Any",
        "location": "Any",
        "patient_age": None,
    }

    ins_kw = {
        "medicare": "Medicare", "medicaid": "Straight Medicaid", "fidelis": "Fidelis",
        "healthfirst": "Healthfirst", "nwd": "NWD", "blue cross": "BCBS", "bcbs": "BCBS",
        "cigna": "Cigna", "optum": "Optum", "aetna": "Aetna", "1199": "1199",
        "united": "Optum", "unitedhealthcare": "Optum", "uhc": "Optum",
    }
    for kw, name in ins_kw.items():
        if kw in text_lower:
            extracted["insurance"] = name
            break

    found = []
    for canonical, aliases in KEYWORD_ALIASES.items():
        for a in aliases:
            if a in text_lower:
                found.append(canonical)
                break
    extracted["specialties"] = list(dict.fromkeys(found))

    if "emdr" in text_lower:
        extracted["require_emdr"] = True

    in_person = any(p in text_lower for p in ["in person", "in-person", "face to face", "office"])
    telehealth = any(p in text_lower for p in ["telehealth", "virtual", "online", "remote", "video"])
    if in_person and not telehealth:
        extracted["modality"] = "In-Person Only"
    elif telehealth and not in_person:
        extracted["modality"] = "Telehealth Only"

    for loc in ["commack", "jericho", "ronkonkoma"]:
        if loc in text_lower:
            extracted["location"] = loc.capitalize()
            if extracted["modality"] == "Any":
                extracted["modality"] = "In-Person Only"
            break

    for pattern in [r'(\d{1,2})\s*[-\s]?year[\s-]?old', r'(\d{1,2})\s*yo\b', r'age\s*(\d{1,2})']:
        m = re.search(pattern, text_lower)
        if m:
            age = int(m.group(1))
            if 5 <= age <= 100:
                extracted["patient_age"] = age
                break

    return extracted


# ---------------------------------------------------------------------------
# Matching Logic
# ---------------------------------------------------------------------------

def condition_matches(conditions: str, approaches: str, keywords: list) -> tuple:
    if not keywords:
        return True, []
    combined = (conditions + " " + approaches).lower()
    matched = []
    for kw in keywords:
        kw_lower = kw.strip().lower()
        if not kw_lower:
            continue
        if kw_lower in combined:
            matched.append(kw)
            continue
        for canonical, aliases in KEYWORD_ALIASES.items():
            if kw_lower in aliases or kw_lower == canonical:
                if any(a in combined for a in aliases) or canonical in combined:
                    matched.append(kw)
                    break
    return len(matched) == len([k for k in keywords if k.strip()]), matched


def has_exclusion_conflict(exclusions: str, notes: str, keywords: list) -> list:
    warnings = []
    excl_lower = exclusions.lower()
    notes_lower = notes.lower()
    if not excl_lower and "only" not in notes_lower:
        return warnings
    for kw in keywords:
        kw_lower = kw.strip().lower()
        for canonical, aliases in KEYWORD_ALIASES.items():
            if kw_lower in aliases or kw_lower == canonical:
                if any(a in excl_lower for a in aliases) or canonical in excl_lower:
                    warnings.append(f"Excludes: {canonical}")
                    break
    if "emdr" in notes_lower and "only" in notes_lower:
        if not any(k.strip().lower() == "emdr" for k in keywords):
            warnings.append("EMDR clients ONLY")
    if "nothing severe" in notes_lower:
        warnings.append("Does not treat severe presentations")
    return list(set(warnings))


def modality_matches(therapist_modality: str, requested: str) -> bool:
    if not requested or requested == "Any":
        return True
    if therapist_modality == "Hybrid":
        return True
    if requested == "In-Person Only":
        return therapist_modality == "In-Person"
    if requested == "Telehealth Only":
        return therapist_modality == "Telehealth"
    return True


def location_matches_therapist(therapist_location: str, requested: str) -> bool:
    if not requested or requested == "Any":
        return True
    if not therapist_location:
        return False
    therapist_locs = [l.strip() for l in therapist_location.split(",")]
    return requested in therapist_locs


def location_is_nearby(therapist_location: str, requested: str):
    if not requested or not therapist_location:
        return None
    therapist_locs = [l.strip() for l in therapist_location.split(",")]
    nearby = NEARBY_LOCATIONS.get(requested, [])
    for loc in therapist_locs:
        if loc in nearby:
            return loc
    return None


def score_therapist(row: dict, criteria: dict):
    miss_reasons = []

    status = row.get("availability_status", "available")
    if status == "permanently_closed":
        status = "not_taking"
    if criteria["hide_unavailable"] and status != "available":
        return None

    insurance = criteria["insurance"]
    if insurance and insurance != "Any":
        ins_col = [k for k, v in INSURANCE_COLUMNS.items() if v == insurance]
        if ins_col and not row.get(ins_col[0]):
            miss_reasons.append(f"Not in-network for {insurance}")

    if criteria["require_emdr"] and not row.get("emdr"):
        miss_reasons.append("Does not offer EMDR")

    patient_age = criteria.get("patient_age")
    if patient_age and row.get("min_age", 0) > 0:
        if patient_age < row["min_age"]:
            miss_reasons.append(f"Min age {row['min_age']}+ (patient is {patient_age})")

    requested_modality = criteria["modality"]
    therapist_modality = row.get("modality", "Telehealth")
    if not modality_matches(therapist_modality, requested_modality):
        miss_reasons.append(f"Modality: {therapist_modality} (needs {requested_modality})")

    location = criteria["location"]
    if requested_modality == "In-Person Only" and location and location != "Any":
        if therapist_modality in ("In-Person", "Hybrid"):
            if not location_matches_therapist(row.get("location", ""), location):
                nearby = location_is_nearby(row.get("location", ""), location)
                if nearby:
                    miss_reasons.append(f"Nearby location: {nearby} (not {location})")
                else:
                    miss_reasons.append(f"Not in {location}")

    specialties = criteria["specialties"]
    cond_match, matched_kws = condition_matches(
        row.get("conditions", ""), row.get("approaches", ""), specialties
    )
    if specialties and not cond_match:
        unmatched = [k for k in specialties if k not in matched_kws]
        miss_reasons.append(f"Missing: {', '.join(unmatched)}")

    warnings = has_exclusion_conflict(
        row.get("exclusions", ""), row.get("notes", ""), specialties
    )

    result = dict(row)
    result["matched_keywords"] = matched_kws
    result["warnings"] = warnings
    result["miss_reasons"] = miss_reasons
    result["is_exact_match"] = len(miss_reasons) == 0
    result["miss_count"] = len(miss_reasons)
    result["match_score"] = len(matched_kws) - len(miss_reasons)
    return result


def filter_and_rank(df: pd.DataFrame, criteria: dict) -> tuple:
    exact, near = [], []
    for _, row in df.iterrows():
        result = score_therapist(row.to_dict(), criteria)
        if result is None:
            continue
        if result["is_exact_match"]:
            exact.append(result)
        elif result["miss_count"] <= 2:
            near.append(result)

    exact_df = pd.DataFrame(exact)
    near_df = pd.DataFrame(near)

    if not exact_df.empty:
        exact_df = exact_df.sort_values("match_score", ascending=False)
    if not near_df.empty:
        near_df = near_df.sort_values(["miss_count", "match_score"], ascending=[True, False])

    return exact_df, near_df


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def render_sidebar(defaults: dict = None) -> dict:
    if defaults is None:
        defaults = {}

    st.sidebar.markdown("## Patient Criteria")
    st.sidebar.markdown("---")

    age_val = defaults.get("patient_age") or 0
    patient_age = st.sidebar.number_input(
        "Patient Age", min_value=0, max_value=100, value=age_val, step=1,
        help="Enter 0 to skip.",
    )

    ins_options = ["Any"] + list(INSURANCE_COLUMNS.values())
    default_ins = defaults.get("insurance", "Any")
    ins_idx = ins_options.index(default_ins) if default_ins in ins_options else 0
    insurance = st.sidebar.selectbox("Insurance", ins_options, index=ins_idx)

    default_spec = ", ".join(defaults.get("specialties", []))
    spec_input = st.sidebar.text_input(
        "Conditions / Presenting Concerns",
        value=default_spec,
        placeholder="e.g. anxiety, trauma, OCD",
    )
    specialties = [s.strip() for s in spec_input.split(",") if s.strip()] if spec_input else []

    require_emdr = st.sidebar.checkbox("Requires EMDR", value=defaults.get("require_emdr", False))

    mod_options = ["Any", "In-Person Only", "Telehealth Only"]
    default_mod = defaults.get("modality", "Any")
    mod_idx = mod_options.index(default_mod) if default_mod in mod_options else 0
    modality = st.sidebar.radio("Modality", mod_options, index=mod_idx)
    st.sidebar.caption("Hybrid therapists match both.")

    location = "Any"
    if modality == "In-Person Only":
        loc_options = ["Any", "Commack", "Jericho", "Ronkonkoma"]
        default_loc = defaults.get("location", "Any")
        loc_idx = loc_options.index(default_loc) if default_loc in loc_options else 0
        location = st.sidebar.selectbox("Location", loc_options, index=loc_idx)

    st.sidebar.markdown("---")
    st.sidebar.markdown("#### Preferred Schedule")
    st.sidebar.caption("Phase 2 — IntakeQ integration")
    st.sidebar.multiselect(
        "Preferred Days",
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        disabled=True,
    )
    st.sidebar.selectbox(
        "Preferred Time",
        ["Any", "Morning (before 12pm)", "Afternoon (12-5pm)", "Evening (after 5pm)"],
        disabled=True,
    )

    st.sidebar.markdown("---")
    hide_unavailable = st.sidebar.checkbox("Hide unavailable therapists", value=True)

    return {
        "patient_age": patient_age if patient_age > 0 else None,
        "insurance": insurance,
        "specialties": specialties,
        "require_emdr": require_emdr,
        "modality": modality,
        "location": location,
        "hide_unavailable": hide_unavailable,
    }


def build_schedule_label(row: dict) -> str:
    """
    Returns a clear, human-readable schedule string.

    In-Person:  "🏢 In-Person: Mon–Fri (Commack)"
    Telehealth: "💻 Telehealth: Mon–Fri"
    Hybrid:     "🏢 In-Person: Mon, Wed, Fri (Commack)  |  💻 Telehealth: Tue, Thu"
    """
    modality = row.get("modality", "Telehealth")
    location = row.get("location", "")
    schedule = get_therapist_schedule(row)

    ip_days = [d for d in WEEKDAYS if schedule.get(d) == "In-Person"]
    th_days = [d for d in WEEKDAYS if schedule.get(d) == "Telehealth"]

    def fmt_days(days):
        if days == WEEKDAYS:
            return "Mon–Fri"
        return ", ".join(days)

    if modality == "In-Person":
        loc = f" ({location})" if location else ""
        return f"🏢 In-Person: {fmt_days(ip_days)}{loc}"
    elif modality == "Telehealth":
        return f"💻 Telehealth: {fmt_days(th_days)}"
    elif modality == "Hybrid":
        loc = f" ({location})" if location else ""
        parts = []
        if ip_days:
            parts.append(f"🏢 In-Person: {fmt_days(ip_days)}{loc}")
        if th_days:
            parts.append(f"💻 Telehealth: {fmt_days(th_days)}")
        return "  |  ".join(parts)
    return modality


def render_therapist_card(row: dict, is_near_match: bool = False):
    status = row.get("availability_status", "available")
    if status == "permanently_closed":
        status = "not_taking"
    status_icon = STATUS_ICONS.get(status, "")
    status_label = STATUS_LABELS.get(status, status)

    schedule_label = build_schedule_label(row)
    accepted = [v for k, v in INSURANCE_COLUMNS.items() if row.get(k)]
    insurance_text = ", ".join(accepted) if accepted else "None listed"
    emdr_text = " | EMDR" if row.get("emdr") else ""
    age_text = f" | Ages {row.get('min_age', 0)}+" if row.get("min_age", 0) > 0 else ""

    stub = get_all_stub_slots(row)

    with st.container(border=True):
        col_name, col_status = st.columns([3, 1])
        with col_name:
            st.markdown(f"**{row['therapist']}**{emdr_text}{age_text}")
        with col_status:
            st.markdown(f"{status_icon} {status_label}")

        parts = []
        if row.get("conditions"):
            parts.append(row["conditions"])
        if row.get("approaches"):
            parts.append(f"Approaches: {row['approaches']}")
        if parts:
            st.caption(" | ".join(parts))

        if row.get("exclusions"):
            st.caption(f"Excludes: {row['exclusions']}")

        # Schedule — explicit day breakdown
        st.markdown(f"**Schedule:** {schedule_label}")

        col_ins, col_notes = st.columns(2)
        with col_ins:
            st.markdown(f"**Insurance:** {insurance_text}")
        with col_notes:
            if row.get("notes"):
                st.caption(f"Note: {row['notes']}")

        # Stub open slots
        if stub:
            st.markdown("**Open slots** _(stub — Phase 2: live IntakeQ data)_")
            day_cols = st.columns(len(stub))
            for i, (day, (day_mod, slots)) in enumerate(
                sorted(stub.items(), key=lambda x: WEEKDAYS.index(x[0]))
            ):
                with day_cols[i]:
                    badge = MODALITY_BADGE.get(day_mod, "")
                    st.caption(f"**{day}** {badge}")
                    for slot in slots:
                        st.caption(f"• {slot}")
        else:
            st.caption("_No open slots this week (stub)_")

        last_updated = row.get("last_updated", "")
        updated_by = row.get("updated_by", "")
        if last_updated or updated_by:
            tracking = []
            if last_updated:
                tracking.append(f"Updated: {last_updated}")
            if updated_by:
                tracking.append(f"By: {updated_by}")
            st.caption(" | ".join(tracking))

        if is_near_match and row.get("miss_reasons"):
            for reason in row["miss_reasons"]:
                st.info(reason, icon="💡")

        if row.get("warnings"):
            for w in row["warnings"]:
                st.warning(w, icon="⚠️")


def render_calendar_view(exact_df: pd.DataFrame, near_df: pd.DataFrame):
    """
    Weekly calendar — 5 columns (Mon–Fri).
    Each column shows matched therapists available that day with modality + stub slots.
    Exact matches shown normally; near-matches labeled.
    """
    all_matches = pd.concat([exact_df, near_df], ignore_index=True) if not near_df.empty else exact_df

    if all_matches.empty:
        st.info("No matches to display. Adjust filters.")
        return

    st.caption("Open slots are stub data — Phase 2 will pull live from IntakeQ.")
    st.markdown("---")

    day_cols = st.columns(5)

    for col_idx, day in enumerate(WEEKDAYS):
        with day_cols[col_idx]:
            st.markdown(f"### {day}")

            any_shown = False
            for _, row in all_matches.iterrows():
                row_dict = row.to_dict()
                schedule = get_therapist_schedule(row_dict)
                day_modality = schedule.get(day)

                if not day_modality:
                    continue

                slots = get_stub_slots(row_dict["therapist"], day)
                is_near = row_dict.get("miss_count", 0) > 0
                badge = MODALITY_BADGE.get(day_modality, "")
                name = row_dict["therapist"].split(",")[0]
                location = row_dict.get("location", "")

                with st.container(border=True):
                    label = f"**{name}**"
                    if is_near:
                        label += " _(near)_"
                    st.markdown(label)

                    loc_str = f" · {location}" if location and day_modality == "In-Person" else ""
                    st.caption(f"{badge} {day_modality}{loc_str}")

                    if slots:
                        st.caption("  ".join(f"`{s}`" for s in slots))
                    else:
                        st.caption("_No open slots_")

                any_shown = True

            if not any_shown:
                st.caption("_No matches_")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.title("Therapist Matcher")
    st.caption("Phase 1.5 — Schedule-aware matching with stub availability. Phase 2: live IntakeQ.")

    df = load_data()

    with st.expander("Paste Patient Inquiry (auto-extract criteria)", expanded=False):
        inquiry_text = st.text_area(
            "Paste the patient's email, text, or call notes:",
            height=120,
            placeholder=(
                "Example: Hello, I'm looking for a therapist. I have Cigna insurance. "
                "I'm dealing with anxiety and trauma. I'd prefer in-person in Commack, "
                "I'm 34 years old."
            ),
        )
        parse_button = st.button("Extract Criteria", type="primary")

    parsed_defaults = {}
    if parse_button and inquiry_text:
        parsed_defaults = parse_inquiry(inquiry_text)
        st.success("Criteria extracted — filters updated in sidebar.")
        tags = []
        if parsed_defaults.get("patient_age"):
            tags.append(f"Age: {parsed_defaults['patient_age']}")
        if parsed_defaults.get("insurance") != "Any":
            tags.append(f"Insurance: {parsed_defaults['insurance']}")
        if parsed_defaults.get("specialties"):
            tags.append(f"Conditions: {', '.join(parsed_defaults['specialties'])}")
        if parsed_defaults.get("require_emdr"):
            tags.append("EMDR")
        if parsed_defaults.get("modality") != "Any":
            tags.append(f"Modality: {parsed_defaults['modality']}")
        if parsed_defaults.get("location") != "Any":
            tags.append(f"Location: {parsed_defaults['location']}")
        if tags:
            st.caption("Extracted: " + " | ".join(tags))

    if parsed_defaults:
        st.session_state["parsed_defaults"] = parsed_defaults
    defaults = st.session_state.get("parsed_defaults", {})

    criteria = render_sidebar(defaults=defaults)
    exact_matches, near_matches = filter_and_rank(df, criteria)

    total = len(df)
    exact_count = len(exact_matches)
    near_count = len(near_matches)

    filter_tags = []
    if criteria.get("patient_age"):
        filter_tags.append(f"Age {criteria['patient_age']}")
    if criteria["insurance"] != "Any":
        filter_tags.append(criteria["insurance"])
    if criteria["specialties"]:
        filter_tags.append(", ".join(criteria["specialties"]))
    if criteria["require_emdr"]:
        filter_tags.append("EMDR")
    if criteria["modality"] != "Any":
        filter_tags.append(criteria["modality"])
    if criteria["location"] != "Any":
        filter_tags.append(criteria["location"])

    summary = " | ".join(filter_tags) if filter_tags else "No filters applied"
    st.markdown(
        f"**{exact_count}** exact match{'es' if exact_count != 1 else ''} "
        f"+ **{near_count}** near  —  of {total} therapists  ({summary})"
    )
    st.markdown("---")

    list_tab, cal_tab = st.tabs(["📋  List View", "📅  Calendar View"])

    with list_tab:
        if exact_matches.empty and near_matches.empty:
            st.info("No therapists match the selected criteria. Try broadening your filters.")
        elif exact_matches.empty:
            st.info("No exact matches. See near-matches below.")
        else:
            for _, row in exact_matches.iterrows():
                render_therapist_card(row.to_dict())

        if not near_matches.empty:
            st.markdown("---")
            st.markdown(f"### Near Matches ({near_count})")
            st.caption("Match most criteria but differ on 1–2 dimensions.")
            for _, row in near_matches.iterrows():
                render_therapist_card(row.to_dict(), is_near_match=True)

    with cal_tab:
        render_calendar_view(exact_matches, near_matches)

    st.markdown("---")
    with st.expander("Phase 2: Auto-Sync Configuration (Coming Soon)", expanded=False):
        st.markdown("""
**How auto-sync will work once IntakeQ API is connected:**

1. **Available → Full (automatic):** When the last open slot is booked, status updates to Full automatically.
2. **Full → Available (automatic):** When a cancellation opens a slot, status flips back to Available.
3. **Not Taking (manual only):** Never changed automatically — only the practice owner toggles this.
4. **Stub slots replaced:** The open-slot display on each card will pull real times from IntakeQ.
        """)
        st.caption("Awaiting IntakeQ API response re: availability endpoint.")

    st.markdown("---")
    st.caption("Phase 1.5: Day-level schedule breakdown + stub availability + calendar view.")


if __name__ == "__main__":
    main()
