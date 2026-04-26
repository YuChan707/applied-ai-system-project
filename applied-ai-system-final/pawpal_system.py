# pawpal_system.py
# Backend logic layer for PawPal+.
# All classes live here so they can be tested independently via main.py
# before being connected to the Streamlit UI in app.py.

from typing import List, Optional
from datetime import date, timedelta

# Maps priority labels to integers so Python's sorted() can compare them.
# Lower number = higher urgency: high=0 beats medium=1 beats low=2.
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

# Each key is a plain-English preference the owner can express.
# The value is a lambda that returns True when a task should be EXCLUDED.
# Storing rules as lambdas makes it easy to add new preferences without
# touching the Planner — just add a new key here.
PREFERENCE_RULES = {
    "no late feeding": lambda t: t.category == "feeding",
    "morning walks":   lambda t: t.category == "walking",
}


class Task:
    def __init__(
        self,
        name: str,
        description: str,
        duration: int,
        priority: str,
        category: str,
        frequency: str = "daily",
        start_time: str = "08:00",
        due_date: date = None,
    ):
        """Initialize a Task with its name, description, duration, priority, category, frequency, and start time."""
        self.name = name
        self.description = description
        self.duration = duration        # in minutes — used for time-budget math
        self.priority = priority        # "high", "medium", "low" — drives sort order
        self.category = category        # "feeding", "grooming", "walking", etc. — used by preference rules
        self.frequency = frequency      # "daily", "twice daily", "weekly" — drives recurrence logic
        self.start_time = start_time    # "HH:MM" — used for conflict detection and time sorting
        # Default to today so every task has a concrete anchor for timedelta math.
        self.due_date = due_date or date.today()
        self.completed = False

    def update_priority(self, new_priority: str) -> None:
        """Validate and update the task's priority level."""
        # Guard against typos — only accept values that exist in PRIORITY_ORDER.
        if new_priority not in PRIORITY_ORDER:
            raise ValueError(f"priority must be one of {list(PRIORITY_ORDER)}")
        self.priority = new_priority

    # Maps frequency strings to the number of days until the next occurrence.
    # Stored on the class so mark_complete() can look it up without any imports.
    RECURRENCE_DAYS = {"daily": 1, "twice daily": 1, "weekly": 7}

    def mark_complete(self) -> Optional["Task"]:
        """Mark this task complete and return a new Task for the next occurrence, or None if not recurring."""
        self.completed = True

        # Look up how many days until this task should repeat.
        days = self.RECURRENCE_DAYS.get(self.frequency)

        # If the frequency isn't in the map (e.g. a one-off task), there is
        # no next occurrence — return None so the caller knows to skip appending.
        if days is None:
            return None

        # timedelta adds exactly `days` calendar days to the current due_date,
        # correctly handling month boundaries and leap years.
        next_due = self.due_date + timedelta(days=days)

        # Return a fresh Task with identical settings but the new due date
        # so the pet's task list always has an upcoming instance ready.
        return Task(
            name=self.name,
            description=self.description,
            duration=self.duration,
            priority=self.priority,
            category=self.category,
            frequency=self.frequency,
            start_time=self.start_time,
            due_date=next_due,
        )

    def __repr__(self) -> str:
        """Return a concise string representation showing name, duration, priority, and status."""
        status = "done" if self.completed else "pending"
        return f"Task({self.name!r}, {self.duration}min, priority={self.priority}, {status})"


class Pet:
    def __init__(self, name: str, pet_type: str, age: int):
        """Initialize a Pet with its name, type, and age."""
        self.name = name
        self.pet_type = pet_type        # "dog", "cat", etc.
        self.age = age
        self.tasks: List[Task] = []     # all tasks belonging to this pet

    def add_task(self, task: Task) -> None:
        """Append a task to this pet's task list."""
        self.tasks.append(task)

    def complete_task(self, task: Task) -> None:
        """Mark a task complete and automatically add the next occurrence if it recurs."""
        # mark_complete() returns the next Task instance or None.
        # Appending here keeps recurrence logic inside the model layer,
        # so callers don't need to know about the scheduling rules.
        next_task = task.mark_complete()
        if next_task:
            self.tasks.append(next_task)

    def __repr__(self) -> str:
        """Return a concise string representation showing name, type, and task count."""
        return f"Pet({self.name!r}, {self.pet_type}, {len(self.tasks)} tasks)"


class Owner:
    def __init__(self, name: str, available_time: int, preferences: List[str] = None):
        """Initialize an Owner with their name, daily time budget, and care preferences."""
        self.name = name
        self.available_time = available_time    # total minutes the owner has today
        # Default to empty list so callers don't need to pass preferences explicitly.
        self.preferences = preferences or []
        self.pets: List[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self.pets.append(pet)

    def get_all_tasks(self) -> List[Task]:
        """Return every task across all owned pets."""
        # Flatten tasks from every pet into one list so the Planner
        # can sort and filter them without caring which pet they belong to.
        all_tasks = []
        for pet in self.pets:
            all_tasks.extend(pet.tasks)
        return all_tasks

    def filter_tasks(self, completed: bool = None, pet_name: str = None) -> List[Task]:
        """Return tasks filtered by completion status and/or pet name."""
        results = []
        for pet in self.pets:
            # Skip pets that don't match the requested name.
            # If pet_name is None, include all pets.
            if pet_name and pet.name != pet_name:
                continue
            for task in pet.tasks:
                # completed=None means "return all regardless of status".
                # Otherwise only include tasks that match the requested status.
                if completed is None or task.completed == completed:
                    results.append(task)
        return results

    def __repr__(self) -> str:
        """Return a concise string representation showing name, pet count, and time budget."""
        return f"Owner({self.name!r}, {len(self.pets)} pets, {self.available_time}min available)"


class Schedule:
    def __init__(self, tasks: List[Task]):
        """Initialize a Schedule from a list of tasks and compute total time."""
        self.tasks = tasks
        # Sum durations once at construction so total_time is always in sync
        # with self.tasks — no risk of it drifting if tasks were mutated.
        self.total_time = sum(t.duration for t in tasks)

    def display_plan(self) -> None:
        """Print each scheduled task with a running time tracker."""
        print(f"\n{'='*40}")
        print(f"  Daily Schedule  ({self.total_time} min total)")
        print(f"{'='*40}")
        elapsed = 0
        for i, task in enumerate(self.tasks, start=1):
            print(
                f"{i}. [{task.priority.upper():6}] {task.name} "
                f"({task.duration} min) — {task.category}"
            )
            print(f"   {task.description}")
            elapsed += task.duration
            print(f"   Cumulative time: {elapsed} min")
        print(f"{'='*40}\n")

    def explain_plan(self) -> None:
        """Explain why each task was selected and how it was ordered."""
        # Gives the owner a human-readable reason for each scheduling decision,
        # making the system transparent rather than a black box.
        print(f"\n{'='*40}")
        print("  Schedule Explanation")
        print(f"{'='*40}")
        for i, task in enumerate(self.tasks, start=1):
            print(
                f"{i}. '{task.name}' was scheduled because it is a "
                f"{task.priority}-priority task (category: {task.category}, "
                f"frequency: {task.frequency})."
            )
        print(f"{'='*40}\n")

    def __repr__(self) -> str:
        """Return a concise string representation showing task count and total duration."""
        return f"Schedule({len(self.tasks)} tasks, {self.total_time} min)"


class Planner:
    def __init__(self, constraints: Optional[dict] = None):
        """Initialize the Planner with an optional dictionary of scheduling constraints."""
        # Default to empty dict so the Planner works without any extra config.
        self.constraints = constraints or {}

    def sort_tasks(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks by priority (high → medium → low), then by duration (shortest first)."""
        # Tuple key: first compare priority rank (0/1/2), then duration.
        # Sorting by duration within the same priority fills the time budget
        # more efficiently — shorter tasks leave room for more items.
        return sorted(tasks, key=lambda t: (PRIORITY_ORDER[t.priority], t.duration))

    def sort_by_time(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks by their start_time in HH:MM format, earliest first."""
        # "HH:MM" strings sort correctly as plain strings because the format
        # is zero-padded — no date parsing or conversion needed.
        return sorted(tasks, key=lambda t: t.start_time)

    def apply_constraints(self, tasks: List[Task], available_time: int, preferences: List[str] = None) -> List[Task]:
        """Filter tasks by owner preferences, then keep only tasks that fit within available time."""
        # Step 1 — preference filter: remove tasks the owner has opted out of.
        # Each preference maps to a rule lambda in PREFERENCE_RULES.
        # Unknown preferences are silently skipped so new UI options don't crash old code.
        if preferences:
            for pref in preferences:
                rule = PREFERENCE_RULES.get(pref)
                if rule:
                    tasks = [t for t in tasks if not rule(t)]

        # Step 2 — time-budget filter: greedy selection.
        # Tasks arrive already sorted by priority, so the most important ones
        # are picked first and lower-priority ones fill whatever time remains.
        selected = []
        time_used = 0
        for task in tasks:
            if time_used + task.duration <= available_time:
                selected.append(task)
                time_used += task.duration
        return selected

    def detect_conflicts(self, tasks: List[Task]) -> List[str]:
        """Return a list of warning strings for any tasks whose time windows overlap."""
        def to_minutes(hhmm: str) -> int:
            """Convert a 'HH:MM' string to total minutes since midnight."""
            h, m = hhmm.split(":")
            return int(h) * 60 + int(m)

        warnings = []
        # Check every unique pair of tasks (i, j where j > i) to avoid
        # reporting the same conflict twice (A vs B and B vs A).
        for i in range(len(tasks)):
            for j in range(i + 1, len(tasks)):
                a, b = tasks[i], tasks[j]
                a_start = to_minutes(a.start_time)
                b_start = to_minutes(b.start_time)
                a_end = a_start + a.duration
                b_end = b_start + b.duration

                # Standard interval overlap formula:
                # Two ranges [a_start, a_end) and [b_start, b_end) overlap
                # if and only if a_start < b_end AND b_start < a_end.
                # Tasks that share only an endpoint (one ends exactly when
                # the other starts) are NOT flagged — that is valid back-to-back scheduling.
                if a_start < b_end and b_start < a_end:
                    warnings.append(
                        f"WARNING: '{a.name}' ({a.start_time}, {a.duration}min) "
                        f"overlaps with '{b.name}' ({b.start_time}, {b.duration}min)"
                    )
        # Return warnings as strings rather than raising an exception so the
        # app stays running and the owner can decide how to resolve the conflict.
        return warnings

    def generate_schedule(self, owner: Owner) -> Schedule:
        """Collect all tasks from the owner's pets, sort, filter, and check for conflicts."""
        # Pipeline: collect → sort by priority → apply constraints → wrap in Schedule.
        all_tasks = owner.get_all_tasks()
        sorted_tasks = self.sort_tasks(all_tasks)
        feasible_tasks = self.apply_constraints(sorted_tasks, owner.available_time, owner.preferences)
        return Schedule(feasible_tasks)
