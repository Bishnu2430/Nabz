"""NHANES population percentiles for FR-20.

    python -m tools.nhanes fetch     # download the source files into data/external/nhanes and verify checksums
    python -m tools.nhanes build     # write data/catalogue/population_percentiles.csv

NHANES (US CDC / NCHS) is public domain. Nabz labels every comparison as a US population, because robust
Indian population percentiles are not publicly available (docs/09 §2, risk R-14).
"""
