# Contribution and integration workflow

## Team responsibilities
- Oussema Braham: technical lead, code reviewer and integration owner. Reviews Lina's pull requests, requests corrections, and performs merges after validation.
- Lina: answer generation, citations, interface, evaluation questions, user guide and presentation. Opens pull requests and addresses review feedback.
- Oussema also implements ingestion, indexing and retrieval. Lina reviews Oussema's changes as a peer check; Oussema performs the final integration.

## Workflow
1. Pick a ClickUp task and create a short-lived branch such as `feature/s2-pdf-ingestion` or `fix/citation-pages`.
2. Make focused commits and include the ClickUp task link in the pull request.
3. Describe the change, acceptance criteria checked, validation evidence and known limitations.
4. Request Oussema's review for Lina's work. Do not merge until Oussema approves. For Oussema's own changes, request Lina's peer review.
5. Oussema checks compatibility with the integrated application and merges into `main` after review and passing checks. Avoid direct feature commits to `main`.
6. Link the merged PR to ClickUp and mark the task complete only after integration verification.

This is the agreed team process; it does not imply branch protection has been enabled.

## Definition of done
Code or document delivered; task acceptance criteria verified; review feedback resolved; integration verified; documentation and known limitations updated.

## Data and secrets
Use only approved/public reference documents and fictional patient examples. Never commit real patient data, secrets, tokens or environment files. Show `Prototype — not for medical use` in the application.

## Schedule
Six one-week sprints: 2 November–13 December 2026. This is the project completion deadline; the official presentation time remains to be confirmed.
