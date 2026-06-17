"""Aegoria error hierarchy."""

from __future__ import annotations


class AegoriaError(Exception):
    """Base for all Aegoria errors."""


class ConfigError(AegoriaError):
    """Invalid or missing configuration."""


class ProviderNotFound(AegoriaError):
    """A requested adapter/service provider is not registered."""


class ProtocolViolation(AegoriaError):
    """A registered provider does not satisfy its declared protocol."""


class DomainPackError(AegoriaError):
    """A domain-pack manifest is invalid or incompatible with the core."""


class AccessDenied(AegoriaError):
    """The governance layer refused an access request."""


class PrivacyBudgetExceeded(AegoriaError):
    """A differential-privacy query would exceed the remaining epsilon budget."""


class QualityGateFailed(AegoriaError):
    """Data failed a domain-pack quality rule at an enforced gate."""
