"""Phone number — one line anywhere in the world: a country code and a national number."""

from typing import Any, ClassVar

from django.core.exceptions import ValidationError
from django.db import models

from tap_grid.models import BaseModel
from tap_plugin.identity_core.contact import MAX_PHONE_DIGITS, country_code_length

_DIGITS = {"type": "string", "pattern": "^[0-9]+$"}


class PhoneNumber(BaseModel):
    """One phone number, shared by every record that names it.

    The country code and the national number are separate fields, so a search can use either or
    put them together. With a country code a number identifies one line anywhere, which is what
    makes it shareable. A number stated without one does not: "555-0100" means something only
    inside a country nobody named. Such a number is never written here. It stays on the record
    that stated it, with its country code null (never sent), until a country code is known.

    Identity is ``(country_code, national_number, extension)``. ``extension`` is the empty string
    when there is none, which is a value and not a gap, so a desk line and its switchboard are two
    nodes and a number with no extension is still found again.

    The text as typed, and how the country code came to be known, are facts about one statement
    of the number. They belong on the record that made the statement, not on this shared node.

    Spec: specs/spec-identity-core-v0.md (req-identity-core-phone-number).
    """

    ENTITY_TYPE: ClassVar[str] = "identity_core__phone_number"
    ENTITY_NAME: ClassVar[str] = "Phone Number"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "One phone number with its country code and national number held apart, shared by every "
        "record that names it. A number with no country code is never written here."
    )
    ENTITY_ICON: ClassVar[str] = "phone-number"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = {}
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("country_code", "national_number", "extension")

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "country_code": {**_DIGITS, "minLength": 1, "maxLength": 3},
        "national_number": {**_DIGITS, "minLength": 1, "maxLength": MAX_PHONE_DIGITS},
        "extension": {"type": "string", "pattern": "^[0-9]*$", "maxLength": 16},
    }
    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = {
        name: {"validation": "jsonschema", "schema": schema}
        for name, schema in FIELD_CRUD_SCHEMA.items()
    }
    CREATE_REQUIRED: ClassVar[list[str]] = ["country_code", "national_number"]

    country_code = models.CharField(max_length=3, db_index=True, help_text="The country calling code, digits only, without the plus sign.")
    national_number = models.CharField(max_length=MAX_PHONE_DIGITS, db_index=True, help_text="The number within the country, digits only.")
    extension = models.CharField(max_length=16, blank=True, default="", help_text="The extension, digits only; empty when the number has none.")

    class Meta(BaseModel.Meta):
        db_table = "identity_core__phone_number"

    def validate(self) -> None:
        """The country code is one, by its length, and the whole number fits what E.164 allows."""
        code, number = self.country_code or "", self.national_number or ""
        if not (code.isdigit() and number.isdigit()):
            return  # the field schemas report it
        if code.startswith("0") or country_code_length(code + number) != len(code):
            raise ValidationError({"country_code": [f"{code!r} is not a country calling code: the leading digits of a number fix how long its code is."]})
        if len(code) + len(number) > MAX_PHONE_DIGITS:
            raise ValidationError({"national_number": [f"a number is at most {MAX_PHONE_DIGITS} digits, country code included."]})

    def get_name(self) -> str:
        shown = f"+{self.country_code} {self.national_number}"
        return f"{shown} x{self.extension}" if self.extension else shown

    def __str__(self) -> str:
        return self.get_name()
