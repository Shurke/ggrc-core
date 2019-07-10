# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Module with common validators for GGRC."""

from werkzeug import exceptions

from ggrc import db
from ggrc.models import mixins


def modified_only(func):
  """Decorator for "before_update" handler that checks if object is changed."""
  def wrapper(mapper, connection, target):
    """Skip listener if target object is not modified.

    Args:
      mapper: the Mapper which is the target of this event
      connection: the Connection being used to emit UPDATE statements
      target: the mapped instance being persisted
    """
    if db.session.is_modified(target):
      return func(mapper, connection, target)

    return None

  return wrapper


# pylint: disable=unused-argument
def validate_object_type_ggrcq(mapper, content, target):
  """Validate object_type actions for GGRCQ."""
  from ggrc import login as login_module
  from ggrc.models import get_model
  from ggrc.models.mixins import synchronizable

  model = get_model(target.object_type)
  user = login_module.get_current_user(False)

  if not user or user.is_anonymous():
    return

  should_prevent = all([
      issubclass(model, synchronizable.Synchronizable),
      not login_module.is_external_app_user()
  ])

  if should_prevent:
    raise exceptions.MethodNotAllowed()


def validate_definition_type_cad(mapper, content, target):
  """Validate actions for CAD object with definition_type."""
  from ggrc import login as login_module
  from ggrc.models import get_model
  from ggrc.models.mixins import synchronizable
  del mapper, content

  model = get_model(target.definition_type)
  user = login_module.get_current_user(False)

  if not user or user.is_anonymous():
    return

  should_prevent = (
      issubclass(model, mixins.ExternalCustomAttributable) or
      issubclass(model, synchronizable.Synchronizable)
  )

  if should_prevent:
    raise exceptions.MethodNotAllowed()


def validate_definition_type_ecad(mapper, content, target):
  """Validate actions for eCAD object with definition_type."""
  from ggrc import login as login_module
  from ggrc.models import get_model
  del mapper, content

  model = get_model(target.definition_type)
  user = login_module.get_current_user(False)

  if not user or user.is_anonymous():
    return

  should_prevent = (
      not login_module.is_external_app_user() or
      issubclass(model, mixins.CustomAttributable)
  )

  if should_prevent:
    raise exceptions.MethodNotAllowed()


def validate_name_correctness(name):
  """Validate name does not contains invalid values"""
  name_to_validate = name.strip().lower()

  names_includes = ["*"]
  for invalid in names_includes:
    if invalid in name_to_validate:
      raise ValueError(u"Name contains unsupported symbol '{}'"
                       .format(invalid))

  names_starts_with = ["map:", "unmap:"]
  for invalid in names_starts_with:
    if name_to_validate.startswith(invalid):
      raise ValueError(u"Name should not start with '{}'".format(invalid))

  invalid_names = ["delete"]
  for invalid in invalid_names:
    if name_to_validate == invalid:
      raise ValueError(u"'{}' is reserved word and should not be used as "
                       u"an name".format(invalid))
