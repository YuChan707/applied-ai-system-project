# calendar_app.py
# Google-Calendar-style visual schedule for PawPal+.
# Tasks appear as colored bars on a daily timeline — one color per pet.
#
# Run with:  python -m streamlit run calendar_app.py

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, date

from pawpal_system import Task, Pet, Owner, Planner

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PawPal+ Calendar",
    page_icon="📅",
    layout="wide",
)

# ── Color palette — one color per pet, cycling if more than 8 pets ─────────────
PET_PALETTE = [
    "#4A90D9",   # blue
    "#E8735A",   # coral
    "#6CC551",   # green
    "#A259D9",   # purple
    "#F5A623",   # amber
    "#50C8C6",   # teal
    "#E05CA0",   # pink
    "#8B7355",   # brown
]

PRIORITY_OPACITY = {"high": 1.0, "medium": 0.75, "low": 0.50}
PRIORITY_BORDER  = {"high": 3,   "medium": 2,     "low": 1}

TODAY = date.today().isoformat()   # "YYYY-MM-DD" — base date for all tasks


def hhmm_to_datetime(hhmm: str) -> datetime:
    h, m = hhmm.split(":")
    return datetime.fromisoformat(f"{TODAY}T{int(h):02d}:{int(m):02d}:00")


def build_timeline_df(owner: Owner, schedule: "Schedule") -> pd.DataFrame:
    """Convert the scheduled tasks into a DataFrame that Plotly can render."""
    scheduled_names = {t.name for t in schedule.tasks}
    pet_color = {}
    for i, pet in enumerate(owner.pets):
        pet_color[pet.name] = PET_PALETTE[i % len(PET_PALETTE)]

    rows = []
    for pet in owner.pets:
        for task in pet.tasks:
            if task.name not in scheduled_names:
                continue
            start_dt = hhmm_to_datetime(task.start_time)
            end_dt   = start_dt + timedelta(minutes=task.duration)
            rows.append({
                "Pet":       pet.name,
                "Task":      task.name,
                "Category":  task.category,
                "Priority":  task.priority,
                "Frequency": task.frequency,
                "Duration":  f"{task.duration} min",
                "Start":     start_dt,
                "Finish":    end_dt,
                "Color":     pet_color[pet.name],
                "Opacity":   PRIORITY_OPACITY[task.priority],
                "Border":    PRIORITY_BORDER[task.priority],
            })

    return pd.DataFrame(rows), pet_color


def build_figure(df: pd.DataFrame, pet_color: dict, owner: Owner) -> go.Figure:
    """Build an interactive Plotly Gantt chart styled like Google Calendar."""
    fig = go.Figure()

    # One trace per pet so the legend shows pet names with matching colors
    for pet_name, color in pet_color.items():
        pet_df = df[df["Pet"] == pet_name]
        if pet_df.empty:
            continue
        for _, row in pet_df.iterrows():
            fig.add_trace(go.Bar(
                x=[(row["Finish"] - row["Start"]).total_seconds() / 60],
                y=[row["Pet"]],
                base=[row["Start"].timestamp() * 1000],   # Plotly uses ms
                orientation="h",
                name=pet_name,
                legendgroup=pet_name,
                showlegend=(row.name == pet_df.index[0]),  # show once per pet
                marker=dict(
                    color=color,
                    opacity=row["Opacity"],
                    line=dict(color="white", width=row["Border"]),
                ),
                hovertemplate=(
                    f"<b>{row['Task']}</b><br>"
                    f"Pet: {row['Pet']}<br>"
                    f"Time: {row['Start'].strftime('%H:%M')} – {row['Finish'].strftime('%H:%M')}<br>"
                    f"Duration: {row['Duration']}<br>"
                    f"Priority: {row['Priority'].upper()}<br>"
                    f"Category: {row['Category']}<br>"
                    f"Repeats: {row['Frequency']}"
                    "<extra></extra>"
                ),
                text=row["Task"],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="white", size=12),
                width=0.5,
            ))

    # X-axis: show hours of the day
    day_start = datetime.fromisoformat(f"{TODAY}T06:00:00")
    day_end   = datetime.fromisoformat(f"{TODAY}T22:00:00")

    tick_times = [day_start + timedelta(hours=h) for h in range(17)]
    tick_ms    = [int(t.timestamp() * 1000) for t in tick_times]
    tick_text  = [t.strftime("%-I %p") if hasattr(datetime, "strftime") else t.strftime("%H:%M")
                  for t in tick_times]
    # Windows-safe format (no %-I)
    tick_text  = [t.strftime("%I %p").lstrip("0") for t in tick_times]

    fig.update_layout(
        title=dict(
            text=f"📅  {owner.name}'s Daily Pet Care Schedule  —  {date.today().strftime('%A, %B %d %Y')}",
            font=dict(size=20),
            x=0.0,
        ),
        barmode="overlay",
        xaxis=dict(
            type="date",
            tickvals=tick_ms,
            ticktext=tick_text,
            range=[int(day_start.timestamp() * 1000), int(day_end.timestamp() * 1000)],
            tickfont=dict(size=12),
            showgrid=True,
            gridcolor="#E8E8E8",
            gridwidth=1,
            zeroline=False,
        ),
        yaxis=dict(
            title="",
            tickfont=dict(size=14, color="#333"),
            autorange="reversed",
            showgrid=False,
        ),
        legend=dict(
            title="<b>Pet</b>",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=13),
        ),
        plot_bgcolor="#FAFAFA",
        paper_bgcolor="white",
        height=max(300, len(owner.pets) * 130 + 150),
        margin=dict(l=20, r=20, t=80, b=40),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )

    # Draw a "Now" line if the current time falls within the display window
    now = datetime.now()
    if day_start <= now <= day_end:
        fig.add_vline(
            x=int(now.timestamp() * 1000),
            line=dict(color="#D0021B", width=2, dash="dot"),
            annotation_text="Now",
            annotation_position="top",
            annotation_font=dict(color="#D0021B", size=11),
        )

    return fig


# ── Session state helpers ──────────────────────────────────────────────────────

def init_state():
    if "cal_owner" not in st.session_state:
        st.session_state.cal_owner = None
    if "cal_pets" not in st.session_state:
        st.session_state.cal_pets = {}     # {pet_name: Pet}
    if "cal_schedule" not in st.session_state:
        st.session_state.cal_schedule = None
    if "cal_conflicts" not in st.session_state:
        st.session_state.cal_conflicts = []


def load_example():
    """Pre-fill the session with Jordan + Mochi + Luna for a quick demo."""
    owner = Owner("Jordan", 90, preferences=[])
    dog = Pet("Mochi", "dog", 3)
    cat = Pet("Luna", "cat", 5)

    dog.add_task(Task("Morning walk",   "30-min walk around the block", 30, "high",   "walking",   start_time="07:00"))
    dog.add_task(Task("Feed breakfast", "1 cup dry food in bowl",       10, "high",   "feeding",   start_time="08:00"))
    dog.add_task(Task("Grooming",       "Brush coat for 15 minutes",    15, "medium", "grooming",  start_time="10:00"))
    cat.add_task(Task("Feed breakfast", "Half can wet food",             5, "high",   "feeding",   start_time="08:30"))
    cat.add_task(Task("Litter box",     "Clean and replace litter",     10, "medium", "hygiene",   start_time="09:00"))
    cat.add_task(Task("Playtime",       "Feather wand session",         20, "low",    "enrichment",start_time="15:00"))

    owner.add_pet(dog)
    owner.add_pet(cat)

    st.session_state.cal_owner    = owner
    st.session_state.cal_pets     = {"Mochi": dog, "Luna": cat}
    st.session_state.cal_schedule = None
    st.session_state.cal_conflicts = []


# ── Main app ───────────────────────────────────────────────────────────────────

init_state()

st.title("📅 PawPal+ Calendar View")
st.caption("Google Calendar-style daily schedule — tasks color-coded by pet")

# ── Sidebar — setup ────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Setup")

    if st.button("Load example (Jordan + Mochi + Luna)", use_container_width=True):
        load_example()
        st.success("Example loaded — click Generate Schedule below.")

    st.divider()

    # Owner settings
    st.subheader("Owner")
    owner_name     = st.text_input("Owner name", value="Jordan")
    available_time = st.number_input("Available time (min)", 10, 480, 90)
    preferences    = st.multiselect(
        "Preferences",
        ["no late feeding", "morning walks"],
        default=[],
    )

    if st.button("Save owner", use_container_width=True):
        if st.session_state.cal_owner is None or st.session_state.cal_owner.name != owner_name:
            st.session_state.cal_pets = {}
        st.session_state.cal_owner = Owner(owner_name, int(available_time), preferences)
        for pet in st.session_state.cal_pets.values():
            st.session_state.cal_owner.add_pet(pet)
        st.session_state.cal_schedule = None
        st.success(f"Saved {owner_name}")

    st.divider()

    # Add pet
    st.subheader("Add Pet")
    new_pet_name    = st.text_input("Pet name", key="new_pet_name", value="")
    new_pet_species = st.selectbox("Species", ["dog", "cat", "other"], key="new_pet_species")
    new_pet_age     = st.number_input("Age (years)", 0, 25, 2, key="new_pet_age")

    if st.button("Add pet", use_container_width=True):
        if new_pet_name:
            pet = Pet(new_pet_name, new_pet_species, int(new_pet_age))
            st.session_state.cal_pets[new_pet_name] = pet
            if st.session_state.cal_owner:
                st.session_state.cal_owner.add_pet(pet)
            st.session_state.cal_schedule = None
            st.success(f"Added {new_pet_name}")
        else:
            st.warning("Enter a pet name first.")

    # Show current pets
    if st.session_state.cal_pets:
        st.write("**Current pets:**")
        for i, (name, pet) in enumerate(st.session_state.cal_pets.items()):
            color = PET_PALETTE[i % len(PET_PALETTE)]
            st.markdown(
                f'<span style="color:{color}; font-weight:bold;">⬤</span> '
                f'{name} ({pet.pet_type})',
                unsafe_allow_html=True,
            )

    st.divider()

    # Add task
    st.subheader("Add Task")
    if not st.session_state.cal_pets:
        st.info("Add a pet first.")
    else:
        task_pet      = st.selectbox("For pet", list(st.session_state.cal_pets.keys()))
        task_name     = st.text_input("Task name", value="Morning walk", key="task_name")
        task_desc     = st.text_input("Description", value="", key="task_desc")
        task_duration = st.number_input("Duration (min)", 1, 240, 30, key="task_dur")
        task_priority = st.selectbox("Priority", ["high", "medium", "low"], key="task_pri")
        task_category = st.text_input("Category", value="walking", key="task_cat")
        task_start    = st.text_input("Start time (HH:MM)", value="08:00", key="task_start")
        task_freq     = st.selectbox("Frequency", ["daily", "twice daily", "weekly"], key="task_freq")

        if st.button("Add task", use_container_width=True):
            pet = st.session_state.cal_pets[task_pet]
            pet.add_task(Task(
                name=task_name,
                description=task_desc or task_name,
                duration=int(task_duration),
                priority=task_priority,
                category=task_category,
                frequency=task_freq,
                start_time=task_start,
            ))
            st.session_state.cal_schedule = None
            st.success(f"Added '{task_name}' to {task_pet}")

# ── Main area ──────────────────────────────────────────────────────────────────

owner = st.session_state.cal_owner

if owner is None:
    st.info("Use the sidebar to set up an owner and pets, or click **Load example** to see a demo.")
    st.stop()

# Summary bar
total_pets  = len(owner.pets)
total_tasks = sum(len(p.tasks) for p in owner.pets)
c1, c2, c3 = st.columns(3)
c1.metric("Owner", owner.name)
c2.metric("Time budget", f"{owner.available_time} min")
c3.metric("Pets / Tasks", f"{total_pets} / {total_tasks}")

st.divider()

# Generate schedule button
if st.button("Generate Schedule", type="primary", use_container_width=True):
    if total_tasks == 0:
        st.warning("Add at least one task before generating a schedule.")
    else:
        planner = Planner()
        schedule = planner.generate_schedule(owner)
        conflicts = planner.detect_conflicts(owner.get_all_tasks())
        st.session_state.cal_schedule  = schedule
        st.session_state.cal_conflicts = conflicts

# ── Calendar display ───────────────────────────────────────────────────────────
schedule = st.session_state.cal_schedule

if schedule:
    used      = schedule.total_time
    remaining = owner.available_time - used

    # Stats row
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Tasks scheduled", len(schedule.tasks))
    s2.metric("Time used",       f"{used} min")
    s3.metric("Time remaining",  f"{remaining} min")
    s4.metric("Utilization",     f"{round(used / owner.available_time * 100)}%")

    # Build and render the Gantt chart
    df, pet_color = build_timeline_df(owner, schedule)

    if df.empty:
        st.warning("No tasks were scheduled — check your time budget and preferences.")
    else:
        fig = build_figure(df, pet_color, owner)
        st.plotly_chart(fig, use_container_width=True)

    # Priority legend below the chart
    st.caption(
        "**Opacity guide:** Full color = HIGH priority  ·  "
        "Slightly faded = MEDIUM priority  ·  Most faded = LOW priority"
    )

    st.divider()

    # ── Detailed task table ────────────────────────────────────────────────────
    st.subheader("Scheduled Tasks")
    rows = []
    for i, task in enumerate(schedule.tasks, 1):
        pet_name = next(
            (p.name for p in owner.pets if any(t.name == task.name for t in p.tasks)), "—"
        )
        color = pet_color.get(pet_name, "#888")
        rows.append({
            "#":           i,
            "Pet":         pet_name,
            "Task":        task.name,
            "Start":       task.start_time,
            "Duration":    f"{task.duration} min",
            "Priority":    task.priority.upper(),
            "Category":    task.category,
            "Repeats":     task.frequency,
        })

    df_table = pd.DataFrame(rows)

    # Highlight rows by pet color using Pandas Styler
    def highlight_pet(row):
        color = pet_color.get(row["Pet"], "#888")
        # Light version of the pet color for the row background
        return [f"background-color: {color}22; color: #111"] * len(row)

    st.dataframe(
        df_table.style.apply(highlight_pet, axis=1),
        use_container_width=True,
        hide_index=True,
    )

    # ── Skipped tasks ──────────────────────────────────────────────────────────
    scheduled_names = {t.name for t in schedule.tasks}
    skipped = [
        (p.name, t)
        for p in owner.pets
        for t in p.tasks
        if t.name not in scheduled_names
    ]
    if skipped:
        with st.expander(f"Skipped tasks ({len(skipped)})"):
            for pet_name, task in skipped:
                st.markdown(
                    f"- **{task.name}** ({pet_name}) — "
                    f"{task.duration} min · {task.priority} priority · "
                    f"filtered by preference or time budget"
                )

    # ── Conflict warnings ──────────────────────────────────────────────────────
    conflicts = st.session_state.cal_conflicts
    if conflicts:
        st.divider()
        st.error(f"⚠️ {len(conflicts)} scheduling conflict(s) detected:")
        for w in conflicts:
            st.markdown(f"- {w}")
    else:
        st.success("No scheduling conflicts detected.")
