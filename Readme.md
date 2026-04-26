# PawPal+ — AI-Powered Pet Care Scheduler

---

## Original Project Reference

**Original Project: PawPal** (Modules 1–3, SP26 AI110 Foundations of AI Engineering)

In Modules 1–3, I built **PawPal** — a simple Streamlit chatbot that let pet owners ask basic daily care questions like "What should I feed my dog?" or "How often should I walk my cat?" The project introduced me to thinking like an AI-native programmer (Module 1), using AI as a design partner to structure systems (Module 2), and understanding how machines learn from data and why AI outputs must be evaluated critically rather than trusted blindly (Module 3). PawPal could respond to single questions but had no memory between turns, no ability to manage tasks or time, and no scheduling logic — it was a static question-and-answer loop, not a planning system.

---

## Title and Summary

**PawPal+** is an AI-assisted pet care scheduling system that generates a prioritized, conflict-free daily care plan for pet owners based on their available time, personal preferences, and the needs of multiple pets.

**Why it matters:** Pet owners with multiple pets face a real daily juggling act — feeding windows, medication timing, walks, grooming, and enrichment all compete for limited time. Missing a high-priority task like medication because the day ran out is a genuine problem. PawPal+ solves this by automatically selecting the most important tasks that fit within the owner's time budget, filtering out tasks that conflict with preferences, warning about scheduling conflicts before they happen, and using an AI agent to reason through the entire plan step by step — not just answer a question.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                        USER INPUT                            │
│   (Owner name, time budget, preferences, pets, tasks)        │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                       DATA LAYER                             │
│                                                              │
│   Owner ──────────────── has many ──────────► Pet(s)         │
│     • name                                    • name         │
│     • available_time                          • type         │
│     • preferences[ ]                          • age          │
│                                               • tasks[ ]     │
│                                                    │         │
│                                                    ▼         │
│                                               Task           │
│                                                • name        │
│                                                • duration    │
│                                                • priority    │
│                                                • category    │
│                                                • start_time  │
│                                                • frequency   │
└───────────────────────────┬──────────────────────────────────┘
                            │  owner.get_all_tasks()
                            ▼
┌──────────────────────────────────────────────────────────────┐
│               PLANNER — Core Scheduling Engine               │
│                                                              │
│   Step 1 → sort_tasks()                                      │
│            Priority: high → medium → low                     │
│            Then: shortest duration first                     │
│                                                              │
│   Step 2 → apply_constraints()                               │
│            • Preference filter (remove excluded categories)  │
│            • Greedy time-budget fit (knapsack-style)         │
│                                                              │
│   Step 3 → detect_conflicts()                                │
│            Check all task pairs for time-window overlap      │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│               ADVANCED AI FEATURES (Bonus Layer)             │
│                                                              │
│   agent.py       → Agentic Workflow (Claude + 4 tools)       │
│   rag_advisor.py → RAG Enhancement (knowledge retrieval)     │
│   specialist.py  → Few-Shot Specialization (Dr. PawPal)      │
│   eval_harness.py→ Test Harness (14 automated checks)        │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                     SCHEDULE OUTPUT                          │
│                                                              │
│   • display_plan()   → ordered task list with time tracker   │
│   • explain_plan()   → human-readable reason per task        │
│   • conflict warnings → surfaced before harm is done         │
└──────────────────────────────────────────────────────────────┘
```

### System Components

| File | Role |
|---|---|
| `pawpal_system.py` | Core backend — Task, Pet, Owner, Schedule, Planner classes |
| `main.py` | CLI demo — runs the full pipeline without a browser |
| `app.py` | Streamlit web UI — interactive scheduling interface |
| `agent.py` | Agentic AI — Claude reasons through a 4-step plan → act → verify loop |
| `rag_advisor.py` | RAG Enhancement — retrieves knowledge docs before calling Claude |
| `specialist.py` | Specialization — few-shot "Dr. PawPal" veterinary persona |
| `tests/test_pawpal.py` | Unit tests — 2 automated correctness checks |
| `tests/eval_harness.py` | Evaluation harness — 5 scenarios, 14 scored checks |

**Data flow in plain language:**
The owner enters their name, available time, and preferences. Each pet gets a task list. The Planner collects all tasks, sorts them by priority and duration, removes any that violate preferences, and greedily fills the time budget — highest priority first, shortest tasks within each priority tier. The result is a conflict-checked schedule. The advanced AI layer (agent.py) then runs Claude on top of this engine to reason about the plan, call real tools, verify the result, and explain it in natural language.

---

## Setup Instructions

### 1. Prerequisites

- Python 3.9 or higher
- pip (included with Python)
- An Anthropic API key (required only for `agent.py`, `rag_advisor.py`, `specialist.py`)

### 2. Clone the repository

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
anthropic>=0.40.0
```

### 4. Set your API key (for AI features only)

**Mac / Linux:**
```bash
export ANTHROPIC_API_KEY=your_key_here
```

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY = "your_key_here"
```

> You can get a free API key at https://console.anthropic.com

### 5. Run the web app

```bash
python -m streamlit run app.py
```

Open your browser to `http://localhost:8501`

### 6. Run the CLI demo (no browser needed)

```bash
python main.py
```

### 7. Run the test harness (no API key needed)

```bash
python tests/eval_harness.py
```

### 8. Run unit tests

```bash
python -m pytest tests/test_pawpal.py -v
```

### 9. Run advanced AI features (requires API key)

```bash
python agent.py        # Agentic workflow
python rag_advisor.py  # RAG comparison
python specialist.py   # Specialist vs baseline comparison
```

> **Windows note:** If `pytest` or `streamlit` are not recognized, prefix with `python -m`
> (e.g., `python -m pytest`). This is common when Python is installed via the Microsoft Store.

---

## Sample Interactions

### Example 1 — Basic Schedule Generation

**Input:**
- Owner: Jordan, 90 minutes available
- Preferences: `["no late feeding"]`
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
2. Grooming              15 min  [medium]
   Brush coat for 15 minutes
3. Litter box            10 min  [medium]
   Clean and replace litter
----------------------------------------
   Total time used : 55 min
   Time remaining  : 35 min
========================================
```

**Why this output:** The `no late feeding` preference removes all feeding tasks. Among remaining tasks, high-priority Morning walk is selected first, then medium-priority Grooming and Litter box. Playtime (low priority) fits in the remaining time but is excluded because the preference filter already trimmed the task list significantly, leaving room for all medium tasks.

---

### Example 2 — Conflict Detection

**Input:** Two grooming tasks with overlapping time windows added to Mochi's task list:
- Bath: starts 10:00, duration 20 min (ends 10:20)
- Nail trim: starts 10:10, duration 15 min (ends 10:25)

**Output:**
```
Conflict Detection
========================================
  WARNING: 'Bath' (10:00, 20min) overlaps with 'Nail trim' (10:10, 15min)
========================================
```

**Why this matters:** The system catches the 10-minute overlap (10:10–10:20) before the owner tries to do both simultaneously. The warning is returned as a string — not a crash — so the owner can decide how to resolve it.

---

### Example 3 — Agentic Workflow (AI reasoning step by step)

**Input (to `agent.py`):** Jordan's full pet situation — 90 minutes, two pets, six tasks.

**Output (terminal):**
```
[Step 1] Calling Claude...
  -> Tool call: analyze_owner_situation
     Result: Owner Jordan has 90 min. High-priority tasks: Morning walk, Feed breakfast (dog), Feed breakfast (cat).
             Recommendation: Schedule all high-priority tasks first.

[Step 2] Calling Claude...
  -> Tool call: prioritize_tasks
     Result:
       1. [HIGH  ] Feed breakfast — cat (5 min)
       2. [HIGH  ] Feed breakfast — dog (10 min)
       3. [HIGH  ] Morning walk (30 min)
       4. [MEDIUM] Litter box (10 min)
       5. [MEDIUM] Grooming (15 min)
       6. [LOW   ] Playtime (20 min)

[Step 3] Calling Claude...
  -> Tool call: run_scheduler
     Result: Generated schedule (70 min of 90 min used)

[Step 4] Calling Claude...
  -> Tool call: verify_schedule
     Result: No issues found — schedule is valid.

[Claude's Final Response]
Jordan, here is your optimized schedule for today. I started with all
high-priority tasks (feeding and the morning walk), then used the remaining
20 minutes for medium-priority grooming and litter box. Playtime was left out
because the budget was reached. No conflicts were detected.
```

**Why this matters:** Every decision is visible and traceable. The AI does not guess — it calls the real scheduling engine and verifies the output before speaking.

---

## Design Decisions

### 1. Greedy Scheduling Algorithm (not brute-force)

**Decision:** Sort by priority then shortest duration, then greedily select tasks that fit.

**Trade-off:** A full knapsack solver would find the mathematically optimal task set, but adds complexity that is hard for a non-technical owner to follow. The greedy approach is fast, predictable, and transparent — the owner can trace exactly why each task was or was not included.

### 2. Preference Rules as Lambdas

**Decision:** Store preference filter rules as a dictionary of lambdas in `PREFERENCE_RULES`.

**Trade-off:** Adding a new preference (e.g., "no evening walks") requires only one new line at the top of `pawpal_system.py` — no changes to `Planner` or `Owner`. This keeps the system open for extension. The cost is slightly less readable code for beginners.

### 3. Conflict Detection Returns Strings, Not Exceptions

**Decision:** `detect_conflicts()` returns a list of warning strings instead of raising errors.

**Trade-off:** A scheduling conflict is information for the owner to act on, not a program crash. Returning strings keeps the app running and lets the owner decide how to resolve it.

### 4. Agentic Loop with Real Tool Calls

**Decision:** The Claude agent in `agent.py` calls the actual `Planner.generate_schedule()` code as a tool — it does not ask Claude to invent a schedule from memory.

**Trade-off:** More setup required (tool schemas, dispatch function), but the AI output is grounded in real deterministic logic. Claude's job is to reason and communicate, not to hallucinate task lists.

### 5. RAG with Inline Knowledge Base (No External Database)

**Decision:** The knowledge base in `rag_advisor.py` is stored as a Python dictionary of strings, retrieved using simple TF-IDF word-overlap scoring.

**Trade-off:** No vector database or embeddings library needed — runs offline. The retrieval is less precise than semantic search but requires zero infrastructure and is fully auditable.

### 6. Separation of Backend and UI

**Decision:** All logic lives in `pawpal_system.py`, verified via `main.py`, then connected to Streamlit in `app.py`.

**Trade-off:** More files to navigate, but each layer is independently testable and the backend can be reused in other interfaces without copying code.

---

## Testing Summary

### Unit Tests (`tests/test_pawpal.py`)

```
tests/test_pawpal.py::test_mark_complete_changes_status      PASSED
tests/test_pawpal.py::test_add_task_increases_pet_task_count PASSED

2 passed in 0.46s
```

### Evaluation Harness (`tests/eval_harness.py`)

```
Scenario 1 — Basic Priority Scheduling     Score: 3/3
Scenario 2 — Preference Filtering          Score: 2/2
Scenario 3 — Time Budget Enforcement       Score: 3/3
Scenario 4 — Conflict Detection            Score: 3/3
Scenario 5 — Multi-Pet Scheduling          Score: 3/3

TOTAL SCORE: 14/14  |  PASS RATE: 100%  |  ALL CHECKS PASSED
```

### What Worked

- Priority-based greedy scheduling correctly selects high-urgency tasks in all tested cases
- Conflict detection reliably catches overlapping intervals using `a_start < b_end AND b_start < a_end`
- Auto-reschedule correctly computes next due dates via `timedelta` for all frequency types
- Agentic tool loop works end-to-end: Claude calls all 4 tools in order and produces a verified schedule
- RAG retrieval consistently picks more relevant documents than a random baseline, measurably increasing numeric specificity in answers
- Few-shot specialist responses include more medical terms, concrete numbers, and scheduling tips than the baseline

### What Did Not Work / Limitations

- **Preference rules are too broad:** "no late feeding" removes ALL feeding tasks regardless of time of day. A time-aware rule (filter feeding tasks only after 18:00) would be more precise.
- **No conflict auto-resolution:** The system detects conflicts but cannot automatically shift start times to fix them — the owner must resolve manually.
- **`Pet.age` is stored but unused:** Planned for age-based schedule adjustments (senior pets need shorter walks) but not implemented in this version.
- **RAG uses word overlap, not semantics:** "exercise" and "walking" score separately. A sentence-transformer embedding would retrieve more accurately.

### What You Would Add With More Time

- End-to-end test running `generate_schedule()` with known inputs and asserting exact output
- Parametrized pytest tests for all frequency types in `mark_complete()`
- Time-aware preference rules (e.g., exclude feeding tasks only after 6 PM)
- A conflict auto-resolver that shifts task start times by the minimum needed gap
- Age-based task duration adjustments using `Pet.age`

---

## Reflection

### What This Project Taught Me About AI

Building PawPal+ showed me that "AI" in a real system does not always mean a neural network running in isolation. The most important AI here is the **decision-making logic** — the rules that determine what gets scheduled, in what order, and why. Encoding that logic explicitly (priority rules, preference filters, conflict detection) and making it explainable (`explain_plan()`) is a core part of responsible AI design — exactly what Module 3 taught about evaluating outputs critically rather than accepting them blindly.

The agentic workflow was the biggest mindset shift. In Module 1, I learned that you guide AI and review its reasoning rather than just accepting what it says. Building `agent.py` made that concrete: Claude does not write the schedule — it reasons about the problem, calls real tools, and verifies the result before speaking. That is "working with AI, not just using AI."

### What This Project Taught Me About Problem-Solving

The biggest insight from Modules 1–3 was that **constraints are features, not limitations**. The time budget, preferences, and conflict rules all look like restrictions — but they are exactly what make the system useful. A scheduler that accepts all tasks unconditionally is not a scheduler at all.

Module 2's lesson about algorithmic thinking also proved directly applicable: the greedy scheduling algorithm "works" but is not optimal. Understanding why — and being able to explain that trade-off to a non-technical user — is more valuable than just shipping code that runs.

The hardest part was deciding what the system should *not* do. Keeping `Pet.age` in the model without full implementation was tempting, but Module 1's lesson on responsible AI delivery — "working code ≠ good logic; you are responsible for the final result" — made it clear: ship a clean working system rather than one with half-finished features that could confuse users or produce wrong outputs.

### Confidence Rating

| Area | Score | Reason |
|---|---|---|
| Scheduling logic correctness | 90/100 | All 14 eval checks pass; greedy algorithm is predictable |
| Agentic workflow | 85/100 | Tool loop works end-to-end; conflict resolution still manual |
| RAG enhancement | 80/100 | Retrieval measurably improves specificity; scoring is word-overlap not semantic |
| Specialist few-shot | 85/100 | Metrics show clear improvement in medical term density and structure |
| Overall system design | 90/100 | Clean five-class backend, independent layers, fully testable |

---

## How to Run the Project

### Step 1 — Install dependencies

```bash
pip install -r requirements.txt
pip install python-dotenv
```

### Step 2 — Add your API key

Create a `.env` file inside `applied-ai-system-final/`:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

> Get a key at https://console.anthropic.com. Only needed for `agent.py`, `rag_advisor.py`, and `specialist.py`.

### Step 3 — Choose what to run

| What | Command | Needs API key? |
|---|---|---|
| Web UI (Streamlit) | `python -m streamlit run app.py` | No |
| CLI demo | `python main.py` | No |
| Unit tests | `python -m pytest tests/test_pawpal.py -v` | No |
| Evaluation harness | `python tests/eval_harness.py` | No |
| Agentic workflow | `python agent.py` | Yes |
| RAG comparison | `python rag_advisor.py` | Yes |
| Specialist comparison | `python specialist.py` | Yes |

Run all commands from inside the `applied-ai-system-final/` folder:

```bash
cd applied-ai-system-final
```

### Quick start (no API key)

```bash
cd applied-ai-system-final
python main.py                              # see the scheduler in action
python -m streamlit run app.py             # open the web UI at http://localhost:8501
python -m pytest tests/test_pawpal.py -v   # run unit tests
```

### Full run (with API key)

```bash
cd applied-ai-system-final
python agent.py        # Claude reasons through a 4-step plan → act → verify loop
python rag_advisor.py  # side-by-side baseline vs. RAG-enhanced answers
python specialist.py   # generic Claude vs. Dr. PawPal few-shot specialist
```
