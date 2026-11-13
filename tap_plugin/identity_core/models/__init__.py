"""Identity Core plugin models package."""

from tap_plugin.identity_core.models.email_address import EmailAddress
from tap_plugin.identity_core.models.human import Human
from tap_plugin.identity_core.models.mailbox import Mailbox
from tap_plugin.identity_core.models.oidc_issuer import OidcIssuer
from tap_plugin.identity_core.models.organization import Organization
from tap_plugin.identity_core.models.phone_number import PhoneNumber
from tap_plugin.identity_core.models.team import Team

__all__ = [
    "EmailAddress",
    "Human",
    "Mailbox",
    "OidcIssuer",
    "Organization",
    "PhoneNumber",
    "Team",
]
