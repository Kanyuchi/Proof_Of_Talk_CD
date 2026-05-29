"""Tests for the same-organization filter (Erin McMahon / Axe Compute regression)."""
from types import SimpleNamespace

from app.services.same_org_filter import (
    is_same_organization,
    _normalize_company,
)


def _a(company: str = "", email: str = ""):
    return SimpleNamespace(company=company, email=email)


# --- Regression: the exact pair that triggered the bug ----------------------

def test_erin_chris_axe_compute_filtered():
    erin = _a(company="Axe Compute", email="erin.mcmahon@axecompute.com")
    chris = _a(company="Axe Compute", email="chris@axecompute.com")
    assert is_same_organization(erin, chris) is True


# --- Company-name match -----------------------------------------------------

def test_exact_company_match_filtered():
    assert is_same_organization(_a("Elliptic"), _a("Elliptic")) is True


def test_company_match_is_case_insensitive():
    assert is_same_organization(_a("ELLIPTIC"), _a("elliptic")) is True


def test_company_match_ignores_whitespace_variation():
    assert is_same_organization(_a("  Axe Compute "), _a("Axe   Compute")) is True


def test_corp_suffix_variants_collapse():
    # Acme Inc / Acme Inc. / Acme LLC / Acme, Inc. all reduce to "acme"
    assert is_same_organization(_a("Acme Inc"), _a("Acme Inc.")) is True
    assert is_same_organization(_a("Acme LLC"), _a("Acme")) is True
    assert is_same_organization(_a("Acme, Inc."), _a("Acme")) is True
    assert is_same_organization(_a("Bain & Company GmbH"), _a("Bain & Company")) is True


def test_different_companies_not_filtered():
    assert is_same_organization(_a("Elliptic"), _a("Chainalysis")) is False


def test_parent_subsidiary_treated_as_different():
    # Bain & Company vs Bain Capital are different orgs — strict policy keeps
    # them distinct.
    assert is_same_organization(_a("Bain & Company"), _a("Bain Capital")) is False


# --- Generic / freelance values -- never match each other --------------------

def test_two_freelancers_not_filtered():
    assert is_same_organization(_a("Freelance"), _a("Freelance")) is False
    assert is_same_organization(_a("Self-employed"), _a("Self-employed")) is False
    assert is_same_organization(_a("Independent"), _a("Independent")) is False
    assert is_same_organization(_a("Consultant"), _a("Consultant")) is False
    assert is_same_organization(_a("Stealth"), _a("Stealth Startup")) is False


def test_blank_company_not_filtered():
    assert is_same_organization(_a(""), _a("")) is False
    assert is_same_organization(_a(""), _a("Elliptic")) is False


def test_dashes_and_na_treated_as_blank():
    assert is_same_organization(_a("-"), _a("--")) is False
    assert is_same_organization(_a("N/A"), _a("none")) is False


# --- Email-domain match -----------------------------------------------------

def test_corporate_domain_match_filtered():
    a = _a(email="alice@elliptic.co")
    b = _a(email="bob@elliptic.co")
    assert is_same_organization(a, b) is True


def test_corporate_domain_match_case_insensitive():
    assert is_same_organization(
        _a(email="alice@Elliptic.CO"),
        _a(email="bob@elliptic.co"),
    ) is True


def test_freemail_domain_never_filters():
    # Two random people on gmail are NOT the same org.
    assert is_same_organization(
        _a(company="Elliptic", email="alice@gmail.com"),
        _a(company="Chainalysis", email="bob@gmail.com"),
    ) is False
    assert is_same_organization(
        _a(email="alice@outlook.com"),
        _a(email="bob@outlook.com"),
    ) is False
    assert is_same_organization(
        _a(email="alice@yahoo.com"),
        _a(email="bob@yahoo.com"),
    ) is False


def test_pot_speaker_alias_domain_treated_as_freemail():
    # @speaker.proofoftalk.io is a shared PoT-allocated alias for many
    # unrelated speakers; must NOT be treated as a shared org domain.
    assert is_same_organization(
        _a(company="Elliptic", email="speaker1@speaker.proofoftalk.io"),
        _a(company="Chainalysis", email="speaker2@speaker.proofoftalk.io"),
    ) is False


# --- Cross-signal -- one signal is enough -----------------------------------

def test_domain_matches_even_when_company_differs():
    # Same domain, slightly different company strings (one missing a word) —
    # still same org. This is the common case where company strings drift.
    assert is_same_organization(
        _a(company="Axe Compute", email="chris@axecompute.com"),
        _a(company="Axe", email="erin@axecompute.com"),
    ) is True


def test_company_matches_even_when_emails_are_freemail():
    # Both wrote the same employer in the registration form but use gmail.
    assert is_same_organization(
        _a(company="Coinbase", email="alice@gmail.com"),
        _a(company="Coinbase", email="bob@gmail.com"),
    ) is True


# --- Dict input -- duck-typed accessor accepts dicts -------------------------

def test_dict_input_works():
    a = {"company": "Elliptic", "email": "alice@elliptic.co"}
    b = {"company": "Elliptic", "email": "bob@elliptic.co"}
    assert is_same_organization(a, b) is True


# --- Normalization helper ---------------------------------------------------

def test_normalize_strips_corp_suffix_and_whitespace():
    assert _normalize_company("Acme Inc.") == "acme"
    assert _normalize_company("  ACME   LLC  ") == "acme"
    assert _normalize_company("Bain & Company GmbH") == "bain & company"


def test_normalize_returns_empty_for_generic():
    assert _normalize_company("Self") == ""
    assert _normalize_company("freelance") == ""
    assert _normalize_company("") == ""
    assert _normalize_company("  ") == ""
