# main.py
# CLI demo script — runs all backend logic without the Streamlit UI.
# Purpose: verify that every class and method in pawpal_system.py works
# correctly before wiring them to app.py.

from pawpal_system import Task, Pet, Owner, Planner

# ── 1. Create an owner ────────────────────────────────────────────────────────
# Preferences are plain strings that map to filter rules in PREFERENCE_RULES.
# "morning walks" means walking tasks are reserved for morning context only.
# "no late feeding" means feeding tasks should be excluded from late scheduling.
owner = Owner(
    name="Jordan",
    available_time=90,
    preferences=["morning walks", "no late feeding"],
)

# ── 2. Create two pets ────────────────────────────────────────────────────────
dog = Pet(name="Mochi", pet_type="dog", age=3)
cat = Pet(name="Luna",  pet_type="cat", age=5)

# ── 3. Add tasks OUT OF ORDER (mixed start_times) to demo sort_by_time ───────
# Tasks are intentionally added in a scrambled time order (10:00, 07:00, 08:00)
# to prove that sort_by_time() reorders them correctly, regardless of insertion order.
dog.add_task(Task("Grooming",       "Brush coat for 15 minutes",    15, "medium", "grooming",  start_time="10:00"))
dog.add_task(Task("Morning walk",   "30-min walk around the block", 30, "high",   "walking",   start_time="07:00"))
dog.add_task(Task("Feed breakfast", "1 cup dry food in bowl",       10, "high",   "feeding",   start_time="08:00"))

cat.add_task(Task("Playtime",       "Feather wand session",         20, "low",    "enrichment",start_time="15:00"))
cat.add_task(Task("Feed breakfast", "Half can wet food",             5, "high",   "feeding",   start_time="08:30"))
# frequency="twice daily" means mark_complete() will schedule the next occurrence same day (+1 day)
cat.add_task(Task("Litter box",     "Clean and replace litter",     10, "medium", "hygiene",   frequency="twice daily", start_time="09:00"))

# ── 4. Register pets with the owner ──────────────────────────────────────────
# Both pets are added so get_all_tasks() returns tasks from both in one flat list.
owner.add_pet(dog)
owner.add_pet(cat)

# ── 5. Generate the schedule ──────────────────────────────────────────────────
# Planner.generate_schedule() runs the full pipeline:
# collect all tasks → sort by priority → apply preference + time constraints → return Schedule.
planner  = Planner()
schedule = planner.generate_schedule(owner)

# ── 6. Print Today's Schedule ─────────────────────────────────────────────────
print(f"\nOwner : {owner.name}  |  Time budget: {owner.available_time} min")
print(f"Pets  : {', '.join(p.name for p in owner.pets)}")
print()

print("Today's Schedule")
print("=" * 40)
elapsed = 0
for i, task in enumerate(schedule.tasks, start=1):
    elapsed += task.duration
    print(f"{i}. {task.name:<20} {task.duration:>3} min  [{task.priority}]")
    print(f"   {task.description}")
print("-" * 40)
print(f"   Total time used : {schedule.total_time} min")
print(f"   Time remaining  : {owner.available_time - schedule.total_time} min")
print("=" * 40)

# ── 7. Sort all tasks by start_time ──────────────────────────────────────────
# get_all_tasks() returns tasks in insertion order (scrambled).
# sort_by_time() reorders them chronologically using the "HH:MM" string key.
all_tasks = owner.get_all_tasks()
sorted_by_time = planner.sort_by_time(all_tasks)

print("\nAll Tasks Sorted by Start Time")
print("=" * 40)
for t in sorted_by_time:
    print(f"  {t.start_time}  {t.name:<20} [{t.priority}]")
print("=" * 40)

# ── 8. Complete tasks — auto-reschedule recurring ones ───────────────────────
# complete_task() marks the task done AND appends a new Task with the next due_date.
# This keeps the pet's task list self-maintaining — no manual re-adding needed.
grooming   = dog.tasks[0]   # Grooming  (daily)   → next occurrence: today + 1
litter_box = cat.tasks[2]   # Litter box (twice daily) → next occurrence: today + 1

dog.complete_task(grooming)
cat.complete_task(litter_box)

print("\nAuto-Reschedule Results")
print("=" * 40)
for t in owner.get_all_tasks():
    status = "DONE" if t.completed else "next"
    print(f"  [{status}] {t.name:<20} due: {t.due_date}  freq: {t.frequency}")
print("=" * 40)

# filter_tasks() lets us query tasks by completion status or pet name.
# completed=False → only pending tasks; completed=True → only finished tasks.
print("\nPending tasks (all pets):")
for t in owner.filter_tasks(completed=False):
    print(f"  - {t.name:<20} due: {t.due_date}")

print("\nCompleted tasks (all pets):")
for t in owner.filter_tasks(completed=True):
    print(f"  - {t.name:<20} due: {t.due_date}")

# pet_name filter narrows results to tasks belonging to a specific pet.
print("\nMochi's tasks only:")
for t in owner.filter_tasks(pet_name="Mochi"):
    status = "done" if t.completed else "pending"
    print(f"  - {t.name} ({status})")

# ── 9. Conflict detection demo ────────────────────────────────────────────────
# Bath starts at 10:00 and runs for 20 min (ends 10:20).
# Nail trim starts at 10:10 — they share a 10-minute window → conflict.
# detect_conflicts() returns warning strings, not exceptions, so the app keeps running.
dog.add_task(Task("Bath",      "Full bath with shampoo", 20, "medium", "grooming", start_time="10:00"))
dog.add_task(Task("Nail trim", "Clip all four paws",     15, "medium", "grooming", start_time="10:10"))

print("\nConflict Detection")
print("=" * 40)
conflicts = planner.detect_conflicts(owner.get_all_tasks())
if conflicts:
    for warning in conflicts:
        print(f"  {warning}")
else:
    print("  No conflicts found.")
print("=" * 40)
