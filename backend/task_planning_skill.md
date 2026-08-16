# Detailed sequential task planning

Plan the user's outcome, not a list of apps or generic activities.

## Default

- Create one task for one cohesive outcome, even when it uses several apps or tools.
- Split only when each result deserves its own task-board entry and a later task can consume a clearly named output from an earlier task.
- Never split research from the creation or action that directly consumes that research.
- Never create overlapping tasks or ask later tasks to rediscover earlier work.

## Sequence

1. Identify the final deliverables and every prerequisite fact or artifact.
2. Order work by information flow: gather prerequisites, decide, create, verify, then distribute or schedule.
3. For every split, name the predecessor key in `depends_on`, the exact `required_inputs`, and the exact `expected_outputs` handed forward.
4. Make each instruction operational and concrete: name the app or service, the object to find or create, the comparison or edit to perform, and the evidence required for completion.
5. Update queued tasks when new information changes their plan. Steer only work that is already running or blocked.

Good: "In Chrome, search Google Maps for small-group restaurants near the user's stated location for August 13. Compare price level, atmosphere, availability evidence, and distance; select one option and return its name, address, price level, booking link, and selection rationale."

Bad: "Research restaurants online."

## Do not split

- Searching for a restaurant and using the chosen restaurant in an invitation.
- Finding an email and extracting information from that email.
- Creating a document and formatting that same document.
- Work merely because it crosses Chrome, a native app, or a Workspace API.

## Split only with a handoff

If a request genuinely needs separate entries, every dependent task must declare what it consumes. A distribution task, for example, depends on the completed invitation and consumes its verified file path plus the approved recipient list. Never rely on open windows or conversational memory as the handoff.
