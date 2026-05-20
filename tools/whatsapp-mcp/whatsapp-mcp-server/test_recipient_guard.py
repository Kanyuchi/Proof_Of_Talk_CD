import recipient_guard


def test_no_restriction_when_unset(monkeypatch):
    monkeypatch.delenv("WHATSAPP_ALLOWED_JIDS", raising=False)
    assert recipient_guard.is_allowed_recipient("999999")


def test_allows_listed_in_both_forms(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ALLOWED_JIDS", "491732532061@s.whatsapp.net")
    assert recipient_guard.is_allowed_recipient("491732532061")
    assert recipient_guard.is_allowed_recipient("491732532061@s.whatsapp.net")


def test_blocks_unlisted(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ALLOWED_JIDS", "491732532061@s.whatsapp.net")
    assert not recipient_guard.is_allowed_recipient("999999")
    assert not recipient_guard.is_allowed_recipient("999999@s.whatsapp.net")
