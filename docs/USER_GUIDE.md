# Medical Document Assistant user guide

**Prototype — not for medical use.** Use approved reference documents. Keep patient records, credentials and other private information out of files and questions.

## Open the assistant

Follow the local [setup guide](SETUP.md). The operator supplies the approved manifest, an index and development-set calibration for the same corpus version, and the approved local Ollama model. Run `uv run --locked streamlit run app.py` and open the local URL shown in the terminal. In the **Approved corpus** sidebar, select the version you intend to search.

## Import approved documents

1. Open **Import approved documents**.
2. Choose the approved PDF or UTF-8 TXT files whose names and contents match the configured manifest. The assistant checks each file against its registered checksum.
3. Enter a new corpus version and select **Build index**. Review the result and any extraction warnings. The current approved index stays available if the build fails.
4. Calibrate the newly built version against the development set using the setup guide before enabling questions against it.

## Ask a question and check the sources

1. Enter one focused reference question and select **Search documents**. Include any qualifiers, such as a document edition or applicable setting.
2. Read the answer, then open the entries under **Sources**. Each shows the document title, edition, page or text line range, and excerpt. Use **Open source document** when the approved manifest includes a public link.
3. Check the excerpt and the original edition for conditions that matter to the question.

## No answer and errors

**I could not find this in the documents.** The assistant could not verify an answer from the selected corpus. Check the version, rephrase the question with a specific topic, or consult the original approved documents directly.

| Message or symptom | What to do |
| --- | --- |
| A file is rejected | Check its filename, extension, size and checksum against the approved manifest. Ask the corpus operator about a different edition. |
| The index reports pages with no usable text | Review the original pages. The PDF reader may need a text-based edition for scanned material. |
| Search is unavailable | Choose a version with a valid index and matching calibration, then check the approved manifest and configured model. |
| The local model is unavailable or times out | Check that the approved Ollama model is loaded and Ollama is running. Retry after the service is ready. |
| A technical error persists | Share the request ID with the operator. Keep question and document contents out of error reports. |

See the [demo rehearsal instructions](DEMO_RUNBOOK.md) for a repeatable walkthrough.
