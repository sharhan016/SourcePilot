"""Replace the original demo identity with the UAE demo context.

Revision ID: 0002_uae_demo_context
Revises: 0001_initial
"""

from collections.abc import Mapping
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0002_uae_demo_context"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

OLD_COMPANY = "Acme Operations"
OLD_LOCATION = "Bengaluru, India"
NEW_COMPANY = "IT Essentials (ITE)"
NEW_LOCATION = "Sharjah, United Arab Emirates"

procurement_requests = sa.table(
    "procurement_requests",
    sa.column("id", sa.String()),
    sa.column("company_name", sa.String()),
    sa.column("company_location", sa.String()),
    sa.column("normalized_requirements", sa.JSON()),
)


def _requirements(value: Mapping[str, Any] | None, *, uae: bool) -> dict[str, Any]:
    updated = dict(value or {})
    keys = ("currency", "delivery_location", "procurement_region", "sourcing_regions")
    if uae:
        updated.update(
            {
                "currency": "AED",
                "delivery_location": NEW_LOCATION,
                "procurement_region": "UAE",
                "sourcing_regions": ["United Arab Emirates", "GCC"],
            }
        )
    else:
        for key in keys:
            updated.pop(key, None)
    return updated


def _migrate_company(
    source_company: str, source_location: str, target_company: str, target_location: str, *, uae: bool
) -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(procurement_requests.c.id, procurement_requests.c.normalized_requirements).where(
            procurement_requests.c.company_name == source_company,
            procurement_requests.c.company_location == source_location,
        )
    ).mappings()
    for row in rows:
        connection.execute(
            sa.update(procurement_requests)
            .where(procurement_requests.c.id == row["id"])
            .values(
                company_name=target_company,
                company_location=target_location,
                normalized_requirements=_requirements(
                    row["normalized_requirements"], uae=uae
                ),
            )
        )


def upgrade() -> None:
    _migrate_company(OLD_COMPANY, OLD_LOCATION, NEW_COMPANY, NEW_LOCATION, uae=True)


def downgrade() -> None:
    _migrate_company(NEW_COMPANY, NEW_LOCATION, OLD_COMPANY, OLD_LOCATION, uae=False)
