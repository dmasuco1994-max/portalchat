"""Unit tests for the pure inbound helpers and the Evolution state mapper."""
from app.services.evolution import map_state_to_status
from app.services.webhook_inbound import (
    _extract_content,
    _extract_phone,
    _normalize_event,
)


class TestNormalizeEvent:
    def test_dotted_and_snake_variants(self):
        assert _normalize_event("messages.upsert") == "MESSAGES_UPSERT"
        assert _normalize_event("MESSAGES_UPSERT") == "MESSAGES_UPSERT"
        assert _normalize_event("connection.update") == "CONNECTION_UPDATE"


class TestExtractPhone:
    def test_strips_suffix_and_nondigits(self):
        assert _extract_phone("5491155@s.whatsapp.net") == "5491155"

    def test_none_and_empty(self):
        assert _extract_phone(None) is None
        assert _extract_phone("@s.whatsapp.net") is None


class TestExtractContent:
    def test_plain_text(self):
        ct, text, url, mime = _extract_content({"conversation": "hola"})
        assert (ct, text, url, mime) == ("text", "hola", None, None)

    def test_extended_text(self):
        ct, text, _url, _mime = _extract_content(
            {"extendedTextMessage": {"text": "x"}}
        )
        assert ct == "text" and text == "x"

    def test_image(self):
        ct, caption, url, mime = _extract_content(
            {
                "imageMessage": {
                    "caption": "foto",
                    "url": "https://cdn/x",
                    "mimetype": "image/jpeg",
                }
            }
        )
        assert ct == "image"
        assert caption == "foto"
        assert url == "https://cdn/x"
        assert mime == "image/jpeg"

    def test_unknown_and_none(self):
        assert _extract_content(None)[0] == "unknown"
        assert _extract_content({"weirdMessage": {}})[0] == "unknown"


class TestMapStateToStatus:
    def test_known_states(self):
        assert map_state_to_status("open") == "connected"
        assert map_state_to_status("connecting") == "connecting"
        assert map_state_to_status("qr") == "connecting"
        assert map_state_to_status("close") == "disconnected"
        assert map_state_to_status("logout") == "disconnected"

    def test_unknown_and_none_default_to_created(self):
        assert map_state_to_status(None) == "created"
        assert map_state_to_status("weird") == "created"
