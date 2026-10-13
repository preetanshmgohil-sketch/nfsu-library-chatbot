"""Unit tests for the deterministic query parser — run: python -m pytest tests/ -q
Or without pytest: python tests/test_query_parser.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.query_parser import parse_query  # noqa: E402


def test_subject_search():
    intent = parse_query("Find books on forensic DNA analysis.")
    assert intent.is_search
    assert "forensic" in intent.keywords.lower() or "dna" in intent.keywords.lower()


def test_author_search():
    intent = parse_query("Search for books written by Calder Wong.")
    assert intent.is_search
    assert intent.author is not None
    assert "Wong" in intent.author


def test_isbn_search():
    intent = parse_query("Do we have ISBN 9780123456789?")
    assert intent.is_search
    assert intent.isbn == "9780123456789"


def test_year_after_filter():
    intent = parse_query("Find books on forensic psychology published after 2020.")
    assert intent.is_search
    assert intent.year_after == 2020


def test_year_range_filter():
    intent = parse_query("Show cybercrime books published between 2018 and 2022.")
    assert intent.is_search
    assert intent.year_after is not None
    assert intent.year_before is not None


def test_combined_author_year():
    intent = parse_query("Books by Calder Wong after 2018 on digital evidence")
    assert intent.is_search
    assert intent.author is not None
    assert intent.year_after == 2018


def test_thesis_type():
    intent = parse_query("Find theses on digital forensics")
    assert intent.is_search
    assert intent.resource_type == "thesis"


def test_bare_topic_phrase():
    intent = parse_query("forensic toxicology")
    assert intent.is_search


def test_faq_is_not_search():
    intent = parse_query("What are the library timings?")
    assert not intent.is_search


def test_renew_is_not_search():
    intent = parse_query("How do I renew my book?")
    assert not intent.is_search


def test_koha_params_primary_index_isbn():
    intent = parse_query("ISBN 9780123456789")
    params = intent.to_koha_params()
    assert params["idx"] == "nb"
    assert params["q"] == "9780123456789"


def test_koha_params_author_index_is_au():
    # Verified live on catalog.nfsu.ac.in — author index is 'au', not 'ac'
    intent = parse_query("Show books by Calder Wong")
    params = intent.to_koha_params()
    assert params["idx"] == "au"
    assert "Wong" in params["q"]


def test_koha_params_subject_default():
    intent = parse_query("Show books on cybercrime investigation.")
    params = intent.to_koha_params()
    assert params["idx"] in ("su", "", "ti")
    assert params.get("weight_search") == "1"


def test_empty_message():
    intent = parse_query("")
    assert not intent.is_search


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except AssertionError as e:
                failures += 1
                print(f"FAIL  {name}: {e}")
            except Exception as e:  # noqa: BLE001
                failures += 1
                print(f"ERROR {name}: {type(e).__name__}: {e}")
    print(f"\n{'OK' if failures == 0 else str(failures) + ' failed'}")
    sys.exit(1 if failures else 0)
