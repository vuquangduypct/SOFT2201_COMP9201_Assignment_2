# Legacy Before-Refactoring Snapshot

This directory is the runnable “before” version for Assignment 2. It contains the legacy design immediately before the Composite, Factory Method, and Command maintenance work.

Treat this directory as read-only evidence. All assessed production changes belong under the repository's main `src/` directory.

From the repository root:

```bash
PYTHONPATH=before_refactoring/src pytest before_refactoring/tests
PYTHONPATH=before_refactoring/src python -m quiz_platform.question_bank.cli import data/questions.json
PYTHONPATH=before_refactoring/src python -m quiz_platform.question_bank.cli candidates \
    data/questions.json --request data/request.json
PYTHONPATH=before_refactoring/src python -m quiz_platform.question_bank.cli moderate \
    data/questions.json approve Q-1
```

The legacy snapshot deliberately does not support JSON Lines, reuse cooldown, or pattern-based Command history. Those are maintenance requirements for the target scaffold.
