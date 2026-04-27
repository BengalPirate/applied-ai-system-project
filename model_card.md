# Model Card: MoodMatch Agent (Applied AI System)

## 1. Model name

**MoodMatch Agent v2.0** — an agentic extension of *MoodMatch
Recommender v1.0* (my Module 3 starter project).

## 2. Intended use

- **What it does:** given a user profile (genre / mood / energy /
  acousticness preference, optionally a free-text context like "music
  for the gym"), the agent produces 5 ranked song recommendations
  drawn from a 25-song local catalog, plus a confidence label and a
  full observable trace of every reasoning step.
- **Who it is for:** the AI-110 grader, my portfolio, and anyone using
  this repo as a teaching example for agentic workflows, RAG, persona
  specialization, and evaluation harnesses on a tiny dataset.
- **What it is *not* for:** real consumer music recommendations.
  The catalog is too small, the data is Western-only, and the agent has
  no notion of artist popularity, lyrics, language, or licensing.

## 3. How the model works (plain language)

For each request the system runs a five-step loop:

1. **Plan.** It picks one of five "personas" (default, discovery,
   comfort, workout, study) — either explicitly chosen by the caller
   or auto-routed from the user's free-text context using few-shot
   keyword overlap. The chosen persona supplies a starting set of
   weights that decide how much each feature (genre, mood, energy,
   acoustic, valence) matters. It also retrieves up to three relevant
   passages from a curated knowledge base via TF-IDF, so the agent has
   text-based hints (for example, "for study contexts prefer lofi /
   ambient / instrumental jazz, energy 0.25–0.5").
2. **Act.** It scores every song with those weights, applies any
   persona-specific penalties (the workout persona, for example,
   subtracts 2.0 points from any song below 0.7 energy), and ranks
   the catalog. It returns the top 5.
3. **Reflect.** It computes a confidence score from four signals: how
   strong the top score is, how big the gap is from #1 to #5, how many
   distinct genres are in the top 5, and how many distinct artists.
   The confidence comes back as both a number (0.0–1.0) and a label
   (very-low / low / medium / high), with notes such as "low genre
   diversity (filter-bubble risk)".
4. **Refine** (only if confidence is below the threshold). It nudges
   weights based on the failure mode: low diversity drops the genre
   weight; low top-score raises valence; low artist diversity activates
   a per-artist repeat penalty. It then re-runs Act and Reflects again.
5. **Finalize.** It applies the persona's tone prefix to each
   explanation ("For deep focus:", "You might also enjoy", "Sticking
   with what you love:") and returns an `AgentResult` containing the
   recommendations, the confidence report, and the full step-by-step
   trace.

## 4. Data

- **Catalog:** `data/songs.csv` with 25 songs across 18 genres
  (pop, lofi, rock, ambient, jazz, synthwave, indie pop, metal,
  reggae, edm, blues, classical, dubstep, country, r&b, punk, latin,
  gothic, tropical house, jazz fusion). Same catalog as v1.0.
- **Knowledge base:** `data/knowledge_base.md` with 11 hand-curated
  passages added for this project. Examples: "lofi listener tendencies",
  "low-data genre fallback", "discovery vs comfort tradeoff",
  "workout and high-tempo guidance".
- **Whose taste does it reflect?** Mine and the original course
  starter's. It is heavily weighted toward Western, English-language
  popular music. There is no hip-hop, K-pop, afrobeats, or
  non-English-language content. Any conclusions a user draws from
  this system will inherit those omissions.

## 5. Strengths

- **Observability.** Every recommendation comes with an `AgentTrace`
  showing persona choice, retrieved KB passages, weights used, top
  scores, confidence breakdown, and any refinement decisions.
- **Reproducibility.** Pure Python, no API keys, deterministic. Clone
  the repo, run two commands, get identical numbers.
- **Specialization that actually changes behavior.** The same prefs
  produce different top-5 lists across personas (verified in
  `tests/test_personas.py::test_personas_produce_different_results`
  and the eval harness's `discovery` vs `comfort` cases).
- **Self-correction with a budget.** The reflect / refine loop is
  capped at 2 iterations so it cannot mask catalog problems by
  spinning forever.
- **Backward compatibility.** The original Module-3 tests (`Song`,
  `UserProfile`, `Recommender`) still pass unchanged.

## 6. Limitations and bias

- **Data scarcity.** Single-track genres (blues, country, gothic,
  classical, latin, jazz fusion, dubstep, metal, reggae, punk) cannot
  produce a diverse top-5; the rest of the list comes from energy /
  mood fallback. The agent flags this in `confidence.notes` but cannot
  fix it without more songs.
- **Algorithmic filter bubble.** The `comfort` persona deliberately
  narrows recommendations to a single genre. Even the default persona
  weights genre at +2.0, the largest single weight. A product
  defaulting to `comfort` would entrench taste and harm discovery.
- **Mood imbalance.** "happy" and "chill" dominate the catalog;
  "sad", "rebellious", "experimental", "dark" are 1-song moods. A user
  asking for those will see fallback recommendations more often.
- **English-only routing.** The persona router is keyword-based and
  cannot route non-English context strings. It silently falls back to
  `default`, which can hide a misclassification.
- **Confidence is internal consistency, not user satisfaction.** A
  "high" confidence does not mean the user will like the songs. There
  is no user-feedback loop yet.
- **TF-IDF over a tiny KB.** The retriever is excellent for a corpus
  of 11 passages but would not scale to thousands. A real deployment
  would swap in dense embeddings and the retriever interface is the
  one place that would change.
- **Misuse risk: thumb on the scale.** Persona weights are a plain
  dict, so a bad-faith operator could quietly bias the system toward
  sponsored content. Mitigation: the `AgentTrace` exposes every
  weight choice, and the evaluation harness writes a JSON report that
  can be audited or diffed by CI.

## 7. Evaluation

- **Pytest:** 37 tests across all modules, all passing.
- **Evaluation harness** (`scripts/run_evaluation.py`): 6 fixed cases
  (covering all five personas, an auto-routing case, and an edge case),
  20 assertions total, **20 / 20 passing**.
- **Aggregate metrics from the harness:**
  - average confidence: **0.805** (label: high)
  - median confidence: **0.798**
  - min confidence: **0.701** (medium — the lofi study case)
  - average iterations: **1.00** (refine is rarely needed on this catalog)
- **Manual verification:** every persona produced a sensible top result.
  The `discovery` persona surfaced ≥3 distinct genres for a pop user;
  `comfort` kept rock at #1 with score 6.19 and rock-adjacent metal
  / pop / punk / dubstep filling the rest.
- **What I learned from evaluation:**
  - Refine almost never fires on this catalog. The single-blues edge
    case I expected to trigger it actually scores the highest because
    every feature aligns. To deterministically test refinement, I
    construct an agent with `confidence_threshold=0.99` in
    `tests/test_agent.py`.
  - Confidence drops most cleanly when genre diversity drops, which
    is the right behavior for this catalog where filter-bubble risk
    is the most plausible failure mode.

## 8. Future work

- Larger and more diverse catalog, especially non-Western and
  non-English-language genres.
- Dense embeddings (or a hybrid sparse + dense retriever) once the KB
  grows past ~50 passages.
- A small classifier or LLM-based router for the persona step so
  non-English context strings still route correctly.
- A user-feedback loop ("thumbs up / down") that updates persona
  weights for the same user across sessions.
- Calibrated confidence: today the score is internal-consistency-only.
  With user feedback it could become a real probability.
- A web UI (Streamlit is already in `requirements.txt`) showing the
  trace as a left panel and the recommendations as a right panel —
  the audit story is much more compelling visually.

## 9. Personal reflection

### What surprised me about my system's behavior

I expected the agent to refine often, especially on the niche-genre
edge case. It almost never does, because confidence is dominated by
top-score and the single blues track is a near-perfect match. That
taught me to look at the *shape* of the result set, not just the
top score, which is why I added genre and artist diversity into the
confidence formula. Once I added them, the qualitative intuition
("this list is too narrow") finally lined up with a measurable signal.

I was also surprised by how well a few-shot keyword router performed
on persona routing. The harness's three "auto-routed" cases all picked
the right persona without any ML. That's a useful reminder that simple
deterministic baselines deserve a real shot before reaching for
embeddings or fine-tuning.

### How building this changed how I think about real music recommenders

Everything Spotify does at scale, this project does at toy scale: pick
a slice of the catalog, score it against the user, and tell a story
about *why*. The hard parts at scale are the same hard parts here:
data imbalance, filter bubbles, calibrated confidence, transparency.
The agentic loop is just a way to make those problems addressable in
small, observable steps.

### Where human judgment still matters

The persona weights, the knowledge-base passages, the confidence
formula, and the test-case assertions are all human-authored. The
agent is good at executing on those choices and even adjusting them
within bounds, but every value-laden decision (what counts as a "good"
recommendation, who the catalog represents, how much filter-bubble is
acceptable) was made by a person.

### AI collaboration during this project

I built this as a pair-programming session with Claude. Two specific
moments stood out.

**Helpful suggestion.** When I started writing the agent, Claude
proposed making `AgentTrace` the public contract — the same data
structure consumed by the demo, the unit tests, and the eval harness.
I would have ended up with three separate pieces of observability code
without that suggestion. Building everything against one trace cut
the surface area roughly in half and made the eval harness's
assertions read directly off the same shape the demo prints.

**Flawed suggestion.** My first version of
`test_low_data_blues_triggers_refine` asserted that the blues case
would fire the refine step. Claude wrote that test alongside me on
the assumption "only 1 song in catalog -> low confidence -> refine".
The test failed because the single blues track is a perfect match
and confidence stayed at 0.83. The right fix was to derive the test
from the *confidence formula* (artificially raise the threshold), not
from data-shape intuition. The lesson is to write tests that follow
from the math the system actually does, not from how I imagine the
system "should" feel.
