# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Module contains utils for external CADs."""

import sqlalchemy as sa


CADS_BY_OBJECT_TYPE_SQL = u'''
  SELECT
    id,
    definition_type,
    attribute_type,
    multi_choice_options,
    mandatory,
    helptext,
    placeholder,
    context_id,
    updated_at,
    modified_by_id,
    created_at,
    title
  FROM
    custom_attribute_definitions
  WHERE
    definition_type = :object_type
'''

PROPAGATE_EXTERNAL_CADS_BY_CADS_SQL = u'''
  INSERT INTO external_custom_attribute_definitions (
    id,
    definition_type,
    attribute_type,
    multi_choice_options,
    mandatory,
    helptext,
    placeholder,
    context_id,
    updated_at,
    modified_by_id,
    created_at,
    title
  ) VALUES (
    :id,
    :definition_type,
    :attribute_type,
    :multi_choice_options,
    :mandatory,
    :helptext,
    :placeholder,
    :context_id,
    :updated_at,
    :modified_by_id,
    :created_at,
    :title
  )
'''


def _get_cads(connection, object_type):
  """Returns CADs by object type.

  Args:
    connection: sqlalchemy.engine.Connection object.
    object_type: String representation of object type.

  Returns:
    cads: List of CADs objects.
  """
  cads = connection.execute(
      sa.text(CADS_BY_OBJECT_TYPE_SQL),
      object_type=object_type
  ).fetchall()

  return cads


def _propagate_external_cads(connection, cads):
  """Propagates external CADs by CADs.

  Args:
    connection: sqlalchemy.engine.Connection object.
    cads: List of CADs objects.
  """
  for cad in cads:
    connection.execute(
        sa.text(PROPAGATE_EXTERNAL_CADS_BY_CADS_SQL),
        definition_type=cad.definition_type,
        attribute_type=cad.attribute_type,
        multi_choice_options=cad.multi_choice_options,
        mandatory=cad.mandatory,
        helptext=cad.helptext,
        placeholder=cad.placeholder,
        context_id=cad.context_id,
        updated_at=cad.updated_at,
        modified_by_id=cad.modified_by_id,
        created_at=cad.created_at,
        title=cad.title,
        id=cad.id
    )


def migrate_to_external_cads(connection, obj_type):
  """Migrates CADs to external CADs for object type.

  Args:
    connection: An instance of SQLAlchemy connection.
    obj_type: String representation of object type.
  """
  cads = _get_cads(connection, obj_type)
  _propagate_external_cads(connection, cads)
