"""Mailbox — one display name as it was written, used with one email address."""

from typing import Any, ClassVar

from django.core.exceptions import ValidationError
from django.db import models

from tap_grid.models import BaseModel
from tap_plugin.identity_core.contact import MAX_ADDRESS, MAX_DISPLAY_NAME, canonical_email, clean_display_name


class Mailbox(BaseModel):
    """A name and an address together, as a record stated them: ``George Chamales <george@example.com>``.

    RFC 5322 calls this pair a mailbox. A commit's author is one; so is the contact typed onto an
    application. The pair is its own thing because the name is not a property of the address
    (three systems use three names with one address) and it is not a property of the link from a
    record to the address either: a relationship that needs to carry a name is a missing node.
    So the record points at the mailbox, and the mailbox points at its address.

    Identity is ``(address, display_name)``: the canonical address and the name exactly as
    written. Two spellings of a name at one address are two mailboxes on one address node, and
    nothing merges them. A mailbox is not a person; a person is tied to one by the same edge that
    ties an account to a person.

    An account does not need a mailbox. A system's own user record is already the node for the
    party it names, carries its own name, and points at the address directly.

    ``address`` is a hotlink: the field and the edge to the address node must agree, so a mailbox
    cannot be written naming an address it has no edge to.

    Spec: specs/spec-identity-core-v0.md (req-identity-core-mailbox).
    """

    ENTITY_TYPE: ClassVar[str] = "identity_core__mailbox"
    ENTITY_NAME: ClassVar[str] = "Mailbox"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "One display name as written, used with one email address: the pair a commit's author line "
        "or a typed contact states. Not a person, and not the address itself."
    )
    ENTITY_ICON: ClassVar[str] = "mailbox"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = {}
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("address", "display_name")

    # Written out as literals: the plugin validator reads this declaration statically. A test holds
    # them equal to the names contact.py builds the edge with.
    HOTLINKS: ClassVar[list[dict[str, Any]]] = [
        {
            "name": "mailbox-address",
            "field": "address",
            "selector_type": "scalar",
            "selector": "",
            "edge_direction": "outbound",
            "edge_type": "DELIVERS_TO_ADDRESS__identity_core",
            "mode": "exact",
        }
    ]

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "address": {"type": "string", "minLength": 3, "maxLength": MAX_ADDRESS},
        "display_name": {"type": "string", "minLength": 1, "maxLength": MAX_DISPLAY_NAME},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = {
        "address": {"validation": "function"},
        "display_name": {"validation": "function"},
    }
    CREATE_REQUIRED: ClassVar[list[str]] = ["address", "display_name"]

    address = models.CharField(max_length=MAX_ADDRESS, db_index=True, help_text="The address the name is used with, in canonical form. Mirrored by the edge to the address node.")
    display_name = models.CharField(max_length=MAX_DISPLAY_NAME, db_index=True, help_text="The name exactly as the record wrote it, less surrounding space.")

    class Meta(BaseModel.Meta):
        db_table = "identity_core__mailbox"

    def validate_address(self) -> None:
        """``address`` is an email address already in canonical form."""
        if canonical_email(self.address) != self.address:
            raise ValidationError({"address": ["address must be an email address in canonical form (contact.canonical_email)."]})

    def validate_display_name(self) -> None:
        """``display_name`` is a name as written: not blank, not padded, no control character."""
        if clean_display_name(self.display_name) != self.display_name:
            raise ValidationError({"display_name": ["display_name must be a non-empty name with no surrounding space and no control character (contact.clean_display_name)."]})

    def get_name(self) -> str:
        return f"{self.display_name} <{self.address}>" if self.display_name and self.address else (self.address or "")

    def __str__(self) -> str:
        return self.get_name()
