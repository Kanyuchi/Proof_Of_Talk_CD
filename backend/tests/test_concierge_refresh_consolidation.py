def test_concierge_uses_shared_refresh():
    import app.api.routes.chat as chat
    assert hasattr(chat, "refresh_profile_matches")
    assert not hasattr(chat, "_refresh_attendee_matches_bg")
