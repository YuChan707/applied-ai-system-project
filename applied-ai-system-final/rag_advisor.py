# rag_advisor.py
# RAG Enhancement — retrieves relevant pet-care knowledge before calling Claude,
# producing measurably richer advice than a plain baseline prompt.
#
# Run with:  python rag_advisor.py
# Requires:  ANTHROPIC_API_KEY environment variable
#            pip install anthropic>=0.40.0

import re
from dotenv import load_dotenv
load_dotenv()
import anthropic


MODEL = "claude-opus-4-7"

# ── Inline knowledge base ──────────────────────────────────────────────────────
# Each entry is a domain-specific document Claude does not have in its weights
# in this structured, task-oriented form. Retrieval adds it to the context.
KNOWLEDGE_BASE = {
    "feeding_guidelines": """
PawPal+ Feeding Guidelines:
- Dogs: Feed 2x daily (morning 7-9 AM, evening 5-7 PM). Puppies under 6 months need 3x daily.
- Cats: Feed 2-3x daily. Wet food provides hydration; dry food supports dental health.
- Never feed within 1 hour of vigorous exercise (risk of bloat in dogs).
- High-priority feeding tasks should never be skipped; low-priority treats can be deferred.
- Medication often must accompany feeding — always schedule med tasks adjacent to meal tasks.
- Senior pets (dogs 8+, cats 10+) may need smaller, more frequent meals.
""",
    "exercise_guidelines": """
PawPal+ Exercise Guidelines:
- Adult dogs: 30-60 min of walking per day split across 2 sessions minimum.
- Puppies: 5 min per month of age, twice daily (e.g., 4-month-old = 20 min max per session).
- Senior dogs: shorter but more frequent low-impact walks; monitor for limping.
- Cats: 10-20 min of interactive play per day (feather wand, laser pointer).
- Never schedule intense exercise within 30 min of meals for dogs.
- Morning walks are highest value — sets behavior tone for the day.
- Walking tasks are time-sensitive; they should be high priority if the pet hasn't gone out.
""",
    "grooming_guidelines": """
PawPal+ Grooming Guidelines:
- Short-coat dogs: brush 1-2x per week, bathe monthly.
- Long-coat dogs: brush daily to prevent matting, bathe every 3-4 weeks.
- Cats: self-groom but benefit from weekly brushing; longhairs need daily brushing.
- Nail trims every 3-4 weeks for dogs; cats monthly or as needed.
- Bath and nail trim should NOT be scheduled in the same 30-min window — both are stressful.
- Never schedule bath within 2 hours of other grooming tasks (drying time needed).
- Grooming tasks are medium priority unless a medical issue (skin infection, matting) is present.
""",
    "health_guidelines": """
PawPal+ Health & Medication Guidelines:
- Medication tasks are ALWAYS high priority — missing a dose can harm the pet.
- Ear cleaning: weekly for floppy-eared dogs (Beagles, Spaniels); monthly for others.
- Dental brushing: ideally daily, minimum 3x per week for dogs.
- Litter box cleaning: daily scooping; full change weekly. Cats refuse dirty boxes.
- Senior pets need more frequent health check tasks scheduled.
- If a task has frequency 'twice daily', the second occurrence must be at least 6 hours after the first.
- Vet visit tasks should be scheduled first thing — they anchor the rest of the day.
""",
    "scheduling_best_practices": """
PawPal+ Scheduling Best Practices:
- Always slot high-priority tasks before medium or low tasks — never sacrifice medication or feeding.
- Build in 5-10 min buffer between back-to-back tasks to account for setup/cleanup.
- Prefer clustering tasks by location: all outdoor tasks together, all indoor tasks together.
- If time budget is tight, cut enrichment (play) first, then grooming, never feeding or medication.
- Conflict detection flags are warnings — the owner decides how to resolve them.
- Recurring tasks ('daily', 'twice daily') must always appear in the next day's schedule automatically.
""",
}


# ── Retrieval: simple TF-IDF word-overlap scoring ─────────────────────────────

def tokenize(text: str) -> set:
    return set(re.findall(r"\b[a-z]{3,}\b", text.lower()))


def score_document(query_tokens: set, document: str) -> float:
    doc_tokens = tokenize(document)
    if not doc_tokens:
        return 0.0
    overlap = len(query_tokens & doc_tokens)
    return overlap / (len(query_tokens | doc_tokens) + 1e-9)


def retrieve_relevant_docs(query: str, top_k: int = 2) -> list[tuple[str, str]]:
    query_tokens = tokenize(query)
    scored = [
        (name, doc, score_document(query_tokens, doc))
        for name, doc in KNOWLEDGE_BASE.items()
    ]
    scored.sort(key=lambda x: x[2], reverse=True)
    return [(name, doc) for name, doc, _ in scored[:top_k]]


# ── Baseline vs RAG comparison ────────────────────────────────────────────────

def baseline_response(question: str) -> str:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text


def rag_response(question: str) -> tuple[str, list[str]]:
    retrieved = retrieve_relevant_docs(question, top_k=2)
    doc_names = [name for name, _ in retrieved]
    context = "\n\n".join(
        f"--- {name.replace('_', ' ').title()} ---\n{doc}"
        for name, doc in retrieved
    )

    augmented_prompt = (
        f"Use the following PawPal+ knowledge base excerpts to answer the question "
        f"precisely and with specific numbers or rules where possible.\n\n"
        f"{context}\n\n"
        f"Question: {question}"
    )

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": augmented_prompt}],
    )
    return response.content[0].text, doc_names


def compare(question: str):
    print("\n" + "=" * 60)
    print("  PawPal+ RAG Advisor — Comparison")
    print("=" * 60)
    print(f"\nQuestion: {question}\n")

    print("[BASELINE — No retrieval]")
    print("-" * 40)
    baseline = baseline_response(question)
    print(baseline)
    print(f"\n(Word count: {len(baseline.split())})")

    print("\n[RAG ENHANCED — With retrieved knowledge]")
    print("-" * 40)
    enhanced, sources = rag_response(question)
    print(enhanced)
    print(f"\n(Word count: {len(enhanced.split())})")
    print(f"(Sources retrieved: {', '.join(sources)})")

    # Measure specificity improvement: count numeric tokens (specific guidelines)
    def count_specifics(text):
        return len(re.findall(r"\b\d+\b", text))

    b_specifics = count_specifics(baseline)
    e_specifics = count_specifics(enhanced)
    print(f"\n[Specificity metric — numeric references in answer]")
    print(f"  Baseline : {b_specifics} numbers")
    print(f"  RAG      : {e_specifics} numbers")
    improvement = e_specifics - b_specifics
    if improvement > 0:
        print(f"  RAG adds {improvement} more specific data points.")
    elif improvement == 0:
        print(f"  Similar specificity — both answers are equally concrete.")
    else:
        print(f"  Baseline was more specific in this case.")
    print("=" * 60)


if __name__ == "__main__":
    questions = [
        "How often should I groom my long-coat dog, and can I combine bath and nail trim in one session?",
        "My senior cat is 11 years old — how should I adjust her feeding schedule?",
        "I only have 30 minutes today. Which pet care tasks should I prioritize?",
    ]
    for q in questions:
        compare(q)
        print()
