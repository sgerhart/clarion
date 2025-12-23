"""
Clarion Identity Module

Identity resolution and enrichment for endpoints.

Key components:
- IdentityResolver: Map endpoints to users and AD groups
- IdentityContext: Complete identity information for an endpoint
"""

from clarion.identity.resolver import (
    IdentityResolver,
    IdentityContext,
    enrich_sketches,
)

__all__ = [
    "IdentityResolver",
    "IdentityContext",
    "enrich_sketches",
]

