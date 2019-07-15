# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""External service models API resource."""

from werkzeug.exceptions import Forbidden, MethodNotAllowed

from ggrc import db, utils
from ggrc.login import get_current_user, is_external_app_user
from ggrc.services import common


class ExternalResource(common.Resource):
  """Resource handler for external service models."""

  def post(self, *args, **kwargs):
    """POST operation handler."""
    del args, kwargs
    raise MethodNotAllowed()

  def collection_post(self):
    """Prevent creation of object for internal users."""
    if not is_external_app_user():
      raise Forbidden()

    return super(ExternalResource, self).collection_post()

  @utils.validate_mimetype("application/json")
  def put(self, *args, **kwargs):   # pylint:disable=arguments-differ
    """Prevent update of object for internal users."""
    if not is_external_app_user():
      raise Forbidden()

    return super(ExternalResource, self).put(*args, **kwargs)

  def patch(self, *args, **kwargs):   # pylint:disable=arguments-differ
    """PATCH operation handler."""
    del args, kwargs
    raise MethodNotAllowed()

  def delete(self, *args, **kwargs):  # pylint:disable=arguments-differ
    """Prevent update of object for internal users."""
    if not is_external_app_user():
      raise Forbidden()

    return super(ExternalResource, self).delete(*args, **kwargs)

  def validate_headers_for_put_or_delete(self, obj):
    """Skip ETAG checking for external resources."""
    return None

  def add_modified_object_to_session(self, obj):
    """Update modification metadata and add object to session."""
    obj.modified_by = get_current_user()

    db.session.add(obj)


class ExternalCADResource(ExternalResource):
  """Resource handler for External Custom Attribute Definitions"""

  def build_collection_representation(self, objs, extras=None):
    """Mask external Custom attribute definitions for JSON response"""
    resp = super(ExternalCADResource, self).build_collection_representation(
        objs, extras
    )
    if "external_custom_attribute_definitions_collection" in resp:
      col = resp.pop("external_custom_attribute_definitions_collection", {})
      if "external_custom_attribute_definitions" in col:
        col["custom_attribute_definitions"] = col.pop(
            "external_custom_attribute_definitions"
        )
      resp["custom_attribute_definitions_collection"] = col
    return resp

  def object_for_json(self, obj, model_name=None, properties_to_include=None):
    """Mask external Custom attribute definitions for JSON response"""
    resp = super(ExternalCADResource, self).object_for_json(
        obj, model_name, properties_to_include
    )
    if "external_custom_attribute_definition" in resp:
      resp["custom_attribute_definition"] = resp.pop(
          "external_custom_attribute_definition",
          {}
      )
    return resp

  def delete(self, *args, **kwargs):
    """DELETE operation handler."""
    del args, kwargs
    raise MethodNotAllowed()
