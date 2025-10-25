"""seed_default_vocab_policies

Revision ID: fcd5edb73bc7
Revises: 29d0cfa904f6
Create Date: 2025-10-24 17:57:39.472219

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fcd5edb73bc7'
down_revision: Union[str, None] = '29d0cfa904f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Seed default vocab policies based on ONTOLOGY.md
    conn = op.get_bind()

    default_policies = [
        # Strict lookup-only (system vocab)
        ('crm.stage', None, 'lookup_only', False, 'Controls reporting, funnel math'),
        ('res.country', None, 'lookup_only', False, 'Pre-seeded reference data'),
        ('res.country.state', None, 'lookup_only', False, 'Pre-seeded reference data'),
        ('res.users', None, 'lookup_only', False, 'Security boundary'),
        ('res.company', None, 'lookup_only', False, 'System config'),

        # Suggest-only (requires approval)
        ('crm.lost.reason', None, 'suggest_only', True, 'Bespoke wording requires approval'),
        ('utm.source', None, 'suggest_only', False, 'Review before creating; flip to lookup_only post-stabilization'),
        ('utm.medium', None, 'suggest_only', False, 'Review before creating; flip to lookup_only post-stabilization'),
        ('utm.campaign', None, 'suggest_only', False, 'Review before creating; flip to lookup_only post-stabilization'),

        # Create-if-missing (user vocab)
        ('crm.tag', None, 'create_if_missing', False, 'Low risk, high variability'),
        ('res.partner.category', None, 'create_if_missing', False, 'Low risk, m2m friendly'),
    ]

    # Insert policies
    for model, company_id, policy, requires_approval, description in default_policies:
        conn.execute(sa.text("""
            INSERT INTO vocab_policies (model, company_id, default_policy, requires_approval, created_at, updated_at, company_overrides)
            VALUES (:model, :company_id, :policy, :requires_approval, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, '{}')
            ON CONFLICT (model, company_id) DO UPDATE
            SET default_policy = EXCLUDED.default_policy,
                requires_approval = EXCLUDED.requires_approval,
                updated_at = CURRENT_TIMESTAMP
        """), {
            'model': model,
            'company_id': company_id,
            'policy': policy,
            'requires_approval': requires_approval
        })

    # Seed common aliases
    common_aliases = [
        # Country aliases
        ('res.country', 'name', 'US', 'United States', None),
        ('res.country', 'name', 'USA', 'United States', None),
        ('res.country', 'name', 'UK', 'United Kingdom', None),
        ('res.country', 'name', 'GB', 'United Kingdom', None),

        # UTM source aliases
        ('utm.source', 'name', 'g ads', 'google', None),
        ('utm.source', 'name', 'gooogle', 'google', None),
        ('utm.source', 'name', 'fb', 'facebook', None),
        ('utm.source', 'name', 'li', 'linkedin', None),
    ]

    # Insert aliases
    for model, field, alias, canonical, company_id in common_aliases:
        conn.execute(sa.text("""
            INSERT INTO vocab_aliases (model, field, alias, canonical_value, company_id, created_at)
            VALUES (:model, :field, :alias, :canonical, :company_id, CURRENT_TIMESTAMP)
            ON CONFLICT (model, field, alias, company_id) DO UPDATE
            SET canonical_value = EXCLUDED.canonical_value
        """), {
            'model': model,
            'field': field,
            'alias': alias,
            'canonical': canonical,
            'company_id': company_id
        })


def downgrade() -> None:
    # Remove seeded policies and aliases
    conn = op.get_bind()

    # Delete default policies
    conn.execute(sa.text("""
        DELETE FROM vocab_policies
        WHERE model IN (
            'crm.stage', 'res.country', 'res.country.state', 'res.users', 'res.company',
            'crm.lost.reason', 'utm.source', 'utm.medium', 'utm.campaign',
            'crm.tag', 'res.partner.category'
        ) AND company_id IS NULL
    """))

    # Delete common aliases
    conn.execute(sa.text("""
        DELETE FROM vocab_aliases
        WHERE model IN ('res.country', 'utm.source')
          AND company_id IS NULL
    """))
