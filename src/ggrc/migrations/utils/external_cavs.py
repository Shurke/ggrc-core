# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Module contains utils for external CAVs."""

import sqlalchemy as sa

CAVS_BY_OBJECT_TYPE_SQL = u'''
  SELECT
    custom_attribute_id,
    attributable_type,
    attributable_id,
    attribute_value,
    context_id,
    updated_at,
    modified_by_id,
    created_at
  FROM
    custom_attribute_values
  WHERE
    attributable_type = :object_type
'''

PROPAGATE_EXTERNAL_CAVS_BY_CAVS_SQL = u'''
  INSERT INTO external_custom_attribute_values (
    custom_attribute_id,
    attributable_type,
    attributable_id,
    attribute_value,
    context_id,
    updated_at,
    modified_by_id,
    created_at
  ) VALUES (
    :custom_attribute_id,
    :attributable_type,
    :attributable_id,
    :attribute_value,
    :context_id,
    :updated_at,
    :modified_by_id,
    :created_at
  )
'''


def _get_cavs(connection, object_type):
  """Returns CAVs by object type.
  Args:
    connection: sqlalchemy.engine.Connection object.
  Returns:
    cavs: List of CAVs objects.
  """
  cavs = connection.execute(
      sa.text(CAVS_BY_OBJECT_TYPE_SQL),
      object_type=object_type
  ).fetchall()

  return cavs


def _propagate_external_cavs(connection, cavs):
  """Propagates external CAVs by CAVs.
  Args:
    connection: sqlalchemy.engine.Connection object.
    cavs: List of CAVs objects.
  """
  for cav in cavs:
    connection.execute(
        sa.text(PROPAGATE_EXTERNAL_CAVS_BY_CAVS_SQL),
        cav
    )


def migrate_to_external_cavs(connection, obj_type):
  """Migrates CAVs to external CAVs.

  Args:
    connection: An instance of SQLAlchemy connection.
    obj_type: String representation of object type.
  """
  cavs = _get_cavs(connection, obj_type)
  _propagate_external_cavs(connection, cavs)
