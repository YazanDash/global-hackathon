# BudgetDev — Token-Efficient Coding Agent

BudgetDev is a coding agent that fixes software issues using the **fewest tokens possible without sacrificing correctness**. It builds a one-time semantic index of a repository (the *Repo Atlas*), then retrieves only the small code windows a task needs, instead of letting the LLM browse the repo.

> **Pay once to understand the repository. Retrieve by meaning. Read only what matters. Spend tokens only where they improve the chance of a correct, test-passing patch.**

## The Problem

Coding agents are expensive, and most of the cost is waste, not reasoning:

- They **explore blindly**: grep, open whole files, repeat.
- They **re-read the same context** on every turn of the loop.
- They **paste raw tool output** (full file dumps, huge test logs) back into the prompt.
- They **use one expensive model for everything**, including trivial steps like summarizing a log.

The result is high cost and latency per task, and budgets that are hard to predict or cap.

## The Solution

BudgetDev attacks each source of waste:

| Waste | BudgetDev's answer |
|---|---|
| Blind exploration | **Repo Atlas**: search code by meaning and get symbol pointers, not files |
| Whole-file reads | **`read_lines`**: read only the relevant line window |
| Raw tool output in context | **Compress** every observation before it enters the context |
| One model for everything | **Model routing**: cheap model for planning/summarizing, stronger model only when needed |
| Unbounded spend | **Budget Controller** with a hard token cap and a token receipt |

## Status: What Works Today

This is a proof of concept. The core loop works end to end; the rest of the design is planned.

| Component | Status | Notes |
|---|---|---|
| Agent loop (Reason → Act → Observe) | ✅ / 🔜 | TODO: confirm |
| Repo Atlas: structural index | ✅ / 🔜 | TODO: AST parser or simpler approach? |
| Repo Atlas: semantic summaries | ✅ / 🔜 | TODO |
| Call graph (callers, callees, tests) | 🔜 | TODO |
| Incremental index update after edits | 🔜 | TODO |
| Tools: `semantic_search`, `read_lines`, `write_patch`, `run_tests`, `finish` | ✅ / 🔜 | TODO: list which exist |
| Tools: `find_symbol`, `get_call_graph` | 🔜 | TODO |
| Output compression | ✅ / 🔜 | TODO |
| Model routing via Bifrost | ✅ / 🔜 | TODO |
| Token budget + receipt | ✅ / 🔜 | TODO |

## Quickstart

```bash
git clone https://github.com/YazanDash/global-hackathon
cd global-hackathon
pip install -e .
cp .env.example .env        # add your API keys
# TODO: exact commands
# python -m budgetdev index <path-to-repo>
# python -m budgetdev fix <path-to-repo> "Login crashes when email is empty"
```

## How It Works

### 1. Index once (Repo Atlas)

The repository is parsed into functions, classes, imports, calls and tests. A cheap model writes a short title, summary and keywords for each symbol. Only changed symbols (and their direct callers/callees) are re-summarized after edits.

```mermaid
flowchart TD
    A[Repository] --> B[Parser / AST]
    B --> C[Extract Functions, Classes, Imports, Calls, Tests]
    C --> D[Structural Index]

    D --> E[Cheap LLM Summarization Pass]
    E --> F[Semantic Index:<br/>title + short summary + keywords]

    D --> G[Call Graph Index]

    F --> H[(Repo Atlas Store)]
    G --> H
    D --> H

    I[Agent Edits Code] --> J[Detect Changed Symbols]
    J --> K[Re-summarize Only Changed Code<br/>and direct callers/callees]
    K --> H
```

Example index entry:

```json
{
  "id": "auth/login.py::validate_login",
  "title": "Validate user login credentials",
  "summary": "Checks email and password, rejects empty email, returns a session or AuthError.",
  "keywords": ["login", "authentication", "email validation"],
  "file": "auth/login.py",
  "lines": "42-88",
  "calls": ["db.get_user", "security.hash_password"],
  "called_by": ["api/routes/auth.py::login_handler"],
  "tests": ["tests/test_login.py::test_empty_email_rejected"]
}
```

### 2. Solve with a budgeted agent loop

The agent is a **Reason → Act → Observe** loop. The LLM decides *what* to do; Python code does the work (searching the index, reading code, applying patches, running tests). Every tool output is compressed before it is appended to the context.

```mermaid
flowchart LR
    A[Task + Tool Definitions] --> B[LLM Decision]
    B --> C{Tool call or final answer?}

    C -- Tool call --> D[Execute Python Tool]
    D --> E[Compress Tool Output]
    E --> F[Append Result to Context]
    F --> B

    C -- Final answer --> G[Return Patch]
```

### 3. Control the spend

Around the loop, a Budget Controller decides which model handles each step and when to stop. This is the target pipeline:

```mermaid
flowchart TD
    A[User Issue] --> B[Budget Controller]
    B --> C[Cheap Planner Model:<br/>what evidence do we need?]
    C --> D[Repo Atlas Lookup]
    D --> E[Symbol Pointers, not files]
    E --> F[read_lines: relevant window only]
    F --> G[Cheap Model: compress evidence]
    G --> H{Enough evidence?}
    H -- No --> D
    H -- Yes --> I[Coder Model: minimal patch]
    I --> J[Apply Patch + Run Targeted Tests]
    J --> K{Tests pass?}
    K -- Yes --> L[Finish: patch + token receipt]
    K -- No --> M{Budget left?}
    M -- Yes --> N[Compress failure, retry<br/>escalate to stronger model once]
    N --> I
    M -- No --> O[Stop: report failure + token usage]
```

Before each action the controller asks: *Can the Atlas answer this without an LLM? Can a cheap model handle it? Do we need to read more? Should we run only targeted tests? Should we escalate? Is the budget exhausted?*

## Tools

| Tool | Purpose | Token-saving role |
|---|---|---|
| `semantic_search` | Find functions/classes by meaning | Replaces broad grep and file exploration |
| `find_symbol` | Locate an exact function or class | Returns a precise pointer |
| `get_call_graph` | Show callers, callees and related tests | Avoids reading unrelated modules |
| `read_lines` | Read a specific line window | Prevents whole-file reads |
| `write_patch` | Apply a unified diff | Avoids rewriting entire files |
| `run_tests` | Run selected tests | Avoids huge full-test logs |
| `finish` | Submit the final patch | Ends the loop |

## Model Routing

[Bifrost](https://github.com/maximhq/bifrost) is the single gateway for all model calls. It provides provider routing, virtual keys, budgets, rate limits, caching and a token ledger.

```mermaid
flowchart TD
    A[Agent Action] --> B{Action type?}
    B -- Classify / Plan / Summarize --> C[Cheap Model]
    B -- Small localized patch --> D[Mid or Strong Coder Model]
    B -- Repeated failure / complex task --> E[Strong Escalation Model]
    C --> F[Bifrost Gateway]
    D --> F
    E --> F
    F --> G[Token Ledger + Observability]
```

## Example Run

**Issue:** "Login crashes when email is empty."

```mermaid
sequenceDiagram
    participant U as User
    participant A as BudgetDev Agent
    participant R as Repo Atlas
    participant F as File Reader
    participant L as LLM via Bifrost
    participant T as Test Runner

    U->>A: Fix empty-email login crash
    A->>L: Plan task (cheap model)
    L-->>A: Search for login validation
    A->>R: semantic_search("empty email login validation")
    R-->>A: auth/login.py::validate_login, lines 42-88
    A->>F: read_lines("auth/login.py", 42, 88)
    F-->>A: Relevant code only
    A->>L: Generate minimal patch
    L-->>A: Unified diff
    A->>T: run_tests("test_login")
    T-->>A: 1 test failed: empty email not rejected
    A->>L: Compress failure and revise patch
    L-->>A: Updated diff
    A->>T: run_tests("test_login")
    T-->>A: All tests pass
    A-->>U: Final patch + token receipt
```

## Evaluation

We compare three configurations on the same tasks:

| Configuration | Purpose |
|---|---|
| Baseline agent | Normal token consumption |
| Baseline + Repo Atlas | Retrieval savings |
| Baseline + Repo Atlas + Budget Controller | Full-system savings |

Metric:

$$
\text{Tokens per resolved task} = \frac{\text{Total tokens used}}{\text{Tasks successfully resolved}}
$$

We also track input/output tokens, LLM calls, files read, tests run, pass rate, cost and wall time.

### Results

| Configuration | Tasks | Resolved | Total tokens | Tokens / resolved task | LLM calls |
|---|---|---|---|---|---|
| Baseline | TODO | TODO | TODO | TODO | TODO |
| + Repo Atlas | TODO | TODO | TODO | TODO | TODO |
| + Atlas + Budget Controller | TODO | TODO | TODO | TODO | TODO |

*Even a small run (3–5 tasks on one repo) is enough for a POC. Report the one-time indexing cost separately.*

## Limitations and Next Steps

- **Indexing has an upfront cost.** It pays off only across multiple tasks on the same repo.
- **Summaries can be wrong or stale.** A bad summary can hide the right function. Incremental re-indexing and a fallback to plain text search are needed.
- **Static call graphs miss dynamic behavior** (dynamic dispatch, reflection, runtime registration).
- **Tests are required.** Without tests, the agent has no signal for "correct".
- Next: full call graph, incremental updates, multi-language support, larger