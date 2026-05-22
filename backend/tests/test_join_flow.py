import pytest
from pydantic import ValidationError

from app.schemas.auth import JoinRequest


def test_join_request_rejects_weak_password():
    with pytest.raises(ValidationError):
        JoinRequest(invite_code="x", email="a@b.com", password="weak", name="A")


def test_join_request_rejects_blank_name():
    with pytest.raises(ValidationError):
        JoinRequest(invite_code="x", email="a@b.com", password="Strong1pass", name="   ")


def test_join_request_valid_minimal():
    r = JoinRequest(invite_code="code", email="a@b.com", password="Strong1pass", name="Ann")
    assert r.invite_code == "code"
    assert r.email == "a@b.com"
    assert r.ticket_type == "SPONSOR"
