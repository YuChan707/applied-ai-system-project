# agent.py
# Agentic Workflow — multi-step reasoning with observable tool calls.
# Claude plans → acts (calls real scheduler tools) → verifies the result.
#
# Run with:  python agent.py
# Requires:  ANTHROPIC_API_KEY environment variable
#            pip install anthropic>=0.40.0

import json
import os
from dotenv import load_dotenv
load_dotenv()
import anthropic


from pawpal_system import Task, Pet, Owner, Planner

MODEL = "claude-opus-4-7"

# ── Tool definitions ───────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "analyze_owner_situation",
        "description": (
            "Analyze an owner's pets and available time to identify the most "
            "critical care needs for today. Returns a priority summary."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "owner_name":      {"type": "string",  "description": "Owner's name"},
                "available_time":  {"type": "integer", "description": "Minutes available today"},
                "pet_summaries":   {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pet_name":   {"type": "string"},
                            "pet_type":   {"type": "string"},
                            "task_count": {"type": "integer"},
                            "high_priority_tasks": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    },
                    "description": "One entry per pet with their task summary"
                }
            },
            "required": ["owner_name", "available_time", "pet_summaries"]
        }
    },
    {
        "name": "prioritize_tasks",
        "description": (
            "Given a raw task list, return them sorted by priority (high → medium → low) "
            "and then by duration (shortest first). Shows the intended scheduling order."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name":     {"type": "string"},
                            "duration": {"type": "integer"},
                            "priority": {"type": "string"},
                            "category": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["tasks"]
        }
    },
    {
        "name": "run_scheduler",
        "description": (
            "Run the PawPal+ scheduling engine to generate an optimized daily care plan "
            "that respects the time budget and owner preferences."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "owner_name":     {"type": "string"},
                "available_time": {"type": "integer"},
                "preferences":    {"type": "array", "items": {"type": "string"}},
                "pets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name":     {"type": "string"},
                            "pet_type": {"type": "string"},
                            "age":      {"type": "integer"},
                            "tasks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name":       {"type": "string"},
                                        "description":{"type": "string"},
                                        "duration":   {"type": "integer"},
                                        "priority":   {"type": "string"},
                                        "category":   {"type": "string"},
                                        "start_time": {"type": "string"},
                                        "frequency":  {"type": "string"}
                                    },
                                    "required": ["name", "description", "duration",
                                                 "priority", "category"]
                                }
                            }
                        }
                    }
                }
            },
            "required": ["owner_name", "available_time", "pets"]
        }
    },
    {
        "name": "verify_schedule",
        "description": (
            "Verify the generated schedule: check for conflicts, confirm the budget "
            "is respected, and validate that all high-priority tasks were included."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "scheduled_tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name":       {"type": "string"},
                            "duration":   {"type": "integer"},
                            "priority":   {"type": "string"},
                            "start_time": {"type": "string"}
                        }
                    }
                },
                "available_time": {"type": "integer"},
                "preferences":    {"type": "array", "items": {"type": "string"}}
            },
            "required": ["scheduled_tasks", "available_time"]
        }
    }
]


# ── Tool implementations ───────────────────────────────────────────────────────

def analyze_owner_situation(owner_name, available_time, pet_summaries):
    high_priority_all = []
    for p in pet_summaries:
        high_priority_all.extend(p.get("high_priority_tasks", []))

    lines = [
        f"Owner {owner_name} has {available_time} min available today.",
        f"Total pets: {len(pet_summaries)}",
        f"High-priority tasks across all pets: {', '.join(high_priority_all) if high_priority_all else 'none'}",
        "Recommendation: Schedule all high-priority tasks first; use remaining time for medium/low.",
    ]
    return "\n".join(lines)


def prioritize_tasks(tasks):
    from pawpal_system import PRIORITY_ORDER
    sorted_t = sorted(tasks, key=lambda t: (PRIORITY_ORDER.get(t["priority"], 9), t["duration"]))
    lines = ["Priority-sorted task order:"]
    for i, t in enumerate(sorted_t, 1):
        lines.append(f"  {i}. [{t['priority'].upper():6}] {t['name']} ({t['duration']} min)")
    return "\n".join(lines)


def run_scheduler(owner_name, available_time, pets, preferences=None):
    owner = Owner(owner_name, available_time, preferences or [])
    for p_data in pets:
        pet = Pet(p_data["name"], p_data["pet_type"], p_data.get("age", 0))
        for t_data in p_data.get("tasks", []):
            task = Task(
                name=t_data["name"],
                description=t_data.get("description", ""),
                duration=t_data["duration"],
                priority=t_data["priority"],
                category=t_data["category"],
                frequency=t_data.get("frequency", "daily"),
                start_time=t_data.get("start_time", "08:00"),
            )
            pet.add_task(task)
        owner.add_pet(pet)

    planner = Planner()
    schedule = planner.generate_schedule(owner)

    lines = [f"Generated schedule ({schedule.total_time} min of {available_time} min used):"]
    for i, t in enumerate(schedule.tasks, 1):
        lines.append(f"  {i}. [{t.priority.upper():6}] {t.name} ({t.duration} min, {t.start_time})")
    lines.append(f"Time remaining: {available_time - schedule.total_time} min")
    return "\n".join(lines)


def verify_schedule(scheduled_tasks, available_time, preferences=None):
    total_time = sum(t["duration"] for t in scheduled_tasks)
    issues = []

    if total_time > available_time:
        issues.append(f"BUDGET EXCEEDED: {total_time} min > {available_time} min")

    # Check for overlapping time windows
    def to_min(hhmm):
        h, m = hhmm.split(":")
        return int(h) * 60 + int(m)

    for i in range(len(scheduled_tasks)):
        for j in range(i + 1, len(scheduled_tasks)):
            a, b = scheduled_tasks[i], scheduled_tasks[j]
            a_start = to_min(a.get("start_time", "08:00"))
            b_start = to_min(b.get("start_time", "08:00"))
            a_end = a_start + a["duration"]
            b_end = b_start + b["duration"]
            if a_start < b_end and b_start < a_end:
                issues.append(f"CONFLICT: '{a['name']}' overlaps '{b['name']}'")

    high_tasks = [t["name"] for t in scheduled_tasks if t["priority"] == "high"]

    lines = ["Verification Report:"]
    lines.append(f"  Total time used : {total_time} min / {available_time} min")
    lines.append(f"  High-priority tasks included: {', '.join(high_tasks) if high_tasks else 'none'}")
    if issues:
        lines.append("  ISSUES FOUND:")
        for issue in issues:
            lines.append(f"    - {issue}")
    else:
        lines.append("  No issues found — schedule is valid.")
    return "\n".join(lines)


# ── Tool dispatch ──────────────────────────────────────────────────────────────

def execute_tool(tool_name, tool_input):
    if tool_name == "analyze_owner_situation":
        return analyze_owner_situation(**tool_input)
    elif tool_name == "prioritize_tasks":
        return prioritize_tasks(**tool_input)
    elif tool_name == "run_scheduler":
        return run_scheduler(**tool_input)
    elif tool_name == "verify_schedule":
        return verify_schedule(**tool_input)
    else:
        return f"Unknown tool: {tool_name}"


# ── Agentic loop ───────────────────────────────────────────────────────────────

def run_agent(user_request: str):
    print("\n" + "=" * 60)
    print("  PawPal+ Agentic Workflow")
    print("=" * 60)
    print(f"\nUser request: {user_request}\n")

    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": user_request}]

    system_prompt = (
        "You are PawPal+, an AI pet care scheduling assistant. "
        "When asked to create a schedule, use your tools in order:\n"
        "1. analyze_owner_situation — understand what's critical\n"
        "2. prioritize_tasks — sort tasks by importance\n"
        "3. run_scheduler — generate the actual schedule\n"
        "4. verify_schedule — confirm no conflicts or budget issues\n"
        "After all tool calls, provide a final plain-language summary of the schedule."
    )

    step = 0
    while True:
        step += 1
        print(f"[Step {step}] Calling Claude...")

        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        # Append Claude's response to the conversation
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Extract final text response
            for block in response.content:
                if block.type == "text":
                    print(f"\n[Claude's Final Response]\n{block.text}")
            break

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    print(f"  -> Tool call: {tool_name}")
                    print(f"     Input: {json.dumps(tool_input, indent=6)[:300]}...")

                    result = execute_tool(tool_name, tool_input)
                    print(f"     Result:\n       {result.replace(chr(10), chr(10) + '       ')}")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})
        else:
            print(f"  Unexpected stop_reason: {response.stop_reason}")
            break

    print("\n" + "=" * 60)


# ── Demo ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    request = """
    Please create an optimized daily care schedule for Jordan.
    Jordan has 90 minutes available today and prefers no late feeding.

    Pets:
    - Mochi (dog, age 3) with tasks:
        * Morning walk: 30 min, high priority, walking, starts 07:00
        * Feed breakfast: 10 min, high priority, feeding, starts 08:00
        * Grooming: 15 min, medium priority, grooming, starts 10:00
    - Luna (cat, age 5) with tasks:
        * Feed breakfast: 5 min, high priority, feeding, starts 08:30
        * Litter box: 10 min, medium priority, hygiene, starts 09:00
        * Playtime: 20 min, low priority, enrichment, starts 15:00

    Use your tools to analyze the situation, prioritize tasks, run the scheduler,
    and verify the result before giving me the final schedule.
    """
    run_agent(request)
