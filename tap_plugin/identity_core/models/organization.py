"""Organization — a party that holds identities: a company, agency or other body people act for."""

from typing import Any, ClassVar

from django.db import models

from tap_grid.event_time import NO_EVENT_TIME
from tap_grid.models import BaseModel


class Organization(BaseModel):
    """A party that holds identities: a company, agency, or other body people act on behalf of.

    Deliberately role-free. Whether an organization is a customer, a vendor, an assessor or the
    operator is a relationship some other plugin asserts about it, never its type: the same
    company is a customer in one instance and a vendor in another, and a type that bakes one
    view in cannot be shared. An instance plugin that needs "customer" draws that edge itself.

    ``domain`` is the organization's primary DNS domain when one is known; blank means not
    observed, not "has none". There is no free-form ``configuration`` blob: nothing collects an
    organization's source record, so the field would only be a place for unchosen data to collect. Identity rests on ``name`` in v0 because a designed organization
    often has no domain yet; revisit when an observer can supply a stronger key.

    Spec: specs/spec-identity-core-v0.md (req-identity-core-organization).
    """

    ENTITY_TYPE: ClassVar[str] = "identity_core__organization"
    ENTITY_NAME: ClassVar[str] = "Organization"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "A party that holds identities: a company, agency or other body people act on behalf of. "
        "Role-free: customer, vendor or operator is a relationship asserted elsewhere."
    )
    ENTITY_ICON: ClassVar[str] = "organization"
    # No default dimension: `identity.protocol` does not apply (an organization is not a protocol
    # artefact), and a party-kind value would only restate the entity type.
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = {}
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("name",)
    # No event time: a role-free party record with name and domain only; no source time is stored.
    EVENT_TIME = NO_EVENT_TIME
    # Same amber/gold identity-anchor palette as oidc_issuer: both are identity substrate.
    DEFAULT_DISPLAY: ClassVar[dict[str, Any]] = {
        "tap_viz": {
            "shape": "round-rectangle",
            "colors": {"fill": "#FFF8E1", "border": "#F9A825", "label": "#5F4300"},
            "label": {"valign": "bottom", "halign": "center", "position": "outside"},
        }
    }

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "name": {"type": "string", "minLength": 1},
        "domain": {"type": "string"},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = {
        "name": {"validation": "jsonschema", "schema": {"type": "string", "minLength": 1}},
        "domain": {"validation": "jsonschema", "schema": {"type": "string"}},
    }
    CREATE_REQUIRED: ClassVar[list[str]] = ["name"]

    name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    domain = models.CharField(max_length=255, blank=True, default="", db_index=True)

    class Meta(BaseModel.Meta):
        db_table = "identity_core__organization"

    def get_name(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.get_name()
