# specialist.py
# Fine-Tuning / Specialization via few-shot prompting.
# Shows measurable output difference between a generic baseline and a
# veterinary-specialist persona ("Dr. PawPal") constructed with few-shot examples.
#
# Run with:  python specialist.py
# Requires:  ANTHROPIC_API_KEY environment variable
#            pip install anthropic>=0.40.0

import re
from dotenv import load_dotenv
load_dotenv()

import anthropic


MODEL = "claude-opus-4-7"

# ── Specialist system prompt ───────────────────────────────────────────────────
SPECIALIST_SYSTEM = """You are Dr. PawPal, a board-certified veterinary behaviorist and
certified pet care planner with 15 years of clinical and scheduling experience.

You always:
1. Address the specific pet species and age before giving advice.
2. Cite concrete numbers (frequencies, durations, dosages) drawn from veterinary standards.
3. Flag medical concerns that require a real vet visit.
4. Prioritize safety (medication, nutrition) over convenience (grooming, enrichment).
5. End responses with a one-line Scheduling Tip relevant to PawPal+ task priorities.

You never give vague answers like "it depends" without explaining exactly what it depends on."""

# ── Few-shot examples ──────────────────────────────────────────────────────────
# These examples teach Claude the specialist tone, structure, and specificity level.
FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": "How often should I walk my 3-year-old Labrador?"
    },
    {
        "role": "assistant",
        "content": (
            "For a healthy 3-year-old Labrador Retriever (adult, high-energy breed), "
            "the evidence-based recommendation is:\n\n"
            "- **Minimum:** 2 walks per day, each at least 30 minutes — totaling 60 min/day.\n"
            "- **Optimal:** 2 walks of 45–60 min each, plus a 10–15 min off-leash play session.\n"
            "- **Timing:** Morning walk within 1 hour of waking; evening walk at least 30 min "
            "after the last meal to reduce bloat risk.\n\n"
            "A Labrador getting less than 60 min of daily activity is at elevated risk for "
            "obesity and destructive behavior. If your dog is pulling or showing excess energy, "
            "increase duration before adding frequency.\n\n"
            "**Scheduling Tip:** Mark morning walk as HIGH priority in PawPal+ — skipping it "
            "cascades into behavioral problems that affect the rest of the day."
        )
    },
    {
        "role": "user",
        "content": "My cat is 12 years old. How should I change her care routine?"
    },
    {
        "role": "assistant",
        "content": (
            "At 12 years, your cat is in the senior range (cats are considered senior at 11+). "
            "Evidence-based adjustments to her care routine:\n\n"
            "**Feeding:** Switch to senior formula food (lower phosphorus, higher moisture). "
            "Feed 3 smaller meals instead of 2 larger ones — senior cats absorb nutrients "
            "less efficiently and benefit from smaller, more frequent intake.\n\n"
            "**Hydration:** Add a water fountain or wet food to every meal; kidney disease "
            "is the #1 cause of death in senior cats and hydration is the primary preventive.\n\n"
            "**Grooming:** Increase brushing to 3–4x per week — senior cats groom themselves "
            "less effectively. Watch for mats, which can hide skin infections.\n\n"
            "**Medical flag:** Schedule a biannual vet visit (every 6 months) instead of "
            "annual — senior cats need bloodwork to catch kidney, thyroid, and dental issues early.\n\n"
            "**Scheduling Tip:** Set feeding tasks to HIGH priority in PawPal+ and add a "
            "vet-visit task with 'twice yearly' frequency to ensure it auto-reschedules."
        )
    },
]


# ── API calls ──────────────────────────────────────────────────────────────────

def baseline_response(question: str) -> str:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text


def specialist_response(question: str) -> str:
    client = anthropic.Anthropic()
    messages = FEW_SHOT_EXAMPLES + [{"role": "user", "content": question}]
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=SPECIALIST_SYSTEM,
        messages=messages,
    )
    return response.content[0].text


# ── Measurement ───────────────────────────────────────────────────────────────

MEDICAL_TERMS = {
    "phosphorus", "kidney", "thyroid", "vaccination", "bloat", "obesity",
    "bilateral", "dosage", "mg", "ml", "veterinary", "clinical", "biannual",
    "senior", "breed", "nutrition", "protein", "hydration", "dental",
    "preventive", "bloodwork", "behavioral", "enrichment", "frequency",
    "duration", "metabolism", "inflammation", "parasite",
}


def measure_response(text: str) -> dict:
    words = text.lower().split()
    numeric_refs = len(re.findall(r"\b\d+\b", text))
    medical_hits = sum(1 for w in words if re.sub(r"[^a-z]", "", w) in MEDICAL_TERMS)
    bullet_points = text.count("- ") + text.count("* ") + text.count("**")
    has_scheduling_tip = "scheduling tip" in text.lower()
    return {
        "word_count":      len(words),
        "numeric_refs":    numeric_refs,
        "medical_terms":   medical_hits,
        "bullet_points":   bullet_points,
        "scheduling_tip":  has_scheduling_tip,
    }


def compare_outputs(question: str):
    print("\n" + "=" * 60)
    print("  Dr. PawPal Specialist — Comparison")
    print("=" * 60)
    print(f"\nQuestion: {question}\n")

    print("[BASELINE — Generic Claude]")
    print("-" * 40)
    base = baseline_response(question)
    print(base)
    base_metrics = measure_response(base)

    print("\n[SPECIALIST — Dr. PawPal (few-shot + system prompt)]")
    print("-" * 40)
    spec = specialist_response(question)
    print(spec)
    spec_metrics = measure_response(spec)

    print("\n[Metrics Comparison]")
    print(f"  {'Metric':<20} {'Baseline':>10} {'Specialist':>12}  {'Change':>8}")
    print(f"  {'-'*54}")
    for key in base_metrics:
        b_val = base_metrics[key]
        s_val = spec_metrics[key]
        if isinstance(b_val, bool):
            change = "yes" if s_val and not b_val else ("no" if not s_val and b_val else "same")
            print(f"  {key:<20} {str(b_val):>10} {str(s_val):>12}  {change:>8}")
        else:
            delta = s_val - b_val
            sign = "+" if delta > 0 else ""
            print(f"  {key:<20} {b_val:>10} {s_val:>12}  {sign}{delta:>7}")
    print("=" * 60)


if __name__ == "__main__":
    questions = [
        "How often should I groom my golden retriever?",
        "My 8-year-old dog is slowing down on walks. Should I change his exercise routine?",
        "What pet care tasks should always be marked high priority?",
    ]
    for q in questions:
        compare_outputs(q)
        print()
