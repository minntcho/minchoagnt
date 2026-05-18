# Review Workbench MVP Design

## Goal

Build the first visual workbench for minchoagnt by focusing on one review/apply
cycle:

```text
UserMessage -> ReviewEngine -> ReviewPlan -> StateDiff
```

The workbench should help a developer see how one input message becomes memory
or skill candidates, how those candidates are applied, and what changed in the
agent state.

This is the first slice of a larger "Agent Graph Workbook" idea. The larger
workbook may eventually expose session graphs, tool traces, prompt snapshots,
and model/tool loops. This MVP only visualizes the deterministic review-to-state
mutation path that already exists in the repository.

## Non-goals

This MVP does not include:

- full chat response generation
- tool call replay
- full session graph visualization
- subagent or delegation graphs
- cron or background automation graphs
- prompt snapshot inspection
- manual ReviewPlan editing
- Ollama reviewer execution from the browser
- a full EXPECT/check expression builder

## Product Shape

The product surface is a developer-facing Review Workbench, not a general chat
app. It can look conversational because the input is a user message, but its main
job is to reveal the review/apply pipeline.

The UI should use symbolic graph language as labels and visual cues, while still
being operated through buttons and structured controls:

```text
~ Review
! Apply
? Verify
-> Flow
@ Target
```

Symbols should not appear alone. Each symbol should be paired with a readable
label so the interface stays understandable.

## Core UI

Use a four-region layout:

```text
Left:   Command Builder
Center: Review Graph
Right:  Node Detail Panel
Bottom: Execution Log
```

### Command Builder

The builder contains:

- user message input
- reviewer selector
- review action
- apply action
- apply target display
- automatic verification summary

For the first implementation, the reviewer selector should support deterministic
reviewers only:

- `regex`
- `fake`

Ollama should remain a future option because local model availability can make
the first frontend PR harder to test reliably.

The apply target should be sandbox-only in the MVP. Applying a ReviewPlan has
side effects, so the first workbench should write to a temporary/sandbox state
area rather than the user's normal `.minchoagnt` home.

### Review Graph

The graph should show the current run as a small typed flow:

```text
[UserMessage] -> [ReviewEngine] -> [ReviewPlan] -> [StateDiff]
```

Each node should expose a status:

- `pending`
- `running`
- `success`
- `error`
- `no-op`

Selecting a node updates the detail panel.

### Node Detail Panel

The detail panel is contextual:

- `UserMessage`: role, content, and run metadata
- `ReviewEngine`: reviewer type, configuration, raw output if available
- `ReviewPlan`: validated plan JSON and validation errors
- `StateDiff`: memory diff, skill diff, apply result, and no-op reasons

The right panel should not be a permanent JSON-only panel. JSON is useful for
`ReviewPlan`, but diffs and status summaries are more important for state nodes.

### Execution Log

The log should append ordered trace events for each run:

- input received
- reviewer selected
- review started
- review completed
- apply started
- memory addition saved, skipped, or rejected
- skill creation saved, skipped, or rejected
- run completed

## State Model

Each workbench run should produce one renderable object:

```json
{
  "run_id": "run_001",
  "input": {
    "role": "user",
    "content": "remember: I prefer Korean summaries."
  },
  "reviewer": {
    "type": "regex"
  },
  "review_plan": {
    "memory_additions": [
      {
        "target": "user",
        "content": "I prefer Korean summaries."
      }
    ],
    "skill_creations": []
  },
  "apply_result": {
    "memory_saved": 1,
    "skills_created": 0
  },
  "diff": {
    "memory": {
      "added": [],
      "removed": [],
      "unchanged": []
    },
    "user": {
      "added": ["I prefer Korean summaries."],
      "removed": [],
      "unchanged": []
    },
    "skills": {
      "created": []
    }
  },
  "events": []
}
```

The UI should render from this run object rather than scattering state across
independent widgets. That keeps the graph, detail panel, diff, and log in sync.

## Apply Semantics

Applying a plan should distinguish:

- `added`: a memory or skill was saved
- `no-op duplicate`: the store already had equivalent content
- `failed validation`: the candidate failed schema or store validation
- `empty plan`: the reviewer produced no memory or skill candidates

Duplicate results should not be shown as failures. `MemoryStore.add()` already
returns `false` for duplicates, and the workbench should render that as a
successful no-op.

## Verification

The MVP should include automatic verification, not a user-authored EXPECT
builder.

Automatic verification should answer:

- Did review produce a valid ReviewPlan?
- Was the plan empty?
- Did apply save anything?
- Did apply skip anything as a duplicate?
- Did any candidate fail validation?

A future PR can add a check builder for explicit conditions such as "user memory
contains Korean summaries."

## Acceptance Criteria

1. A user can enter one UserMessage.
2. A user can choose a deterministic reviewer, starting with `regex` and `fake`.
3. Clicking `~ Review` produces a validated ReviewPlan.
4. Clicking `! Apply` applies the ReviewPlan to sandbox memory and skills.
5. The UI shows the graph `UserMessage -> ReviewEngine -> ReviewPlan -> StateDiff`.
6. Selecting a graph node changes the detail panel.
7. The ReviewPlan is visible as JSON.
8. Memory and skill changes are visible as diffs.
9. The execution log shows ordered events for the run.
10. Empty plans, duplicates, validation failures, and successful additions are
    visually distinct.
11. The MVP does not write to a user's normal `.minchoagnt` home.

## Future Work

After the MVP is working, likely follow-up PRs are:

1. Add Ollama as an optional reviewer in the workbench.
2. Add an explicit EXPECT/check builder.
3. Add manual ReviewPlan candidate editing.
4. Expand from Review Workbench into broader Agent Graph Workbook views.
