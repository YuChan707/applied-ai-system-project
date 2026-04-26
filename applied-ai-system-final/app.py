# app.py
# Streamlit UI layer for PawPal+.
# This file only handles user input and display — all scheduling logic
# lives in pawpal_system.py so it can be tested independently via main.py.

import io
import json
import re
from contextlib import redirect_stdout

import anthropic
import streamlit as st
from pawpal_system import Task, Pet, Owner, Planner
from agent import run_agent   # also loads .env at import time


_PRIORITY_OPTS = ["low", "medium", "high"]
_FREQ_OPTS     = ["daily", "twice daily", "weekly"]


def generate_random_task(pet_name: str, pet_type: str) -> dict:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": (
                f"Generate one realistic pet care task for {pet_name}, a {pet_type}. "
                "Return ONLY a valid JSON object with exactly these keys: "
                "task_title (string), duration (integer minutes, realistic for the activity), "
                "priority (one of: high, medium, low), description (one sentence), "
                "category (one of: feeding, grooming, walking, hygiene, enrichment, health, training), "
                "start_time (string HH:MM, realistic time of day), "
                "frequency (one of: daily, twice daily, weekly). "
                f"Pick a random activity from: bathing, medication, grooming, nail trimming, "
                "ear cleaning, dental care, feeding, walking, playtime, litter box, training, "
                "hair brushing, vet check-up, flea treatment, socialisation. "
                "No markdown, no explanation — raw JSON only."
            ),
        }],
    )
    text = response.content[0].text.strip()
    # Strip markdown code fences if Claude wraps the JSON
    text = re.sub(r"^```(?:json)?\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return json.loads(text)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ── 1. Owner & Pet Setup ──────────────────────────────────────────────────────
st.subheader("Owner & Pet Setup")

owner_name     = st.text_input("Owner name", value="Jordan")
available_time = st.number_input("Available time (minutes)", min_value=1, max_value=480, value=90)
pet_name       = st.text_input("Pet name", value="Mochi")
species        = st.selectbox("Species", ["dog", "cat", "other"])
preferences    = st.multiselect(
    "Owner preferences",
    options=["no late feeding", "morning walks"],
    default=[],
)

# The "Save" button recreates Owner and Pet from the current input values.
# This is intentional — it lets the user change the setup and regenerate
# without the old frozen objects persisting from a previous session.
if st.button("Save owner & pet"):
    st.session_state.owner = Owner(
        name=owner_name,
        available_time=int(available_time),
        preferences=preferences,
    )
    # Create a fresh Pet and immediately link it to the new Owner.
    pet = Pet(name=pet_name, pet_type=species, age=1)
    st.session_state.pet = pet
    st.session_state.owner.add_pet(pet)
    # Clear any previously generated schedule so the UI stays consistent
    # with the new owner/pet configuration.
    st.session_state.schedule = None
    st.success(f"Saved {owner_name} with pet {pet_name}.")

# Guard: stop rendering the rest of the page until owner is saved.
# st.stop() halts script execution for this rerun — nothing below runs.
# This prevents KeyError crashes when session_state.pet doesn't exist yet.
if "owner" not in st.session_state:
    st.info("Fill in owner & pet details above, then click **Save owner & pet** to continue.")
    st.stop()

st.divider()

# ── 2. Add a Task ─────────────────────────────────────────────────────────────
_hdr_col, _rand_col = st.columns([5, 1])
with _hdr_col:
    st.subheader(f"Add a Task for {st.session_state.pet.name}")
with _rand_col:
    if st.button("Randomize", help="AI suggests a realistic task for your pet"):
        with st.spinner("Thinking..."):
            try:
                _rt = generate_random_task(
                    st.session_state.pet.name,
                    st.session_state.pet.pet_type,
                )
                _p = _rt.get("priority", "high")
                _f = _rt.get("frequency", "daily")
                st.session_state["_task_title"]  = _rt.get("task_title", "Morning walk")
                st.session_state["_duration"]    = max(1, min(240, int(_rt.get("duration", 20))))
                st.session_state["_priority"]    = _p if _p in _PRIORITY_OPTS else "high"
                st.session_state["_description"] = _rt.get("description", "")
                st.session_state["_category"]    = _rt.get("category", "walking")
                st.session_state["_start_time"]  = _rt.get("start_time", "08:00")
                st.session_state["_frequency"]   = _f if _f in _FREQ_OPTS else "daily"
            except Exception as e:
                st.error(f"Could not generate task: {e}")

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk", key="_task_title")
with col2:
    duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20, key="_duration")
with col3:
    priority = st.selectbox("Priority", _PRIORITY_OPTS, index=2, key="_priority")

col4, col5, col6 = st.columns(3)
with col4:
    task_description = st.text_input("Description", value="Quick walk around the block", key="_description")
with col5:
    category = st.text_input("Category", value="walking", key="_category")
with col6:
    start_time = st.text_input("Start time (HH:MM)", value="08:00", key="_start_time")

frequency = st.selectbox("Frequency", _FREQ_OPTS, index=0, key="_frequency")

if st.button("Add task"):
    new_task = Task(
        name=task_title,
        description=task_description,
        duration=int(duration),
        priority=priority,
        category=category,
        frequency=frequency,
        start_time=start_time,
    )
    # add_task() appends to the Pet's task list, which the Owner can later
    # retrieve via get_all_tasks() for scheduling.
    st.session_state.pet.add_task(new_task)
    # Reset the schedule — it is now stale because the task list changed.
    st.session_state.schedule = None
    st.success(f"Added '{task_title}' to {st.session_state.pet.name}'s tasks.")

# Display the current task list so the user can see what has been added.
current_tasks = st.session_state.pet.tasks
if current_tasks:
    st.write(f"**{st.session_state.pet.name}'s tasks ({len(current_tasks)} total):**")
    st.table([
        {
            "task": t.name,
            "start": t.start_time,
            "duration (min)": t.duration,
            "priority": t.priority,
            "category": t.category,
            "frequency": t.frequency,
            # Show a checkmark for completed tasks so the user can see status at a glance.
            "done": "✓" if t.completed else "",
        }
        for t in current_tasks
    ])
else:
    st.info("No tasks yet. Add one above.")

st.divider()

# ── 3. Generate Schedule ──────────────────────────────────────────────────────
st.subheader("Build Schedule")

if st.button("Generate schedule"):
    planner  = Planner()
    # generate_schedule() runs the full pipeline:
    # collect → sort by priority → filter by preference + time → return Schedule.
    schedule = planner.generate_schedule(st.session_state.owner)
    # detect_conflicts() checks ALL tasks (not just scheduled ones) so the owner
    # is warned about overlaps even if a task was filtered out of the schedule.
    conflicts = planner.detect_conflicts(st.session_state.owner.get_all_tasks())
    # Store both in session_state so they persist across reruns.
    # Without this, clicking any other widget would wipe the results.
    st.session_state.schedule  = schedule
    st.session_state.conflicts = conflicts

# Render the persisted schedule — this block runs on every rerun so the
# schedule stays visible even when the user interacts with other widgets.
if st.session_state.get("schedule"):
    schedule = st.session_state.schedule
    owner    = st.session_state.owner

    st.success(f"Schedule generated — {schedule.total_time} min of {owner.available_time} min used.")
    st.table([
        {
            "#": i,
            "task": t.name,
            "start": t.start_time,
            "duration (min)": t.duration,
            "priority": t.priority,
            "category": t.category,
        }
        for i, t in enumerate(schedule.tasks, start=1)
    ])
    st.caption(f"Time remaining: {owner.available_time - schedule.total_time} min")

    # Explanation expander — mirrors Schedule.explain_plan() for the UI.
    # Helps the owner understand WHY each task was included.
    with st.expander("Why was each task chosen?"):
        for i, t in enumerate(schedule.tasks, start=1):
            st.markdown(
                f"**{i}. {t.name}** — `{t.priority}` priority · "
                f"`{t.category}` · repeats `{t.frequency}`"
            )

    # Conflict warnings — shown only when detect_conflicts() found overlaps.
    # Returning strings (not raising exceptions) keeps the app alive so the
    # owner can see the issue and decide how to fix it.
    if st.session_state.get("conflicts"):
        st.divider()
        st.warning("⚠️ Scheduling conflicts detected:")
        for w in st.session_state.conflicts:
            st.markdown(f"- {w}")
    else:
        st.info("No scheduling conflicts found.")

st.divider()

# ── 4. AI Agent Schedule ──────────────────────────────────────────────────────
st.subheader("AI Agent Schedule")
st.caption("Claude analyzes your pets and tasks, calls the scheduler, and verifies the result before giving you the final plan.")

if st.button("Generate", type="primary"):
    owner = st.session_state.owner

    # Build the pet + task description from live session data
    pet_blocks = []
    for pet in owner.pets:
        if not pet.tasks:
            continue
        task_lines = "\n".join(
            f"      * {t.name}: {t.duration} min, {t.priority} priority, "
            f"{t.category}, starts {t.start_time}"
            for t in pet.tasks
        )
        pet_blocks.append(f"  - {pet.name} ({pet.pet_type}) with tasks:\n{task_lines}")

    prefs_str = ", ".join(owner.preferences) if owner.preferences else "none"
    pets_str  = "\n".join(pet_blocks) if pet_blocks else "  (no tasks added yet)"

    request = (
        f"Please create an optimized daily care schedule for {owner.name}.\n"
        f"{owner.name} has {owner.available_time} minutes available today.\n"
        f"Preferences: {prefs_str}.\n\n"
        f"Pets:\n{pets_str}\n\n"
        "Use your tools to analyze the situation, prioritize tasks, run the scheduler, "
        "and verify the result before giving me the final schedule."
    )

    with st.spinner("AI Agent is thinking..."):
        captured = io.StringIO()
        with redirect_stdout(captured):
            run_agent(request)
        st.session_state.agent_output = captured.getvalue()

if st.session_state.get("agent_output"):
    output = st.session_state.agent_output

    # Split tool-call trace from Claude's final response
    if "[Claude's Final Response]" in output:
        trace, _, final = output.partition("[Claude's Final Response]")
        with st.expander("Agent trace (tool calls)"):
            st.code(trace.strip(), language=None)
        st.success("Claude's recommendation")
        st.markdown(final.strip())
    else:
        st.code(output.strip(), language=None)
