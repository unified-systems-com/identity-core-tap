"""Contact primitives — the one place an email address and a phone number are made canonical.

Many systems hold the same address or number: an identity provider's user record, a commit's
author line, a contact someone typed onto an application. They converge on one node only if every
observer writes the same key, so the canonical form is defined here, once, and observers call it.
The models refuse a value that is not already in this form; nothing is silently rewritten on save.

Three shapes:

- an **email address**, ``george@example.com``: the mailbox's address, lower-cased;
- a **mailbox**, ``George Chamales <george@example.com>``: one display name as it was written,
  used with one address (RFC 5322 calls this pair a mailbox);
- a **phone number**: its country code and its national number as separate values.

What is deliberately not done: an address is never folded beyond case (dots and plus-tags mean
different things at different providers), and a phone number written without a country code is
never given one. It stays a number without a country, which the stating record keeps and no
shared node holds.

Spec: specs/spec-identity-core-v0.md (req-identity-core-email-address, -mailbox, -phone-number).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

EMAIL_ADDRESS_TYPE = "identity_core__email_address"
MAILBOX_TYPE = "identity_core__mailbox"
PHONE_NUMBER_TYPE = "identity_core__phone_number"
MAILBOX_ADDRESS_EDGE = "DELIVERS_TO_ADDRESS__identity_core"
#: The name of the mailbox's hotlink: its ``address`` field and its edge to the address node agree.
MAILBOX_ADDRESS_HOTLINK = "mailbox-address"

MAX_ADDRESS = 254
MAX_DISPLAY_NAME = 256
#: The longest number E.164 allows, country code included.
MAX_PHONE_DIGITS = 15

# One @, something either side, no whitespace or control character, and a dot-free or dotted domain.
_ADDRESS = re.compile(r"[^\s@\x00-\x1f\x7f<>]+@[^\s@\x00-\x1f\x7f<>]+")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_SEPARATORS = re.compile(r"[\s().\-]")
_EXTENSION = re.compile(r"(?:;ext=|\s*(?:ext\.?|x|#)\s*)(\d{1,16})\s*$", re.IGNORECASE)
# How long a country code is follows from its leading digits (the E.164 zone structure): zones 1
# and 7 are one digit, the two-digit codes are the ones listed, and every other code has three.
_TWO_DIGIT_CODES = frozenset(
    "20 27 30 31 32 33 34 36 39 40 41 43 44 45 46 47 48 49 51 52 53 54 55 56 57 58 "
    "60 61 62 63 64 65 66 81 82 84 86 90 91 92 93 94 95 98".split()
)


def canonical_email(raw: Any) -> str | None:
    """The canonical form of an email address, or None when ``raw`` is not one.

    Surrounding whitespace is dropped and the whole address is lower-cased. Nothing else is
    folded. A display name is not accepted here: pass the address alone.

    The check is on shape, not deliverability: one ``@``; a local part with no leading, trailing
    or doubled dot; a domain of labels made of letters, digits and inner hyphens. A quoted local
    part and an address literal (``user@[192.0.2.1]``) are not accepted. Malformed text stays on
    the record that held it and never becomes a shared node.
    """
    if not isinstance(raw, str):
        return None
    address = raw.strip()
    if not address or len(address) > MAX_ADDRESS or not _ADDRESS.fullmatch(address):
        return None
    local, _, domain = address.rpartition("@")
    if not local or local.startswith(".") or local.endswith(".") or ".." in local:
        return None
    if not all(_is_domain_label(label) for label in domain.split(".")):
        return None
    return address.lower()


def _is_domain_label(label: str) -> bool:
    """One dot-separated part of a domain: letters and digits of any script, and inner hyphens."""
    return bool(label) and not label.startswith("-") and not label.endswith("-") and all(char.isalnum() or char == "-" for char in label)


def clean_display_name(raw: Any) -> str | None:
    """A display name as written, less surrounding whitespace; None when there is none to keep."""
    if not isinstance(raw, str):
        return None
    name = raw.strip()
    if not name or len(name) > MAX_DISPLAY_NAME or _CONTROL.search(name):
        return None
    return name


def country_code_length(digits: str) -> int:
    """How many leading digits of an international number are its country code."""
    if digits[:1] in ("1", "7"):
        return 1
    return 2 if digits[:2] in _TWO_DIGIT_CODES else 3


@dataclass(frozen=True)
class Phone:
    """A phone number as far as its text allows it to be known.

    ``country_code`` is None when the text gave none: never sent, not "no country". ``source``
    says how the country code is known: ``plus_sign`` when the text was in international form,
    ``not_given`` otherwise. ``raw`` is the text exactly as it was stated.
    """

    raw: str
    country_code: str | None
    national_number: str
    extension: str
    source: str

    @property
    def shareable(self) -> bool:
        """Whether this number identifies one line anywhere: only with a country code."""
        return self.country_code is not None


def parse_phone(raw: Any) -> Phone | None:
    """Read a phone number from text; None when the text is not a phone number.

    Text beginning ``+`` is in international form and is split into country code and national
    number. Any other text keeps its digits as the national number with no country code: no
    default country is ever assumed. An extension written ``;ext=``, ``ext``, ``x`` or ``#`` is
    kept apart.
    """
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    extension = ""
    found = _EXTENSION.search(text)
    if found:
        extension, text = found.group(1), text[: found.start()]
    international = text.startswith("+")
    digits = _SEPARATORS.sub("", text[1:] if international else text)
    if not digits.isdigit() or not digits.isascii():
        return None
    if not international:
        return Phone(raw, None, digits, extension, "not_given") if len(digits) <= MAX_PHONE_DIGITS else None
    length = country_code_length(digits)
    if digits.startswith("0") or len(digits) <= length or len(digits) > MAX_PHONE_DIGITS:
        return None
    return Phone(raw, digits[:length], digits[length:], extension, "plus_sign")


def _node(ref: str, entity_type: str, name: str, fields: dict[str, Any]) -> dict[str, Any]:
    return {"entity": {"ref": ref, "entity_type": entity_type, "name": name, "dimensions": {}}, "node": fields}


def email_address_node(ref: str, raw: Any) -> dict[str, Any] | None:
    """The GRIFT node for an address, keyed by its canonical form; None when ``raw`` is not an address."""
    address = canonical_email(raw)
    return _node(ref, EMAIL_ADDRESS_TYPE, address, {"address": address}) if address else None


def mailbox_fragment(ref: str, display_name: Any, raw_address: Any) -> dict[str, list[dict[str, Any]]] | None:
    """The nodes and the edge for one mailbox: the address, the mailbox, and the edge that joins them.

    None when there is no usable name or address: a mailbox is the pair, and a name alone
    identifies nobody. The address node's ref is ``<ref>:address`` and the mailbox's is ``ref``,
    so a caller can point at either. The edge carries the hotlink data the mailbox's declaration
    is checked against, so a mailbox can never be written naming an address it has no edge to.
    """
    name, address = clean_display_name(display_name), canonical_email(raw_address)
    if name is None or address is None:
        return None
    address_ref = f"{ref}:address"
    edge = {
        "entity": {"ref": f"{ref}:delivers", "entity_type": "edge", "name": MAILBOX_ADDRESS_EDGE, "dimensions": {}},
        "edge": {
            "from_ref": ref,
            "to_ref": address_ref,
            "edge_type": MAILBOX_ADDRESS_EDGE,
            "properties": {"hotlink": {"model": MAILBOX_TYPE, "spec": MAILBOX_ADDRESS_HOTLINK, "value": address}},
        },
    }
    nodes = [
        _node(address_ref, EMAIL_ADDRESS_TYPE, address, {"address": address}),
        _node(ref, MAILBOX_TYPE, f"{name} <{address}>", {"address": address, "display_name": name}),
    ]
    return {"nodes": nodes, "edges": [edge]}


def phone_number_node(ref: str, phone: Phone | None) -> dict[str, Any] | None:
    """The GRIFT node for a phone number; None unless the number has a country code."""
    if phone is None or not phone.shareable:
        return None
    fields = {"country_code": phone.country_code, "national_number": phone.national_number, "extension": phone.extension}
    name = f"+{phone.country_code} {phone.national_number}" + (f" x{phone.extension}" if phone.extension else "")
    return _node(ref, PHONE_NUMBER_TYPE, name, fields)
