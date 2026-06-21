"""Unit tests for the pure webhook adapter builders.

These exercise the payload-shaping functions in services.webhook_outbound that
turn an Evolution event into each CRM format. They are pure (no DB, no network),
so they pin down the contract we send to Neotel — the exact thing that was hard
to verify by eye during the integration.
"""
from app.services.webhook_outbound import (
    build_apiwha_failed_event,
    build_apiwha_inbox_event,
    build_apiwha_processed_event,
    build_external_neotel_payload,
    build_neotel_event_payload,
    build_neotel_message_payload,
    derive_neotel_events_url,
    hash_uuid_to_int,
)


def _upsert_event(
    text="hola",
    remote="5491155@s.whatsapp.net",
    mid="ABC123",
    push="Juan",
    ts=1700000000,
):
    return {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": remote, "id": mid, "fromMe": False},
            "message": {"conversation": text},
            "pushName": push,
            "messageTimestamp": ts,
        },
    }


class TestApiwha:
    def test_inbox_event(self):
        ev = build_apiwha_inbox_event(
            our_phone_number="5490000", raw_event=_upsert_event()
        )
        assert ev["event"] == "INBOX"
        assert ev["from"] == "5491155"
        assert ev["to"] == "5490000"
        assert ev["text"] == "hola"
        assert ev["pushname"] == "Juan"

    def test_inbox_extended_text(self):
        e = _upsert_event()
        e["data"]["message"] = {"extendedTextMessage": {"text": "mundo"}}
        ev = build_apiwha_inbox_event(our_phone_number="x", raw_event=e)
        assert ev["text"] == "mundo"

    def test_processed_event(self):
        p = build_apiwha_processed_event(
            our_phone_number="5490000", raw_event=_upsert_event()
        )
        assert p["event"] == "MESSAGEPROCESSED"
        assert p["from"] == "5490000"
        assert p["to"] == "5491155"

    def test_failed_event(self):
        f = build_apiwha_failed_event(
            our_phone_number="5490000", raw_event=_upsert_event()
        )
        assert f["event"] == "MESSAGEFAILED"
        assert f["to"] == "5491155"


class TestNeotelCustom:
    def test_message_payload_shape(self):
        p = build_neotel_message_payload(
            raw_event=_upsert_event(),
            account_id="acct",
            conversation_id_int=42,
            our_phone_number="5490000",
            remote_phone="5491155",
            remote_name="Juan",
            content_type="text",
        )
        assert p["accountId"] == "acct"
        m = p["messages"][0]
        assert m["body"] == "hola"
        assert m["type"] == "chat"            # text -> chat per NEOTEL_CONTENT_TYPE_MAP
        assert m["caption"] == ""             # obligatorio en la spec de Neotel
        assert m["contactName"] == "Juan"
        assert m["contactNumber"] == "5491155"
        assert m["conversationId"] == 42
        assert m["time"] == 1700000000 * 1000  # segundos -> ms
        assert m["isBot"] is False

    def test_message_type_mapping_image(self):
        p = build_neotel_message_payload(
            raw_event=_upsert_event(),
            account_id="a",
            conversation_id_int=1,
            our_phone_number="x",
            remote_phone="y",
            remote_name=None,
            content_type="image",
        )
        assert p["messages"][0]["type"] == "image"

    def test_event_payload_maps_status(self):
        ev = build_neotel_event_payload(
            raw_event={"data": {"key": {"id": "M1"}, "status": "DELIVERY_ACK"}},
            account_id="acct",
        )
        assert ev == {
            "InstanceId": "acct",
            "events": [{"id": "M1", "status": "delivered"}],
        }

    def test_event_payload_unknown_status_is_none(self):
        ev = build_neotel_event_payload(
            raw_event={"data": {"key": {"id": "M1"}, "status": "BOGUS"}},
            account_id="acct",
        )
        assert ev is None

    def test_derive_events_url(self):
        assert (
            derive_neotel_events_url(
                "https://s2.neotel.cc/neowebhook/api/CustomAccount/Messages/ch@prov"
            )
            == "https://s2.neotel.cc/neowebhook/api/CustomAccount/Events/ch@prov"
        )


class TestHashUuidToInt:
    def test_deterministic_and_in_signed_31bit_range(self):
        u = "550e8400-e29b-41d4-a716-446655440000"
        a = hash_uuid_to_int(u)
        assert a == hash_uuid_to_int(u)        # determinista
        assert 0 <= a <= 0x7FFFFFFF             # positivo, cabe en int firmado

    def test_none_or_empty_is_zero(self):
        assert hash_uuid_to_int(None) == 0
        assert hash_uuid_to_int("") == 0


class TestExternalNeotel:
    def test_payload_shape(self):
        p = build_external_neotel_payload(
            raw_event=_upsert_event(),
            application_id="app-1",
            remote_phone="5491155",
            remote_name="Juan",
            content_type="text",
            message_uuid="uuid-1",
        )
        assert p["text"] == "hola"
        assert p["contactId"] == "5491155"
        assert p["contactName"] == "Juan"
        assert p["accountId"] == "app-1"
        assert p["isInbound"] is True
        assert p["attachment"] is None
        assert p["externalId"] == "uuid-1"

    def test_contact_name_falls_back_to_phone(self):
        p = build_external_neotel_payload(
            raw_event=_upsert_event(),
            application_id="app-1",
            remote_phone="5491155",
            remote_name=None,
            content_type="text",
            message_uuid=None,
        )
        assert p["contactName"] == "5491155"
