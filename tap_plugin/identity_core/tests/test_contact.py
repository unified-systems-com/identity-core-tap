"""Email address, mailbox and phone number (req-identity-core-email-address, -mailbox, -phone-number)."""

from __future__ import annotations

import pytest
from tap_plugin.identity_core import contact
from tap_plugin.identity_core.models import EmailAddress, Mailbox, PhoneNumber

import uuid

from tap_grid.caller_context import CallerContext
from tap_grid.grift.importer import grift_import
from tap_grid.models import Edge, Entity
from tap_grid.services import WriteOperation, write_batch

ADDRESS, MAILBOX, PHONE = contact.EMAIL_ADDRESS_TYPE, contact.MAILBOX_TYPE, contact.PHONE_NUMBER_TYPE


def _write(*ops: WriteOperation) -> list:
    return write_batch(list(ops), caller_context=CallerContext()).results


def _node(type_slug: str, payload: dict) -> object:
    return _write(WriteOperation(verb="create_node", type_slug=type_slug, payload=payload))[0]


def _edge(edge_type: str, src: object, dst: object, properties: dict | None = None) -> object:
    return _write(WriteOperation(verb="create_edge", from_target=src.entity_id, to_target=dst.entity_id, edge_type=edge_type, payload={"properties": properties or {}}))[0]


class TestCanonicalEmail:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("george@example.com", "george@example.com"),
            ("  George@Example.COM ", "george@example.com"),
            ("g.chamales+tap@example.com", "g.chamales+tap@example.com"),
            ("user@localhost", "user@localhost"),
            ("o'brien_x-1@mail-host.example.co.uk", "o'brien_x-1@mail-host.example.co.uk"),
            ("Jürgen@Bücher.example", "jürgen@bücher.example"),
        ],
    )
    def test_case_and_surrounding_space_are_the_only_things_folded(self, raw, expected):
        assert contact.canonical_email(raw) == expected

    @pytest.mark.parametrize("raw", ["george@example.com", "  George@Example.COM ", "Jürgen@Bücher.example", "ΑΒΓ@ΔΕΖ.example", "STRASSE@example.com", "a@İ.com", "ǅ@example.com", "o'brien_x-1@mail-host.example.co.uk"])
    def test_the_canonical_form_is_its_own_canonical_form(self, raw):
        """Whatever comes out goes back in unchanged, so a node this builds is never one the model refuses."""
        once = contact.canonical_email(raw)
        assert once is None or contact.canonical_email(once) == once

    @pytest.mark.parametrize("raw", ["", " ", "george", "@example.com", "george@", "a@b@c", "george @example.com", "George <george@example.com>", "george@example..com", "george@.example.com", "george@example.com.", "a\n@b.com", None, 7, "x" * 250 + "@example.com", "a..b@example.com", ".a@example.com", "a.@example.com", "a@example_com", "a@-example.com", "a@example-.com", "user@[192.0.2.1]", '"quoted local"@example.com', "a,b@example.com", "foo()@example.com", "a;b@example.com", "a@İ.com", "a\u0307@example.com"])
    def test_what_is_not_an_address_is_none(self, raw):
        assert contact.canonical_email(raw) is None


class TestParsePhone:
    @pytest.mark.parametrize(
        "raw, code, number",
        [
            ("+1 415 555 0100", "1", "4155550100"),
            ("+1 (415) 555-0100", "1", "4155550100"),
            ("+44 20 7946 0958", "44", "2079460958"),
            ("+7 495 123-45-67", "7", "4951234567"),
            ("+353 1 234 5678", "353", "12345678"),
            ("+86.10.1234.5678", "86", "1012345678"),
            ("+972-3-1234567", "972", "31234567"),
        ],
    )
    def test_an_international_number_is_split_at_its_country_code(self, raw, code, number):
        got = contact.parse_phone(raw)
        assert (got.country_code, got.national_number, got.extension, got.source, got.raw) == (code, number, "", "plus_sign", raw)
        assert got.shareable

    @pytest.mark.parametrize("raw, digits", [("555-0100", "5550100"), ("(415) 555 0100", "4155550100"), ("020 7946 0958", "02079460958")])
    def test_a_number_with_no_country_code_is_never_given_one(self, raw, digits):
        got = contact.parse_phone(raw)
        assert (got.country_code, got.national_number, got.source) == (None, digits, "not_given")
        assert not got.shareable

    @pytest.mark.parametrize("raw, extension", [("+1 415 555 0100 x12", "12"), ("+1 415 555 0100;ext=5555", "5555"), ("+1 415 555 0100 ext. 7", "7"), ("+14155550100#9", "9")])
    def test_an_extension_is_kept_apart(self, raw, extension):
        got = contact.parse_phone(raw)
        assert (got.country_code, got.national_number, got.extension) == ("1", "4155550100", extension)

    @pytest.mark.parametrize("raw", ["", "   ", "call me", "+", "+0 123 456", "+1", "+1 415 555 0100 0000 0000", "415-555-01OO", "+1 415 ５５５ 0100", None, 4155550100])
    def test_what_is_not_a_phone_number_is_none(self, raw):
        assert contact.parse_phone(raw) is None

    def test_the_length_of_a_country_code_follows_its_leading_digits(self):
        assert [contact.country_code_length(d) for d in ("14155550100", "74951234567", "442079460958", "35312345678", "97231234567", "8613800000000")] == [1, 1, 2, 3, 3, 2]


class TestFragments:
    def test_a_mailbox_fragment_is_the_address_the_mailbox_and_the_edge_between(self):
        got = contact.mailbox_fragment("m", " George Chamales ", "George@Example.com")
        assert [(n["entity"]["ref"], n["entity"]["entity_type"], n["node"]) for n in got["nodes"]] == [
            ("m:address", ADDRESS, {"address": "george@example.com"}),
            ("m", MAILBOX, {"address": "george@example.com", "display_name": "George Chamales"}),
        ]
        (edge,) = got["edges"]
        assert (edge["edge"]["from_ref"], edge["edge"]["to_ref"], edge["edge"]["edge_type"]) == ("m", "m:address", contact.MAILBOX_ADDRESS_EDGE)
        assert edge["edge"]["properties"]["hotlink"] == {"model": MAILBOX, "spec": "mailbox-address", "value": "george@example.com"}

    @pytest.mark.parametrize("name, address", [("George", "not an address"), ("", "george@example.com"), ("   ", "george@example.com"), (None, "george@example.com"), ("George", None)])
    def test_a_name_alone_or_an_address_alone_is_no_mailbox(self, name, address):
        assert contact.mailbox_fragment("m", name, address) is None

    def test_a_phone_node_exists_only_with_a_country_code(self):
        assert contact.phone_number_node("p", contact.parse_phone("555-0100")) is None
        assert contact.phone_number_node("p", None) is None
        node = contact.phone_number_node("p", contact.parse_phone("+1 415 555 0100 x12"))
        assert node["node"] == {"country_code": "1", "national_number": "4155550100", "extension": "12"}
        assert node["entity"]["name"] == "+1 4155550100 x12"

    def test_an_address_node_is_keyed_by_the_canonical_form(self):
        assert contact.email_address_node("a", " George@Example.com ")["node"] == {"address": "george@example.com"}
        assert contact.email_address_node("a", "nope") is None


@pytest.mark.django_db
class TestEmailAddress:
    def test_create_and_display(self):
        made = _node(ADDRESS, {"address": "george@example.com"})
        assert made.success
        assert EmailAddress.all_objects.get(entity_id=made.entity_id).address == "george@example.com"
        assert Entity.objects.get(pk=made.entity_id).name == "george@example.com"

    @pytest.mark.parametrize("address", ["George@example.com", " george@example.com", "george", "George <george@example.com>"])
    def test_an_address_not_in_canonical_form_is_refused_not_rewritten(self, address):
        assert not _node(ADDRESS, {"address": address}).success
        assert not EmailAddress.objects.exists()

    def test_it_holds_no_name(self):
        assert not _node(ADDRESS, {"address": "george@example.com", "name": "George"}).success

    def test_any_record_can_be_registered_with_it_and_a_human_can_use_it(self):
        address = _node(ADDRESS, {"address": "george@example.com"})
        account = _node("identity_core__organization", {"name": "stands in for some plugin's account type"})
        human = _node("identity_core__human", {"handle": "e1042"})
        assert _edge("REGISTERED_WITH_EMAIL__identity_core", account, address).success
        assert _edge("USES_EMAIL_ADDRESS__identity_core", human, address).success


def _import(nodes: list[dict], edges: list[dict]):
    """One GRIFT batch through the real importer, the way a collector writes."""
    batch = {
        "batch_entity": {"entity_id": str(uuid.uuid4()), "entity_type": "batch", "name": "contact test", "dimensions": {}},
        "batch_node": {"source": "tap_plugin.identity_core.tests", "name": "contact test", "description": "contact test"},
        "nodes": nodes,
        "edges": edges,
    }
    return grift_import({"metadata": {"grift_version": "0"}, "_reserved": {}, "batches": [batch]})


@pytest.mark.django_db
class TestMailbox:
    def write(self, name: str = "George Chamales", address: str = "george@example.com"):
        got = contact.mailbox_fragment(f"m-{name}", name, address)
        return _import(got["nodes"], got["edges"])

    def test_the_fragment_writes_the_address_the_mailbox_and_the_edge(self):
        result = self.write()
        assert result.success, result
        box = Mailbox.objects.get()
        assert (box.address, box.display_name) == ("george@example.com", "George Chamales")
        assert Entity.objects.get(pk=box.entity_id).name == "George Chamales <george@example.com>"
        edge = Edge.objects.get(edge_type=contact.MAILBOX_ADDRESS_EDGE)
        assert (edge.from_entity_id, edge.to_entity_id) == (box.entity_id, EmailAddress.objects.get().entity_id)

    def test_the_declared_hotlink_is_the_one_the_fragment_writes(self):
        (declared,) = Mailbox.HOTLINKS
        assert (declared["name"], declared["edge_type"]) == (contact.MAILBOX_ADDRESS_HOTLINK, contact.MAILBOX_ADDRESS_EDGE)

    def test_two_names_at_one_address_are_two_mailboxes_on_one_address(self):
        assert self.write("George Chamales").success
        assert self.write("gchamales").success
        assert EmailAddress.objects.count() == 1 and Mailbox.objects.count() == 2
        address = EmailAddress.objects.get()
        assert Edge.objects.filter(edge_type=contact.MAILBOX_ADDRESS_EDGE, to_entity_id=address.entity_id).count() == 2

    def test_writing_the_same_mailbox_again_makes_no_second_one(self):
        assert self.write().success and self.write().success
        assert (EmailAddress.objects.count(), Mailbox.objects.count(), Edge.objects.filter(edge_type=contact.MAILBOX_ADDRESS_EDGE).count()) == (1, 1, 1)

    def test_a_mailbox_with_no_edge_to_its_address_is_refused(self):
        """The hotlink: the address field and the edge must agree, so the field cannot stand alone."""
        got = contact.mailbox_fragment("m", "George", "george@example.com")
        assert not _import(got["nodes"], []).success
        assert not Mailbox.objects.exists()

    def test_the_service_layer_refuses_it_too_not_only_the_importer(self):
        """A valid mailbox payload written alone through ``write_batch`` has no edge, so it is refused there as well."""
        made = _node(MAILBOX, {"address": "george@example.com", "display_name": "George"})
        assert not made.success
        assert not Mailbox.objects.exists()

    def test_a_mailbox_whose_edge_names_another_address_is_refused(self):
        got = contact.mailbox_fragment("m", "George", "george@example.com")
        got["nodes"][0]["node"]["address"] = "other@example.com"
        got["edges"][0]["edge"]["properties"]["hotlink"]["value"] = "other@example.com"
        assert not _import(got["nodes"], got["edges"]).success
        assert not Mailbox.objects.exists()

    @pytest.mark.parametrize("payload", [{"address": "George@example.com", "display_name": "George"}, {"address": "george@example.com", "display_name": " George "}, {"address": "george@example.com", "display_name": ""}, {"address": "george@example.com"}, {"display_name": "George"}])
    def test_a_padded_name_or_an_uncanonical_address_is_refused(self, payload):
        assert not _node(MAILBOX, payload).success

    def test_a_record_names_a_mailbox_as_its_contact_and_a_human_can_hold_it(self):
        assert self.write().success
        box = Mailbox.objects.get()
        record = _node("identity_core__organization", {"name": "stands in for an application record"})
        human = _node("identity_core__human", {"handle": "e1042"})
        named = _write(WriteOperation(verb="create_edge", from_target=record.entity_id, to_target=box.entity_id, edge_type="NAMES_CONTACT_MAILBOX__identity_core"))[0]
        held = _write(WriteOperation(verb="create_edge", from_target=box.entity_id, to_target=human.entity_id, edge_type="HELD_BY_HUMAN__identity_core"))[0]
        assert named.success and held.success


@pytest.mark.django_db
class TestPhoneNumber:
    def test_create_and_display(self):
        made = _node(PHONE, {"country_code": "1", "national_number": "4155550100"})
        assert made.success
        number = PhoneNumber.all_objects.get(entity_id=made.entity_id)
        assert (number.country_code, number.national_number, number.extension) == ("1", "4155550100", "")
        assert Entity.objects.get(pk=made.entity_id).name == "+1 4155550100"

    def test_an_extension_makes_a_different_number(self):
        assert _node(PHONE, {"country_code": "1", "national_number": "4155550100", "extension": ""}).success
        assert _node(PHONE, {"country_code": "1", "national_number": "4155550100", "extension": "12"}).success
        assert PhoneNumber.objects.count() == 2

    @pytest.mark.parametrize(
        "payload",
        [
            {"national_number": "4155550100"},
            {"country_code": "", "national_number": "4155550100"},
            {"country_code": "+1", "national_number": "4155550100"},
            {"country_code": "1", "national_number": "415-555-0100"},
            {"country_code": "14", "national_number": "155550100"},
            {"country_code": "4", "national_number": "42079460958"},
            {"country_code": "0", "national_number": "2079460958"},
            {"country_code": "353", "national_number": "1234567890123"},
        ],
    )
    def test_a_number_without_a_real_country_code_is_refused(self, payload):
        assert not _node(PHONE, payload).success
        assert not PhoneNumber.objects.exists()

    def test_records_point_at_it(self):
        number = _node(PHONE, {"country_code": "44", "national_number": "2079460958"})
        record = _node("identity_core__organization", {"name": "stands in for a record"})
        assert _edge("NAMES_CONTACT_PHONE__identity_core", record, number).success
        assert _edge("REGISTERED_WITH_PHONE__identity_core", record, number).success


@pytest.mark.django_db
def test_a_record_names_an_organization_as_the_party_behind_its_contact():
    organization = _node("identity_core__organization", {"name": "Acme Corp"})
    record = _node("identity_core__human", {"handle": "stands-in-for-a-record"})
    assert _edge("NAMES_CONTACT_ORGANIZATION__identity_core", record, organization).success


CONTACT_EDGES = ("DELIVERS_TO_ADDRESS", "REGISTERED_WITH_EMAIL", "USES_EMAIL_ADDRESS", "NAMES_CONTACT_MAILBOX", "REGISTERED_WITH_PHONE", "NAMES_CONTACT_PHONE", "NAMES_CONTACT_ORGANIZATION")


@pytest.mark.parametrize("name", CONTACT_EDGES)
def test_a_contact_edge_carries_no_property_and_is_one_edge_per_pair(name):
    """req-identity-core-contact-edges-2, -3: context on an edge means a missing node, so there is none."""
    import json
    from pathlib import Path

    definition = json.loads((Path(__file__).resolve().parent.parent / "edges" / f"{name}.edge.json").read_text())
    assert definition["property_schema"] == {"type": "object", "additionalProperties": False, "properties": {}}
    assert definition["identity"] == {"discriminators": []}
    assert definition["slug"] == f"{name}__identity_core"
