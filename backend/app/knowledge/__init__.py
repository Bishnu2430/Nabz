"""Knowledge base for grounded explanations (FR-21): passages from licence-checked sources, embedded for retrieval.

- `embed`: the sentence-embedding model (multilingual-e5-small on ONNX Runtime) and a test double.
- `store`: load the committed chunk file into kb_document / kb_chunk.
- `retrieve`: the passages for each test being explained, most relevant first.
"""
