# tests/eval_harness.py
# Test Harness — runs predefined scheduling scenarios and prints pass/fail scores.
# No Claude API dependency needed: tests deterministic backend logic only.
#
# Run with:   python tests/eval_harness.py
#         or: python -m pytest tests/eval_harness.py -v

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from pawpal_system import Task, Pet, Owner, Planner


def make_task(name, duration, priority, category, start_time="08:00", frequency="daily"):
    return Task(name, f"{name} description", duration, priority, category,
                frequency=frequency, start_time=start_time)


def run_scenario(scenario_name, owner, expected_checks):
    planner = Planner()
    schedule = planner.generate_schedule(owner)
    conflicts = planner.detect_conflicts(schedule.tasks)

    results = []
    for check_name, check_fn in expected_checks:
        passed = check_fn(schedule, conflicts)
        results.append((check_name, passed))

    return results


def scenario_1_basic_priority():
    """High-priority tasks must be selected before low-priority ones."""
    owner = Owner("Alex", available_time=60, preferences=[])
    pet = Pet("Rex", "dog", 4)
    pet.add_task(make_task("Feed breakfast", 10, "high", "feeding"))
    pet.add_task(make_task("Morning walk", 30, "high", "walking"))
    pet.add_task(make_task("Playtime", 25, "low", "enrichment"))
    owner.add_pet(pet)

    checks = [
        (
            "Feed breakfast is scheduled (high priority)",
            lambda s, c: any(t.name == "Feed breakfast" for t in s.tasks),
        ),
        (
            "Morning walk is scheduled (high priority)",
            lambda s, c: any(t.name == "Morning walk" for t in s.tasks),
        ),
        (
            "Playtime is excluded (low priority, budget exceeded)",
            lambda s, c: all(t.name != "Playtime" for t in s.tasks),
        ),
    ]
    return run_scenario("Scenario 1 — Basic Priority", owner, checks)


def scenario_2_preference_filtering():
    """'no late feeding' preference must exclude all feeding category tasks."""
    owner = Owner("Sam", available_time=120, preferences=["no late feeding"])
    pet = Pet("Whiskers", "cat", 2)
    pet.add_task(make_task("Feed breakfast", 5, "high", "feeding"))
    pet.add_task(make_task("Litter box", 10, "medium", "hygiene"))
    pet.add_task(make_task("Playtime", 15, "low", "enrichment"))
    owner.add_pet(pet)

    checks = [
        (
            "Feed breakfast excluded by 'no late feeding' preference",
            lambda s, c: all(t.name != "Feed breakfast" for t in s.tasks),
        ),
        (
            "Litter box still scheduled (not affected by preference)",
            lambda s, c: any(t.name == "Litter box" for t in s.tasks),
        ),
    ]
    return run_scenario("Scenario 2 — Preference Filtering", owner, checks)


def scenario_3_time_budget_enforcement():
    """Tasks that exceed the available time budget must be excluded."""
    owner = Owner("Taylor", available_time=30, preferences=[])
    pet = Pet("Buddy", "dog", 5)
    pet.add_task(make_task("Short walk", 20, "high", "walking"))
    pet.add_task(make_task("Long groom", 60, "medium", "grooming"))
    owner.add_pet(pet)

    checks = [
        (
            "Short walk fits within 30-min budget",
            lambda s, c: any(t.name == "Short walk" for t in s.tasks),
        ),
        (
            "Long groom excluded (60 min > 10 min remaining after short walk)",
            lambda s, c: all(t.name != "Long groom" for t in s.tasks),
        ),
        (
            "Total time does not exceed budget of 30 min",
            lambda s, c: s.total_time <= 30,
        ),
    ]
    return run_scenario("Scenario 3 — Time Budget Enforcement", owner, checks)


def scenario_4_conflict_detection():
    """Overlapping task windows must generate a conflict warning."""
    owner = Owner("Morgan", available_time=120, preferences=[])
    pet = Pet("Max", "dog", 3)
    # Bath: 10:00–10:20, Nail trim: 10:10–10:25 → overlap 10:10–10:20
    pet.add_task(make_task("Bath", 20, "medium", "grooming", start_time="10:00"))
    pet.add_task(make_task("Nail trim", 15, "medium", "grooming", start_time="10:10"))
    owner.add_pet(pet)

    planner = Planner()
    schedule = planner.generate_schedule(owner)
    all_tasks = owner.get_all_tasks()
    conflicts = planner.detect_conflicts(all_tasks)

    checks = [
        (
            "Conflict detected between Bath (10:00) and Nail trim (10:10)",
            lambda s, c: len(c) > 0,
        ),
        (
            "Conflict warning mentions 'Bath'",
            lambda s, c: any("Bath" in w for w in c),
        ),
        (
            "Conflict warning mentions 'Nail trim'",
            lambda s, c: any("Nail trim" in w for w in c),
        ),
    ]
    return [(name, check_fn(schedule, conflicts)) for name, check_fn in checks]


def scenario_5_multi_pet_scheduling():
    """Tasks from multiple pets must all be considered and prioritized together."""
    owner = Owner("Jordan", available_time=60, preferences=[])
    dog = Pet("Mochi", "dog", 3)
    cat = Pet("Luna", "cat", 5)
    dog.add_task(make_task("Morning walk", 30, "high", "walking"))
    cat.add_task(make_task("Feed breakfast", 5, "high", "feeding"))
    cat.add_task(make_task("Litter box", 10, "medium", "hygiene"))
    owner.add_pet(dog)
    owner.add_pet(cat)

    checks = [
        (
            "Morning walk from dog included",
            lambda s, c: any(t.name == "Morning walk" for t in s.tasks),
        ),
        (
            "Feed breakfast from cat included",
            lambda s, c: any(t.name == "Feed breakfast" for t in s.tasks),
        ),
        (
            "Schedule draws from both pets",
            lambda s, c: len(s.tasks) >= 2,
        ),
    ]
    return run_scenario("Scenario 5 — Multi-Pet Scheduling", owner, checks)


def print_results(scenario_name, results):
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\n{scenario_name}")
    print("-" * 50)
    for check_name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {check_name}")
    print(f"  Score: {passed}/{total}")
    return passed, total


def main():
    print("=" * 60)
    print("  PawPal+ Evaluation Harness")
    print("=" * 60)

    all_passed = 0
    all_total = 0

    scenarios = [
        ("Scenario 1 — Basic Priority Scheduling", scenario_1_basic_priority),
        ("Scenario 2 — Preference Filtering",      scenario_2_preference_filtering),
        ("Scenario 3 — Time Budget Enforcement",   scenario_3_time_budget_enforcement),
        ("Scenario 4 — Conflict Detection",        scenario_4_conflict_detection),
        ("Scenario 5 — Multi-Pet Scheduling",      scenario_5_multi_pet_scheduling),
    ]

    for name, fn in scenarios:
        results = fn()
        p, t = print_results(name, results)
        all_passed += p
        all_total += t

    print("\n" + "=" * 60)
    print(f"  TOTAL SCORE: {all_passed}/{all_total}")
    pct = round(all_passed / all_total * 100)
    print(f"  PASS RATE  : {pct}%")
    if pct == 100:
        print("  RESULT     : ALL CHECKS PASSED")
    else:
        print(f"  RESULT     : {all_total - all_passed} CHECK(S) FAILED")
    print("=" * 60)


if __name__ == "__main__":
    main()
