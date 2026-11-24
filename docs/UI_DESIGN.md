# Interface design

The workspace is a reading desk for staff who need to find a passage in the
approved reference documents. It keeps the question and short answer in the
main column. Each source heading pairs the document title with its page or
line location so staff can check an answer without scanning the excerpt first.

```text
Sidebar                          Main column
┌───────────────────────┐   ┌────────────────────────────────────────┐
│ Approved corpus       │   │ Medical Document Assistant             │
│ Active version/status │   │ Prototype — not for medical use        │
│ ▸ Import documents    │   │                                        │
│   PDF/TXT chooser     │   │ Question                               │
│   New corpus version  │   │ [                                    ] │
│   Build index         │   │ [Search documents]                     │
│                       │   │                                        │
│                       │   │ Answer                                 │
│                       │   │ Short response or a clear status      │
│                       │   │                                        │
│                       │   │ Sources                                │
│                       │   │ ▸ Document title · page 12             │
│                       │   │ ▸ Document title · lines 8–10          │
└───────────────────────┘   └────────────────────────────────────────┘
```

Use a light mineral background (`#F3F7F8`), white reading surface (`#FFFFFF`),
dark ink (`#172D37`), deep teal (`#136A69`) for the main action and a slate
rule (`#C4D4D9`) between fields. Use Streamlit's system sans for compact,
left-aligned titles and body text. Keep the main column comfortably readable
and use Streamlit's collapsible sidebar on narrow screens.

| State | Interface behavior |
|---|---|
| Ready | Show the active corpus version and enable the question form. |
| Empty question | Prompt for a question and leave the result area clear. |
| Answer found | Show the short answer, document title, page or lines, version and expandable excerpt. |
| Evidence missing | Show “I could not find this in the documents” with no sources. |
| Missing corpus or settings | Explain what must be configured before searching. |
| Model or index error | Show the retry or setup step and the request ID when available. |
| Upload validation fails | Explain which file is missing from the approved set or differs from its checksum. |
| Import succeeds | Confirm what was indexed and use the new version for subsequent requests after calibration is configured. |

The prototype notice remains visible. Answers and source excerpts render as
literal text. Results stay in the current session and clear when the active
corpus changes. Uploaded files must match the operator's approved manifest.
