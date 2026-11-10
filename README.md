# BudgetDev — Token-Efficient Coding Agent

BudgetDev is a coding agent designed to complete software tasks using the **fewest tokens possible without sacrificing correctness**.

Instead of letting the LLM browse an entire repository, it first builds a one-time **semantic code index** (the *Repo Atlas*), then retrieves only the smallest relevant code windows needed to solve the task.

## Core Idea

> **Pay once to understand the repository. Retrieve by meaning. Read only what matters. Spend tokens only where they improve the chance of a correct, test-passing patch.**

## High-Level Process

```mermaid
flowchart TD
    A[User Issue / Feature Request] --> B[Budget Controller]

    B --> C[Cheap Planner Model]
    C --> D[Create Minimal Evidence Checklist]

    D --> E[Repo Atlas Lookup]

    subgraph RepoAtlas[Repo Atlas / Semantic Code Index]
        F[Structural Index<br/>files, symbols, signatures]
        G[Semantic Index<br/>LLM-generated titles and summaries]
        H[Call Graph<br/>callers, callees, tests]
    end

    E --> F
    E --> G
    E --> H

    E --> I[Return Symbol Pointers<br/>not full files]

    I --> J[Targeted Code Read<br/>read only relevant lines]
    J --> K[Cheap Summarizer Model<br/>compress evidence and logs]

    K --> L{Enough evidence?}
    L -- No --> E
    L -- Yes --> M[Coder Model<br/>write minimal patch]

    M --> N[Apply Patch]
    N --> O[Run Targeted Tests]

    O --> P{Tests pass?}
    P -- Yes --> Q[Finish:<br/>return final patch + token receipt]
    P -- No --> R{Budget remaining?}

    R -- Yes --> S[Compress failure reason]
    S --> T{Retry with cheap model?}
    T -- Yes --> M
    T -- No --> U[Escalate once to stronger model]
    U --> M

    R -- No --> V[Stop:<br/>report failure and token usage]
```

## Agent Loop

The agent is a simple **Reason → Act → Observe** loop.

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

The LLM decides **what to do**. Your Python code performs the actual work: searching the index, reading code, applying patches, and running tests.

## Tools

| Tool | Purpose | Token-Saving Role |
|---|---|---|
| `semantic_search` | Find functions/classes by meaning | Avoids broad grep and file exploration |
| `find_symbol` | Locate an exact function or class | Returns a precise pointer |
| `get_call_graph` | Show callers, callees, and related tests | Avoids reading unrelated modules |
| `read_lines` | Read a specific line window | Prevents whole-file reads |
| `write_patch` | Apply a unified diff | Avoids rewriting entire files |
| `run_tests` | Run selected tests | Avoids huge full-test logs |
| `finish` | Submit the final patch | Ends the loop |

## Repo Atlas

The Repo Atlas is built once, then updated incrementally after edits.

```mermaid
flowchart TD
    A[Repository] --> B[Tree-sitter / AST Parser]
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

## Model Routing

BudgetDev uses Bifrost to route work to the cheapest model that can handle it.

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

Bifrost provides a single gateway for multiple providers, virtual keys, budgets, rate limits, routing, caching, and observability.

## Token Budget Policy

Before each action, the Budget Controller asks:

1. Can the Repo Atlas answer this without an LLM?
2. Can a cheap model handle it?
3. Do we need to read more code?
4. Should we run only targeted tests?
5. Should we escalate to a stronger model?
6. Should we stop because the budget is exhausted?

The agent optimizes:

\[
	ext{Token Efficiency} = rac{	ext{Tasks successfully resolved}}{	ext{Total tokens used}}
\]

## Example Flow

**Issue:** “Login crashes when email is empty.”

```mermaid
sequenceDiagram
    participant U as User
    participant A as BudgetDev Agent
    participant R as Repo Atlas
    participant L as LLM via Bifrost
    participant T as Test Runner

    U->>A: Fix empty-email login crash
    A->>L: Plan task using cheap model
    L-->>A: Search for login validation
    A->>R: semantic_search("empty email login validation")
    R-->>A: auth/login.py::validate_login, lines 42-88
    A->>R: read_lines("auth/login.py", 42, 88)
    R-->>A: Relevant code only
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

Compare these configurations on the same tasks:

| Configuration | Purpose |
|---|---|
| Baseline agent | Shows normal token consumption |
| Baseline + Repo Atlas | Measures retrieval savings |
| Baseline + Repo Atlas + Budget Controller | Measures full-system savings |

Track:

- Total input and output tokens
- Number of LLM calls
- Number of files read
- Number of tests run
- Patch correctness / tests passed
- Cost and wall time
- Tokens per successfully resolved task

## Demo Message

> BudgetDev plans before it reads, retrieves only the code it needs through a semantic Repo Atlas, compresses everything it observes, and routes work through Bifrost so tokens are spent only where they change the outcome.
