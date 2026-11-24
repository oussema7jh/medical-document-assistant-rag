# Demo rehearsal

**Prototype — not for medical use.** Use the approved corpus or a clearly labeled synthetic corpus. Keep patient records and live clinical systems out of the demo.

## Before the session

1. Confirm the presentation time and agree who will drive the app. Allow time for questions.
2. Confirm the exact corpus and version, encoder revision, local generation model, top-k and distance limit used in the demo. Record them once on the demo machine.
3. Verify the index loads, the local model responds, and the app shows the same corpus version on each screen. Open the reference documents at the pages used in the demo.
4. Rehearse an evidence-backed answer, a question outside the corpus, and a rejected import. Select questions from the development split. Keep the final test questions for evaluation.
5. Record the walkthrough after testing these cases, with the version and prototype notice visible. Include the question, result, expanded source and rejected import message. Verify that the saved recording plays offline before the session.

Open the [presentation slides](demo/medical-document-assistant.pptx) in presenter view for speaker notes. The evaluation slide currently lists the targets. Add measured counts and denominators after the frozen run and cross-review.

The [backup recording](demo/backup-walkthrough.mp4) uses a synthetic visitor-desk document and deterministic local test components. It shows an answer with the cited source, an out-of-scope travel question, and a changed TXT file rejected by the import check. Play it offline if the live demo is unavailable.

## Suggested five-minute walkthrough

| Time | Speaker | Walkthrough | What to verify on screen |
| --- | --- | --- | --- |
| 0:00–0:40 | Lyna | Explain the staff document-lookup problem and the project scope. | The prototype notice and selected corpus are visible. |
| 0:40–1:30 | Oussema | Trace one source through extraction, chunking, embeddings and retrieval. | The document edition and original page or text line range are traceable. |
| 1:30–3:00 | Lyna | Ask a supported question, open its citation, ask a question outside the corpus, then try an altered copy of an approved TXT file. | The first answer matches the excerpt. The second question returns “I could not find this in the documents.” The import fails and the existing index remains available. |
| 3:00–4:00 | Oussema | Explain how the threshold was tuned and how the frozen test set was evaluated. | Show raw counts, denominators and limitations if evaluation has been completed. Identify checks still pending if applicable. |
| 4:00–5:00 | Lyna | Describe limitations and hand off to questions. | Distinguish document lookup from clinical decision-making. |

## Rehearsal record

For each rehearsal, record the date, corpus and model versions, elapsed time, outcome of the three demo cases, and any fixes. Repeat after fixing issues that change the flow. Both students should verify that the same supported answer can be checked against the cited document and that an outage is displayed as an error.

## Questions to prepare for

- What happens when two documents discuss the same topic but apply to different populations? Check the selected edition, the source passage, and whether the question's qualifiers appear in the evidence. Flag conflicting evidence for human review.
- Why use retrieval? It selects passages from the designated corpus and supplies traceable evidence to the local model for each question.
- How is success measured? Report exact document and location accuracy, human-reviewed grounding and correct abstention. Include refusals on answerable questions and report runtime errors separately.
- What should a staff member do when the assistant cannot answer? Check the approved source directly or use the established document lookup process.
