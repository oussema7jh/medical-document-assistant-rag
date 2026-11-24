# Grounded answers and citations

The pipeline asks a local model to select up to two verbatim excerpts from an approved corpus.
It displays the excerpts with the document title, edition, and PDF page or TXT line range.
It returns “I could not find this in the documents.” when there is no usable evidence.
An unavailable index or Ollama model produces an operational error.

## Local setup

Use the approved, indexed corpus and the top-k and distance threshold frozen after development
calibration in [Setup](SETUP.md). Install the model and tag approved for the project on the local
Ollama service. Record the selected tag and model digest with the evaluation results.

Disable Ollama cloud features before using the assistant. Set `OLLAMA_NO_CLOUD=1` in the Ollama
server environment, or set `"disable_ollama_cloud": true` in its configuration and restart
Ollama. Check the server logs for `Ollama cloud disabled: true`. The adapter connects to loopback,
checks for the selected model in the local inventory, and rejects remote aliases reported by the
server. Use approved reference documents and questions without patient information.
[Ollama local setup](https://docs.ollama.com/faq#how-do-i-disable-ollamas-cloud-features)

Call the service from Python with the paths and values from your deployment.

```python
from pathlib import Path

from rag_assistant.embeddings import Encoder
from rag_assistant.generation import OllamaModel
from rag_assistant.pipeline import AnswerPipeline

pipeline = AnswerPipeline(
    index_dir=Path("data/index"),
    corpus_version=corpus_version,
    manifest_path=Path("data/manifest.jsonl"),
    encoder=Encoder(),
    model=OllamaModel(approved_local_model),
    max_distance=calibrated_distance,
    top_k=calibrated_top_k,
)
response = pipeline.answer(question)
```

## Validation

The pipeline validates the model's JSON, the cited IDs from the exact prompt, the source
metadata in the approved manifest, and that the selected excerpts are contiguous source text.
Explicit role overrides are filtered out of the prompt. The remaining passages are still handled
as untrusted data. Reviewers need to check that selected excerpts answer the whole question and
preserve the source context. Extractive answers use the language of the cited documents.

Run `uv run --locked pytest -q tests/test_answer_schema.py tests/test_answer_pipeline.py`
to check the response contract, refusal cases, citation validation, and local-model behavior
with a mock model. Evaluation with the approved model and final corpus is a separate step.
