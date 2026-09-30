"""Build the knowledge base's source file from MedlinePlus Connect (US National Library of Medicine).

    python -m tools.knowledge fetch     # query Connect per LOINC code; raw responses go to data/external/medlineplus
    python -m tools.knowledge build     # write data/knowledge/chunks.jsonl and manifest.csv from the raw responses
"""
