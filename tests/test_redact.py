from pathlib import Path

from application_analyzer.facts import ExtractedFacts
from llm_score.redact import apply_identity_redactions, redact_application_text


def test_redacts_name_address_contact_and_ids() -> None:
    source = Path("Doe,_Jane_AU99999_OPHTH-R_2025-26.pdf")
    facts = ExtractedFacts(source_path=str(source), applicant_name="Jane Q Doe")
    original = """
Applicant's Name: Jane Q Doe
Current Address
123 Oak Street Apt 4
Evanston, IL 60208
Email: jane.doe@example.com
Phone: (312) 555-0199
Date of Birth: 01/15/1998
AAMC ID: 12345678
AU99999

I enthusiastically recommend Jane Doe. She lives at 123 Oak Street.
"""
    redacted, notes = apply_identity_redactions(original, facts, source, harvest_from=original)
    joined = " ".join(notes)
    assert "Jane" not in redacted
    assert "Doe" not in redacted
    assert "jane.doe@example.com" not in redacted
    assert "555-0199" not in redacted
    assert "123 Oak" not in redacted
    assert "60208" not in redacted
    assert "12345678" not in redacted or "[AAMC_ID]" in redacted or "[APPLICANT_ID]" in redacted
    assert "[APPLICANT]" in redacted
    assert "Jane" not in joined  # notes must not leak the name
    payload, _ = redact_application_text(original, facts, source, harvest_from=original)
    assert payload.startswith("[IDENTIFIERS REDACTED LOCALLY] The applicant is referred to only as [APPLICANT].")



def test_letter_writers_redacted_and_not_mistaken_for_addresses() -> None:
    source = Path("sample.pdf")
    facts = ExtractedFacts(source_path=str(source), applicant_name=None)
    original = "Letter 1 - Dr. A. Patel, Department of Medicine\nProfessor Lin Chen wrote too."
    redacted, _ = apply_identity_redactions(original, facts, source, harvest_from=original)
    assert "Patel" not in redacted and "Chen" not in redacted
    assert "[ADDRESS]" not in redacted
    assert "Letter 1 - [PERSON], Department of Medicine" in redacted



def test_inline_applicant_label_without_name_in_filename() -> None:
    source = Path("upload.pdf")
    facts = ExtractedFacts(source_path=str(source), applicant_name=None)
    original = (
        "Applicant: Jordan Rivera | AAMC ID: AU99999 | PACKET\n"
        "Jordan is nice. 2. Kim S, Rivera J, Ortiz M. Chart review."
    )
    redacted, _ = apply_identity_redactions(original, facts, source, harvest_from=original)
    assert "Jordan" not in redacted and "Rivera" not in redacted
    assert "AU99999" not in redacted


if __name__ == "__main__":
    test_redacts_name_address_contact_and_ids()
    test_letter_writers_redacted_and_not_mistaken_for_addresses()
    test_inline_applicant_label_without_name_in_filename()
    print("ok")
