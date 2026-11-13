"""Email address — one mailbox address, the value that accounts in different systems share."""

from typing import Any, ClassVar

from django.core.exceptions import ValidationError
from django.db import models

from tap_grid.models import BaseModel
from tap_plugin.identity_core.contact import MAX_ADDRESS, canonical_email


class EmailAddress(BaseModel):
    """One email address, independent of who uses it and of what any system calls them.

    An identity provider's user, a commit's author line and a contact typed onto an application
    record can all name the same address. Each points at this node, so "everything that names
    this address" is one hop. The node is not a person and claims nothing about who reads the
    mail: an address is reassigned and aliased, which is why a human is never keyed by one.

    Identity is ``address`` in canonical form, lower-cased (``contact.canonical_email``). A write
    that is not in that form is refused, never rewritten, so every observer must use the one
    function and two of them cannot disagree. Nothing beyond case is folded.

    The type holds no name. The name a system uses with an address is that system's fact: it is
    on the system's own account, or on a mailbox (``identity_core__mailbox``).

    Spec: specs/spec-identity-core-v0.md (req-identity-core-email-address).
    """

    ENTITY_TYPE: ClassVar[str] = "identity_core__email_address"
    ENTITY_NAME: ClassVar[str] = "Email Address"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "One email address, shared by every record that names it. Not a person: who uses it is "
        "asserted by an edge, and the name used with it is on a mailbox or on the account."
    )
    ENTITY_ICON: ClassVar[str] = "email-address"
    # No default dimension: an address belongs to no one system.
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = {}
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("address",)

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "address": {"type": "string", "minLength": 3, "maxLength": MAX_ADDRESS},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = {
        "address": {"validation": "function"},
    }
    CREATE_REQUIRED: ClassVar[list[str]] = ["address"]

    address = models.CharField(max_length=MAX_ADDRESS, db_index=True, help_text="The address in canonical form: lower-cased, nothing else folded.")

    class Meta(BaseModel.Meta):
        db_table = "identity_core__email_address"

    def validate_address(self) -> None:
        """``address`` is an email address already in canonical form."""
        if canonical_email(self.address) != self.address:
            raise ValidationError({"address": ["address must be an email address in canonical form (contact.canonical_email): lower-cased, with no surrounding space."]})

    def get_name(self) -> str:
        return self.address or ""

    def __str__(self) -> str:
        return self.get_name()
