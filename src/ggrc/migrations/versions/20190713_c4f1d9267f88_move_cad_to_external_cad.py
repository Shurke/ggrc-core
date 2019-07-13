# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
move cad to external cad

Create Date: 2019-07-13 14:59:08.773327
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

from alembic import op

from ggrc.migrations.utils import external_cads


# revision identifiers, used by Alembic.
revision = 'c4f1d9267f88'
down_revision = '06186e8d6295'


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  connection = op.get_bind()
  external_cads.migrate_to_external_cads(connection, 'control')
  external_cads.migrate_to_external_cads(connection, 'risk')


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
  raise NotImplementedError("Downgrade is not supported")
