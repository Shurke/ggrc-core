# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Custom Attribute Definition hooks"""

from ggrc import models, views
from ggrc.services import signals
from ggrc.models import custom_attribute_definition as cad


def init_hook():
  """Initialize CAD hooks"""
  # pylint: disable=unused-variable
  # pylint: disable=too-many-arguments
  @signals.Restful.model_put_after_commit.connect_via(
      models.all_models.CustomAttributeDefinition)
  @signals.Restful.model_posted_after_commit.connect_via(
      models.all_models.CustomAttributeDefinition)
  @signals.Restful.model_put_after_commit.connect_via(
      models.all_models.ExternalCustomAttributeDefinition)
  @signals.Restful.model_posted_after_commit.connect_via(
      models.all_models.ExternalCustomAttributeDefinition)
  def handle_cad_creating_editing(sender, obj=None, src=None, service=None,
                                  event=None, initial_state=None):
    """Make reindex without creating revisions for related objects after
      creating/editing CAD from admin panel

    Args:
      sender: A class of Resource handling the POST request.
      obj: A list of model instances created from the POSTed JSON.
      src: A list of original POSTed JSON dictionaries.
      service: The instance of Resource handling the PUT request.
      event: Instance of an Event (if change took place) or None otherwise
      initial_state: A named tuple of initial values of an object before
        applying any change.
    """
    # pylint: disable=unused-argument
    model_name = cad.get_inflector_model_name_dict()[obj.definition_type]
    views.start_update_cad_related_objs(event.id, model_name)

  @signals.Restful.model_deleted_after_commit.connect_via(
      models.all_models.CustomAttributeDefinition)
  def handle_cad_deleting(sender, obj=None, service=None, event=None):
    """Make reindex after deleting CAD from admin panel

    Args:
      sender: A class of Resource handling the POST request.
      obj: A list of model instances created from the POSTed JSON.
      service: The instance of Resource handling the PUT request.
      event: Instance of an Event (if change took place) or None otherwise
    """
    # pylint: disable=unused-argument
    model_name = cad.get_inflector_model_name_dict()[obj.definition_type]
    views.start_update_cad_related_objs(
        event.id, model_name, need_revisions=True
    )
