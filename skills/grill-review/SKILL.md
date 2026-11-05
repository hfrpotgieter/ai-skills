---
name: grill-review
description: Turn a finished grilling session into an HTML review doc (decisions, Mermaid diagrams, the real proposed diff) to sense-check before any code changes.
argument-hint: "Optional: a title or scope for the review"
disable-model-invocation: true
---

Turn the shared understanding from the grilling session in this conversation into one HTML review document. The user reads it to sense-check the change before their working tree is touched. The diff in the document is the exact patch that gets applied on approval: what they check is what lands.

This is synthesis. The decisions are settled; carry them over as they were agreed. When the code needs a decision the session never settled, list it under open questions in the document and keep the draft to what was settled.

## Steps

0. **Gate.** This skill runs on the output of a grilling session: one in this conversation that ended with the user confirming shared understanding. When there is no such session, stop here. Invoke the `grilling` skill on the user's topic (the argument, else ask for one), and resume from step 1 once it ends in confirmed shared understanding. When `grilling` is not installed, tell the user to install it first (`npx skills add mattpocock/skills`, choosing `grilling` and `grill-me`), and end.

1. **Ledger.** List every settled decision: the session's number (Q1, Q2, …), a title, the agreed answer, and the one-line reason. Add the items agreed to be out of scope.

2. **Draft in a scratch checkout**, so the user's working tree stays exactly as it is.
   - Create an isolated checkout of the current commit under `$TMPDIR/grill-review/<slug>/wt`. Use the repo's own worktree mechanism when its agent docs name one (e.g. Sapling worktrees), else `git worktree add`.
   - Carry over the user's uncommitted changes as the **baseline**: take `git diff HEAD` (or `sl diff`) in their checkout, apply it in the scratch checkout, and commit it there as `baseline`. The review diff then holds only the proposed change.
   - Implement every ledger decision, and only those.
   - Run the project's build or typecheck, plus the tests nearest the change. Record each command and its result.
   - Write the proposed change, diffed against `baseline`, to `$TMPDIR/grill-review/<slug>/change.patch`.

3. **Trace.** Map each hunk to the decisions it implements. Done when every decision has at least one hunk or is marked _no code_, and every hunk names a decision. Close a gap by fixing the draft; a hunk no decision asks for is scope creep, so remove it.

4. **Diagrams.** Draw each structural change (calls, queries, data flow, control flow) as a before/after Mermaid pair. A change with no structural effect gets no diagram. Quote node labels (`A["fetchSellers(adminID)"]`) so parentheses and symbols parse.

5. **Write the document.** Write `$TMPDIR/grill-review/<slug>/review.json` in the format in [`fill.py`](fill.py)'s docstring, then run `python3 <this skill's dir>/fill.py review.json change.patch`. It writes `review.html` beside them. The spec holds:
   - **summary**: two to four sentences on what changes and why;
   - **decisions**: the ledger;
   - **diagrams**: the before/after pairs, each with a one-line caption;
   - **files**: one per patched file, with a note per hunk naming its decisions;
   - **verification**: the commands run, with pass or fail;
   - **out of scope** and **open questions**;
   - **apply**: the commands that apply `change.patch` to the user's checkout.

   `fill.py` re-checks the step 3 trace and exits 1 with the gaps listed. Fix the draft or the spec and run it again until it writes the file.

6. **Open** the document (`open` on macOS, `xdg-open` on Linux) and give the user its path. Keep the scratch checkout until they decide. On approval, apply `change.patch` to their checkout (`git apply`, or `sl import --no-commit`), run the verification commands there, then remove the scratch checkout.
