"""Baseline revision.

No domain tables yet. Stamping this revision records that the database has
been migrated, so later milestones add tables on top of a known version.
"""

from collections.abc import Sequence

revision: str = "0001_baseline"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Record the baseline. Domain tables start in later milestones."""


def downgrade() -> None:
    """Return to an unstamped database. There is no schema to undo."""
