"""Human — one real person, the node every system's account for that person resolves to."""

from typing import Any, ClassVar

from django.db import models

from tap_grid.event_time import NO_EVENT_TIME
from tap_grid.models import BaseModel


class Human(BaseModel):
    """One real person, independent of any system they have an account in.

    An Okta user, a Duo user, a Teleport user and a GitLab user are four vendor records; when
    they are the same person, each draws ``HELD_BY_HUMAN__identity_core`` to one ``human``. That
    join is what an access review asks ("everything this person can reach"), and no vendor
    plugin can own it without depending on the others.

    Identity is ``handle``: an identifier the operator assigns and keeps stable, such as an HR
    employee number or the organization's canonical username. Not ``name``, which changes, and
    not an email address, which is an account attribute that is reassigned and aliased. The
    type carries no free-form ``configuration`` blob: there is no source payload to preserve,
    and a person record is exactly where one would collect personal data nobody chose to store.

    Spec: specs/spec-identity-core-v0.md (req-identity-core-human).
    """

    ENTITY_TYPE: ClassVar[str] = "identity_core__human"
    ENTITY_NAME: ClassVar[str] = "Human"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "One real person, independent of any system. Each system's account for that person "
        "points at it with HELD_BY_HUMAN, so one person's access can be read across systems."
    )
    ENTITY_ICON: ClassVar[str] = "human"
    # No default dimension: `identity.protocol` does not apply, and a kind-of-party value would
    # only restate the entity type.
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = {}
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("handle",)
    # No event time: an operator-assigned person record; it stores no time the person or any source states.
    EVENT_TIME = NO_EVENT_TIME
    DEFAULT_DISPLAY: ClassVar[dict[str, Any]] = {
        "tap_viz": {
            "shape": "ellipse",
            "colors": {"fill": "#FFF8E1", "border": "#F9A825", "label": "#5F4300"},
            "label": {"valign": "bottom", "halign": "center", "position": "outside"},
        }
    }

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "handle": {"type": "string", "minLength": 1},
        "name": {"type": "string"},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = {
        "handle": {"validation": "jsonschema", "schema": {"type": "string", "minLength": 1}},
        "name": {"validation": "jsonschema", "schema": {"type": "string"}},
    }
    CREATE_REQUIRED: ClassVar[list[str]] = ["handle"]

    handle = models.CharField(max_length=255, blank=True, default="", db_index=True)
    name = models.CharField(max_length=255, blank=True, default="")

    class Meta(BaseModel.Meta):
        db_table = "identity_core__human"

    def get_name(self) -> str:
        return self.name or self.handle

    def __str__(self) -> str:
        return self.get_name()
