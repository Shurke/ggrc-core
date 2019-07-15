# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Add external CAs tables

Create Date: 2019-06-26 14:25:27.324169
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '06186e8d6295'
down_revision = 'e1988524ed3e'


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  op.create_table(
      'external_custom_attribute_definitions',
      sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
      sa.Column('external_id', sa.Integer(), nullable=True),
      sa.Column('definition_type', sa.String(length=250), nullable=False),
      sa.Column('attribute_type', sa.String(length=250), nullable=False),
      sa.Column('multi_choice_options', sa.String(length=250), nullable=True),
      sa.Column('mandatory', sa.Boolean(), nullable=False),
      sa.Column('helptext', sa.String(length=250), nullable=True),
      sa.Column('placeholder', sa.String(length=250), nullable=True),
      sa.Column('context_id', sa.Integer(), nullable=True),
      sa.Column('updated_at', sa.DateTime(), nullable=False),
      sa.Column('modified_by_id', sa.Integer(), nullable=True),
      sa.Column('created_at', sa.DateTime(), nullable=False),
      sa.Column('title', sa.String(length=250), nullable=False),
      sa.PrimaryKeyConstraint('id'),
      sa.UniqueConstraint('definition_type',
                          'title',
                          name='uq_custom_attribute'),
      sa.UniqueConstraint('external_id'),
  )
  op.create_index(
      'ix_custom_attributes_title',
      'external_custom_attribute_definitions',
      ['title'],
      unique=False
  )

  op.alter_column(
      'custom_attribute_definitions', 'mandatory',
      existing_type=sa.Boolean(),
      nullable=False
  )

  op.create_table(
      'external_custom_attribute_values',
      sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
      sa.Column('external_id', sa.Integer(), nullable=True),
      sa.Column('custom_attribute_id', sa.Integer(), nullable=False),
      sa.Column('attributable_type', sa.String(length=250), nullable=True),
      sa.Column('attributable_id', sa.Integer(), nullable=True),
      sa.Column('attribute_value', sa.String(length=250), nullable=False),
      sa.Column('context_id', sa.Integer(), nullable=True),
      sa.Column('updated_at', sa.DateTime(), nullable=False),
      sa.Column('modified_by_id', sa.Integer(), nullable=True),
      sa.Column('created_at', sa.DateTime(), nullable=False),
      sa.ForeignKeyConstraint(['custom_attribute_id'],
                              ['external_custom_attribute_definitions.id'],
                              ondelete='CASCADE'),
      sa.PrimaryKeyConstraint('id'),
      sa.UniqueConstraint('attributable_id', 'custom_attribute_id'),
      sa.UniqueConstraint('external_id')
  )
  op.create_index(
      'ix_custom_attributes_attributable',
      'external_custom_attribute_values',
      ['attributable_id', 'attributable_type'],
      unique=False
  )


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
  raise NotImplementedError("Downgrade is not supported")
