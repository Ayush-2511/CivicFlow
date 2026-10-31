"""Unit tests for clause splitting and BM25 indexing."""

from app.nodes.index import BM25ClauseIndex, split_into_clauses
from app.nodes.parse import PageText


def test_split_into_clauses_legal_numbered():
    doc_id = "a1b2c3d4e5f678901234567890abcdef"
    page1 = PageText(
        page=1,
        text=(
            "1. Short Title and Commencement: This scheme may be called the PM Kisan Scheme.\n"
            "2. Definitions: In this scheme, 'Farmer Family' means a family consisting of husband, wife and minor children.\n"
            "3. Eligibility Criteria: All landholding farmer families having cultivable land up to 2 hectares shall be eligible for benefit."
        ),
    )
    page2 = PageText(
        page=2,
        text=(
            "Section 4. Benefit Details: Under the Scheme, a financial benefit of Rs. 6000/- per year per family will be provided.\n"
            "Section 5. Exclusion: The following categories of beneficiaries shall not be eligible: Institutional landholders."
        ),
    )

    clauses = split_into_clauses([page1, page2], doc_id)
    assert len(clauses) >= 4

    # Verify ID structure
    assert clauses[0].id == "a1b2c3-p1-c01"
    assert clauses[1].id == "a1b2c3-p1-c02"
    assert clauses[0].page == 1
    assert "PM Kisan Scheme" in clauses[0].text

    p2_clauses = [c for c in clauses if c.page == 2]
    assert len(p2_clauses) >= 2
    assert p2_clauses[0].id == "a1b2c3-p2-c01"
    assert "Rs. 6000/-" in p2_clauses[0].text


def test_bm25_clause_index_search_and_lookup():
    doc_id = "doc999"
    page = PageText(
        page=1,
        text=(
            "1. Landholding: Farmers with less than 2 hectares of agricultural land.\n"
            "2. Financial grant: Direct benefit transfer of Rs 6000 into bank account.\n"
            "3. Required Documents: Aadhaar card and land revenue records must be submitted."
        ),
    )
    clauses = split_into_clauses([page], doc_id)
    index = BM25ClauseIndex(clauses)

    # Test lookup by ID
    c1 = index.get_by_id(clauses[0].id)
    assert c1 is not None
    assert "less than 2 hectares" in c1.text

    # Test BM25 search
    results = index.search("agricultural land holding", top_k=2)
    assert len(results) > 0
    assert results[0].id == clauses[0].id

    # Test search for financial grant
    grant_results = index.search("money grant direct transfer", top_k=1)
    assert len(grant_results) > 0
    assert "6000" in grant_results[0].text

