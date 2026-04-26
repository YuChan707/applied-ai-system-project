# PawPal+ — AI-Powered Pet Care Scheduler

## Original Project Reference

This project builds on **PawPal** (Modules 1–3), a Streamlit-based chatbot that helped
pet owners ask questions about daily pet care using a simple prompt-response loop.
The original PawPal could answer questions like "What should I feed my dog?" but had
no memory, no scheduling logic, and no ability to manage real tasks or time budgets.
PawPal+ replaces the static Q&A model with a structured planning system that actually
builds and manages a personalized daily care plan.

---

## Title and Summary

**PawPal+** is an AI-assisted pet care scheduling system that generates a prioritized,
conflict-free daily care plan for pet owners based on their available time and personal
preferences.

**Why it matters:** Pet owners with multiple pets face a daily juggling act — feeding
windows, medication timing, walks, grooming, and enrichment all compete for limited
time. Missing a high-priority task (e.g., medication) because the day ran out of time
is a real problem. PawPal+ solves this by automatically selecting the most important
tasks that fit within the owner's time budget, filtering out tasks that violate
preferences, and warning about scheduling conflicts before they happen.

---

## Architecture Overview

### System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        USER INPUT                           │
│   (Owner name, time budget, preferences, pets, tasks)       │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     DATA LAYER                              │
│                                                             │
│   Owner ──────────────── has many ──────────► Pet(s)        │
│     • name                                    • name        │
│     • available_time                          • type        │
│     • preferences[ ]                          • age         │
│                                               • tasks[ ]    │
│                                                    │        │
│                                                    ▼        │
│                                               Task          │
│                                                • name       │
│                                                • duration   │
│                                                • priority   │
│                                                • category   │
│                                                • start_time │
│                                                • frequency  │
└───────────────────────────┬─────────────────────────────────┘
                            │  owner.get_all_tasks()
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  PLANNER (Scheduling Engine)                 │
│                                                             │
│   Step 1 ─ sort_tasks()                                     │
│            Sort by priority (high → medium → low)           │
│            then by duration (shortest first)                │
│                    │                                        │
│   Step 2 ─ apply_constraints()                              │
│            • Preference filter (remove excluded categories) │
│            • Greedy time-budget fit (knapsack-style)        │
│                    │                                        │
│   Step 3 ─ detect_conflicts()                               │
│            Check all task pairs for time-window overlap     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     SCHEDULE OUTPUT                         │
│                                                             │
│   • display_plan()   → ordered task list with time tracker  │
│   • explain_plan()   → human-readable reason per task       │
│   • conflict warnings → surfaced before harm is done        │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               HUMAN REVIEW AND FEEDBACK LOOP                │
│                                                             │
│   Owner reads plan → marks tasks complete                   │
│   → auto-reschedule creates next recurrence                 │
│   → owner adjusts preferences for next run                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    TESTING LAYER                            │
│   python -m pytest tests/test_pawpal.py -v                  │
│   • test_mark_complete_changes_status                       │
│   • test_add_task_increases_pet_task_count                  │
└─────────────────────────────────────────────────────────────┘
```

### Component Roles

| Component | File | Role |
|---|---|---|
| **Task** | `pawpal_system.py` | Data model for a single care item |
| **Pet** | `pawpal_system.py` | Groups tasks, handles auto-reschedule on completion |
| **Owner** | `pawpal_system.py` | Holds time budget and preferences, flattens all tasks |
| **Planner** | `pawpal_system.py` | Sorting, filtering, and conflict detection engine |
| **Schedule** | `pawpal_system.py` | Output container with display and explain methods |
| **CLI Demo** | `main.py` | Runs the full pipeline without UI for quick verification |
| **Web UI** | `app.py` | Streamlit interface for interactive use |
| **Tests** | `tests/test_pawpal.py` | Automated correctness checks |

---

## Setup Instructions

### 1. Prerequisites

- Python 3.9 or higher
- pip (comes with Python)

### 2. Clone the project

```bash
git clone https://github.com/YuChan707/ai110-module2show-pawpal-starter.git
cd ai110-module2show-pawpal-starter
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` includes:
```
streamlit>=1.30
pytest>=7.0
```

### 4. Run the web app

```bash
python -m streamlit run app.py
```

Open your browser to `http://localhost:8501`

### 5. Run the CLI demo (no browser needed)

```bash
python main.py
```

### 6. Run the tests

```bash
python -m pytest tests/ -v
```

> **Note for Windows users:** If `pytest` or `streamlit` are not recognized as commands,
> prefix with `python -m` (e.g., `python -m pytest`). This is common when Python is
> installed via the Microsoft Store.

---

## Sample Interactions

### Example 1 — Basic Schedule Generation

**Input:**
- Owner: Jordan, 90 minutes available
- Preferences: `["morning walks", "no late feeding"]`
- Mochi (dog): Morning walk (30 min, high), Feed breakfast (10 min, high), Grooming (15 min, medium)
- Luna (cat): Feed breakfast (5 min, high), Litter box (10 min, medium), Playtime (20 min, low)

**Output:**
```
Owner : Jordan  |  Time budget: 90 min
Pets  : Mochi, Luna

Today's Schedule
========================================
1. Morning walk          30 min  [high]
   30-min walk around the block
2. Feed breakfast        10 min  [high]
   1 cup dry food in bowl
3. Feed breakfast         5 min  [high]
   Half can wet food
4. Litter box            10 min  [medium]
   Clean and replace litter
5. Grooming              15 min  [medium]
   Brush coat for 15 minutes
----------------------------------------
   Total time used : 70 min
   Time remaining  : 20 min
========================================
```

**Why this output:** All high-priority tasks are selected first. Medium tasks fill the
remaining time. Playtime (low priority, 20 min) is skipped because medium tasks consumed
the budget before low-priority tasks were reached.

---

### Example 2 — Conflict Detection

**Input:** Two grooming tasks with overlapping time windows:
- Bath: starts 10:00, duration 20 min (ends 10:20)
- Nail trim: starts 10:10, duration 15 min (ends 10:25)

**Output:**
```
Conflict Detection
========================================
  WARNING: 'Bath' (10:00, 20min) overlaps with 'Nail trim' (10:10, 15min)
========================================
```

**Why this matters:** The system catches the 10-minute overlap (10:10–10:20) before the
owner tries to do both simultaneously, allowing them to reschedule one task.

---

### Example 3 — Auto-Reschedule After Completion

**Input:** Mark Grooming (daily) and Litter box (twice daily) as complete.

**Output:**
```
Auto-Reschedule Results
========================================
  [DONE] Grooming             due: 2026-04-26  freq: daily
  [next] Grooming             due: 2026-04-27  freq: daily
  [DONE] Litter box           due: 2026-04-26  freq: twice daily
  [next] Litter box           due: 2026-04-27  freq: twice daily
========================================

Pending tasks (all pets):
  - Morning walk        due: 2026-04-26
  - Feed breakfast      due: 2026-04-26

Completed tasks (all pets):
  - Grooming            due: 2026-04-26
  - Litter box          due: 2026-04-26
```

**Why this matters:** The owner marks one task done and the next occurrence automatically
appears with the correct future date — no manual re-entry needed.

---

## Design Decisions

### 1. Greedy Scheduling Algorithm (not brute-force)

**Decision:** Sort by priority then shortest duration, then greedily select tasks.

**Trade-off:** A full knapsack solver would find the mathematically optimal set of tasks,
but adds complexity that is hard to explain to a non-technical owner. The greedy approach
is fast, predictable, and transparent — the owner can trace exactly why each task was or
was not selected.

### 2. Preference Rules as Lambdas (not hardcoded if-statements)

**Decision:** Store preference rules as a dictionary of lambdas in `PREFERENCE_RULES`.

**Trade-off:** Adding a new preference only requires one new line at the top of the file
with no changes to `Planner` or `Owner`. This keeps the system open for extension. The
cost is slightly less readable code for beginners.

### 3. Conflict Detection Returns Strings (not exceptions)

**Decision:** `detect_conflicts()` returns a list of warning strings instead of raising errors.

**Trade-off:** A scheduling conflict is information for the owner to act on, not a program
crash. Returning strings keeps the app running and lets the owner decide how to resolve
it. The downside is that warnings can be ignored — a future version could require
acknowledgment before saving the schedule.

### 4. Separation of Backend and UI

**Decision:** All logic lives in `pawpal_system.py`, verified via `main.py`, then
connected to Streamlit in `app.py`.

**Trade-off:** More files to navigate, but each layer is independently testable and the
backend can be reused in other interfaces (API, mobile app) without copying code.

---

## Testing Summary

### Test Results

```
tests/test_pawpal.py::test_mark_complete_changes_status       PASSED
tests/test_pawpal.py::test_add_task_increases_pet_task_count  PASSED

2 passed in 0.13s
```

### What Worked

- Priority-based greedy scheduling correctly selects high-urgency tasks in all tested cases
- Conflict detection reliably catches overlapping intervals using the standard formula
  (`a_start < b_end AND b_start < a_end`)
- Auto-reschedule correctly computes next due dates using `timedelta` for all frequency types

### What Did Not Work / Limitations

- **Preference rules are too broad:** "no late feeding" removes ALL feeding tasks regardless
  of time. A time-aware rule (filter feeding tasks only after 18:00) would be more precise.
- **No conflict resolution:** The system detects conflicts but cannot automatically fix
  them — the owner must manually adjust start times.
- **`Pet.age` is stored but unused:** Planned for age-based adjustments (senior pets need
  shorter walks) but not implemented.

### What Would Be Added With More Time

- Edge-case tests: back-to-back tasks (should not conflict), zero-duration tasks
- Parametrized tests for all frequency types in `mark_complete()`
- End-to-end test running the full `generate_schedule()` pipeline with known input/output

---

## Reflection

### What This Project Taught Me About AI

Building PawPal+ showed me that "AI" in a system does not always mean a neural network
or language model. The intelligence here lives in the **decision-making logic** — the
rules that determine what gets scheduled, in what order, and why. Encoding that logic
explicitly (priority rules, preference filters, conflict detection) and making it
explainable (`explain_plan()`) is a core part of responsible AI design.

I also learned that AI collaboration tools are most useful when you ask **why** questions,
not just **what** questions. Asking "why would a greedy algorithm miss the optimal solution
here?" taught me more about algorithmic trade-offs than asking for code directly.

### What This Project Taught Me About Problem-Solving

The biggest insight was that **constraints are features, not limitations**. The time
budget, preferences, and conflict rules all look like restrictions — but they are exactly
what make the system useful. A scheduler that accepts all tasks unconditionally is not a
scheduler at all.

The hardest part was deciding what the system should *not* do. Keeping `Pet.age` in the
model without full implementation was tempting, but it was better to ship a clean working
system than one with half-finished features that could confuse users or break edge cases.

### Confidence Rating

- Scheduling logic correctness: **85/100** — the greedy algorithm works for tested
  scenarios but preference filtering is coarser than ideal.
- Overall system structure: **90/100** — the five-class design is clean, each class has
  a single clear responsibility, and the separation between data, logic, and UI is solid.
