# CHANGE PROPOSAL TEMPLATE

Use this template for every proposed change before any code is modified.

---

## Goal
**One sentence describing what we're trying to accomplish.**

Example: "Add unit tests for audio microphone detection in WhisperCLI"

---

## Rationale
**Why is this change necessary and safe?**

Explain:
- What problem does it solve?
- Why is this approach sound?
- What could go wrong?

---

## Minimal Change
**Exactly what files change and how.**

Format:
```
File: src/whisper_app/example.py
Lines: 42-56
Changes:
  - Add one new function
  - No existing code removed or modified
```

Keep this to 3-4 sentences max.

---

## Why Safe
**Can you explain exactly why this works?**

Reason through it step by step. Be able to defend every line.

---

## Test Plan
**How will we verify this works?**

Example:
```bash
python -m unittest tests.test_cli.TestMicrophoneDetection -v
```

---

## Size Check
**Is this truly minimal? Could it be split smaller?**

If you answer "yes" to "could it be smaller?", split it.

---

## Notes

- Write proposal BEFORE touching code
- One logical change = one proposal
- Get explicit approval before proceeding
- Code must match proposal exactly
- Include proposal file in commit history

---

**Status:** [PROPOSED | APPROVED | REJECTED]

**Reviewer:** [Name/Date]

**Commit SHA:** [Optional - filled in after merge]
