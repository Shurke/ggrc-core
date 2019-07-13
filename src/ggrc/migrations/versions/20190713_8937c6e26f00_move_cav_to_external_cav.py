# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
move CAVs to external CAVs
Create Date: 2019-07-13 14:59:08.773327
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

from alembic import op

from ggrc.migrations.utils import external_cavs


# revision identifiers, used by Alembic.
revision = '8937c6e26f00'
down_revision = 'c4f1d9267f88'


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  connection = op.get_bind()
  external_cavs.migrate_to_external_cavs(connection, 'control')
  external_cavs.migrate_to_external_cavs(connection, 'risk')


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
  raise NotImplementedError("Downgrade is not supported")
