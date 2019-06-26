# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Module containing custom attributable mixin."""

import collections
from logging import getLogger

import sqlalchemy
from sqlalchemy import and_
from sqlalchemy import or_
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import foreign
from sqlalchemy.orm import relationship
from werkzeug.exceptions import BadRequest

from ggrc import db
from ggrc import utils
from ggrc.models import reflection
from ggrc.models.mixins.customattributable import CustomAttributableBase

# pylint: disable=invalid-name
logger = getLogger(__name__)


class ExternalCustomAttributable(CustomAttributableBase):
  """External Custom Attributable mixin."""

  @declared_attr
  def custom_attribute_definitions(cls):  # pylint: disable=no-self-argument
    """Load custom attribute definitions"""
    from ggrc.models.external_custom_attribute_definition\
        import ExternalCustomAttributeDefinition

    def join_function():
      """Object and CAD join function."""
      definition_type = foreign(ExternalCustomAttributeDefinition.definition_type)
      return and_(definition_type == cls._inflector.table_singular,
                  or_(cls.id != ExternalCustomAttributeDefinition.id,  #TODO FIND SOLUTION!!!!!!!
                      cls.id == ExternalCustomAttributeDefinition.id))

    return relationship(
        "ExternalCustomAttributeDefinition",
        primaryjoin=join_function,
        backref='{0}_custom_attributable_definition'.format(cls.__name__),
        order_by=ExternalCustomAttributeDefinition.id.asc(),
        viewonly=True,
    )

  @declared_attr
  def _custom_attribute_values(cls):  # pylint: disable=no-self-argument
    """Load custom attribute values"""
    current_type = cls.__name__

    joinstr = (
        "and_("
        "foreign(remote(ExternalCustomAttributeValue.attributable_id)) == {type}.id,"
        "ExternalCustomAttributeValue.attributable_type == '{type}'"
        ")"
        .format(type=current_type)
    )

    # Since we have some kind of generic relationship here, it is needed
    # to provide custom joinstr for backref. If default, all models having
    # this mixin will be queried, which in turn produce large number of
    # queries returning nothing and one query returning object.
    backref_joinstr = (
        "remote({type}.id) == foreign(ExternalCustomAttributeValue.attributable_id)"
        .format(type=current_type)
    )

    return db.relationship(
        "ExternalCustomAttributeValue",
        primaryjoin=joinstr,
        backref=orm.backref(
            "{}_custom_attributable".format(current_type),
            primaryjoin=backref_joinstr,
        ),
        cascade="all, delete-orphan"
    )

  @classmethod
  def indexed_query(cls):
    return super(ExternalCustomAttributable, cls).indexed_query().options(
        orm.Load(cls).subqueryload(
            "custom_attribute_values"
        ).joinedload(
            "custom_attribute"
        ).load_only(
            "id",
            "title",
            "attribute_type",
        ),
        orm.Load(cls).subqueryload(
            "custom_attribute_definitions"
        ).load_only(
            "id",
            "title",
            "attribute_type",
        ),
        orm.Load(cls).subqueryload("custom_attribute_values").load_only(
            "id",
            "attribute_value",
            "custom_attribute_id",
        ),
    )

  def _add_ca_value_dicts(self, values):
    """Add CA dict representations to _custom_attributes_values property.

    This adds or updates the _custom_attribute_values with the values in the
    custom attribute values serialized dictionary.

    Args:
      values: List of dictionaries that represent custom attribute values.
    """
    from ggrc.utils import referenced_objects
    from ggrc.models.external_custom_attribute_value import ExternalCustomAttributeValue

    for value in values:
      # TODO: decompose to smaller methods
      # TODO: remove complicated nested conditions, better to use
      # instant exception raising
      if not value.get("attribute_object_id"):
        # value.get("attribute_object", {}).get("id") won't help because
        # value["attribute_object"] can be None
        value["attribute_object_id"] = (value["attribute_object"].get("id") if
                                        value.get("attribute_object") else
                                        None)

      attr = self._values_map.get(value.get("custom_attribute_id"))
      if attr:
        attr.attributable = self
        attr.attribute_value = value.get("attribute_value")
        attr.attribute_object_id = value.get("attribute_object_id")
      elif "custom_attribute_id" in value:
        # this is automatically appended to self._custom_attribute_values
        # on attributable=self
        custom_attribute_id = value.get("custom_attribute_id")
        custom_attribute = referenced_objects.get(
            "ExternalCustomAttributeDefinition", custom_attribute_id
        )
        attribute_object = value.get("attribute_object")
        _id = value.get("id")
        if attribute_object is None:   # TODO remove attribute object !!!!
          ExternalCustomAttributeValue(
              id=_id,
              attributable=self,
              custom_attribute=custom_attribute,
              custom_attribute_id=custom_attribute_id,
              attribute_value=value.get("attribute_value"),
          )
        elif isinstance(attribute_object, dict):
          attribute_object_type = attribute_object.get("type")
          attribute_object_id = attribute_object.get("id")

          attribute_object = referenced_objects.get(
              attribute_object_type, attribute_object_id
          )

          cav = ExternalCustomAttributeValue(
              attributable=self,
              custom_attribute=custom_attribute,
              custom_attribute_id=custom_attribute_id,
              attribute_value=value.get("attribute_value"),
          )
          cav.attribute_object = attribute_object
        else:
          raise BadRequest("Bad custom attribute value inserted")
      elif "href" in value:
        # Ignore setting of custom attribute stubs. Getting here means that the
        # front-end is not using the API correctly and needs to be updated.
        logger.info("Ignoring post/put of custom attribute stubs.")
      else:
        raise BadRequest("Bad custom attribute value inserted")

  def insert_definition(self, definition):
    """Insert a new custom attribute definition into database

    Args:
      definition: dictionary with field_name: value
    """
    from ggrc.models.external_custom_attribute_definition \
        import ExternalCustomAttributeDefinition
    field_names = reflection.AttributeInfo.gather_create_attrs(
        ExternalCustomAttributeDefinition)

    data = {fname: definition.get(fname) for fname in field_names}
    data.pop("definition_type", None)
    data.pop("definition_id", None)
    data["definition"] = self
    cad = ExternalCustomAttributeDefinition(**data)
    db.session.add(cad)

  def process_definitions(self, definitions):
    """
    Process custom attribute definitions

    If present, delete all related custom attribute definition and insert new
    custom attribute definitions in the order provided.

    Args:
      definitions: Ordered list of (dict) custom attribute definitions
    """
    from ggrc.models.external_custom_attribute_definition \
        import ExternalCustomAttributeDefinition as CADef

    if not hasattr(self, "PER_OBJECT_CUSTOM_ATTRIBUTABLE"):
      return

    if self.id is not None:
      db.session.query(CADef).filter(
          CADef.definition_type == self._inflector.table_singular
      ).delete()
      db.session.flush()
      db.session.expire_all()

    for definition in definitions:
      if "_pending_delete" in definition and definition["_pending_delete"]:
        continue

      definition['context'] = getattr(self, "context", None)
      self.insert_definition(definition)

  def _remove_existing_items(self, attr_values):
    """Remove existing CAV and corresponding full text records."""
    from ggrc.fulltext.mysql import MysqlRecordProperty
    from ggrc.models.external_custom_attribute_value \
        import ExternalCustomAttributeValue
    if not attr_values:
      return
    # 2) Delete all fulltext_record_properties for the list of values
    ftrp_properties = []
    for val in attr_values:
      ftrp_properties.append(val.custom_attribute.title)
      if val.custom_attribute.attribute_type == "Map:Person":
        ftrp_properties.append(val.custom_attribute.title + ".name")
        ftrp_properties.append(val.custom_attribute.title + ".email")
    db.session.query(MysqlRecordProperty)\
        .filter(
            and_(
                MysqlRecordProperty.key == self.id,
                MysqlRecordProperty.type == self.__class__.__name__,
                MysqlRecordProperty.property.in_(ftrp_properties)))\
        .delete(synchronize_session='fetch')

    # 3) Delete the list of custom attribute values
    attr_value_ids = [value.id for value in attr_values]
    db.session.query(ExternalCustomAttributeValue)\
        .filter(ExternalCustomAttributeValue.id.in_(attr_value_ids))\
        .delete(synchronize_session='fetch')
    db.session.commit()

  def custom_attributes(self, src):
    """Legacy setter for custom attribute values and definitions.

    This code should only be used for custom attribute definitions until
    setter for that is updated.
    """
    # pylint: disable=too-many-locals
    from ggrc.models.external_custom_attribute_value \
        import ExternalCustomAttributeValue

    ca_values = src.get("custom_attribute_values")
    if ca_values and "attribute_value" in ca_values[0]:
      # This indicates that the new CA API is being used and the legacy API
      # should be ignored. If we need to use the legacy API the
      # custom_attribute_values property should contain stubs instead of entire
      # objects.
      return

    definitions = src.get("custom_attribute_definitions")
    if definitions is not None:
      self.process_definitions(definitions)

    attributes = src.get("custom_attributes")
    if not attributes:
      return

    old_values = collections.defaultdict(list)

    # attributes looks like this:
    #    [ {<id of attribute definition> : attribute value, ... }, ... ]

    # 1) Get all custom attribute values for the CustomAttributable instance
    attr_values = db.session.query(ExternalCustomAttributeValue).filter(and_(
        ExternalCustomAttributeValue.attributable_type == self.__class__.__name__,
        ExternalCustomAttributeValue.attributable_id == self.id)).all()

    # Save previous value of custom attribute. This is a bit complicated by
    # the fact that imports can save multiple values at the time of writing.
    # old_values holds all previous values of attribute, last_values holds
    # chronologically last value.
    for value in attr_values:
      old_values[value.custom_attribute_id].append(
          (value.created_at, value.attribute_value))

    self._remove_existing_items(attr_values)

    # 4) Instantiate custom attribute values for each of the definitions
    #    passed in (keys)
    # pylint: disable=not-an-iterable
    # filter out attributes like Person:None
    attributes = {k: v for k, v in attributes.items() if v != "Person:None"}
    definitions = {d.id: d for d in self.get_custom_attribute_definitions()}
    for ad_id in attributes.keys():
      obj_type = self.__class__.__name__
      obj_id = self.id
      new_value = ExternalCustomAttributeValue(
          custom_attribute_id=int(ad_id),
          attributable=self,
          attribute_value=attributes[ad_id],
      )
      if definitions[int(ad_id)].attribute_type.startswith("Map:"):
        obj_type, obj_id = new_value.attribute_value.split(":")
        new_value.attribute_value = obj_type
        new_value.attribute_object_id = long(obj_id)
      elif definitions[int(ad_id)].attribute_type == "Checkbox":
        new_value.attribute_value = "1" if new_value.attribute_value else "0"

      # 5) Set the context_id for each custom attribute value to the context id
      #    of the custom attributable.
      # TODO: We are ignoring contexts for now
      # new_value.context_id = cls.context_id

      # new value is appended to self.custom_attribute_values by the ORM
      # self.custom_attribute_values.append(new_value)

  @classmethod
  def get_custom_attribute_definitions(cls, field_names=None):   # TODO DOuble CHECK
    """Get all applicable CA definitions (even ones without a value yet)."""
    from ggrc.models.external_custom_attribute_definition import \
        ExternalCustomAttributeDefinition as cad

    query = cad.query.filter(
        cad.definition_type == utils.underscore_from_camelcase(cls.__name__)
    )
    if field_names:
      query = query.filter(
          sqlalchemy.or_(cad.title.in_(field_names), cad.mandatory)
      )
    return query.options(
        orm.undefer_group('ExternalCustomAttributeDefinition_complete')
    )

  @classmethod
  def eager_query(cls, **kwargs):
    """Define fields to be loaded eagerly to lower the count of DB queries."""
    query = super(ExternalCustomAttributable, cls).eager_query(**kwargs)
    query = query.options(
        orm.subqueryload('custom_attribute_definitions')
           .undefer_group('ExternalCustomAttributeDefinition_complete'),
        orm.subqueryload('_custom_attribute_values')
           .undefer_group('ExternalCustomAttributeValue_complete')
           .subqueryload('{0}_custom_attributable'.format(cls.__name__)),
        orm.subqueryload('_custom_attribute_values')
           .subqueryload('_related_revisions'),
    )
    if hasattr(cls, 'comments'):
      # only for Commentable classess
      query = query.options(
          orm.subqueryload('comments')
             .undefer_group('Comment_complete'),
      )
    return query

  def log_json(self):
    """Log custom attribute values."""
    # pylint: disable=not-an-iterable, protected-access
    from ggrc.models.external_custom_attribute_definition import \
        ExternalCustomAttributeDefinition

    res = super(ExternalCustomAttributable, self).log_json()

    if self.custom_attribute_values:
      res["custom_attribute_values"] = [
          value.log_json() for value in self.custom_attribute_values]
      # fetch definitions form database because `self.custom_attribute`
      # may not be populated
      defs = ExternalCustomAttributeDefinition.query.filter(
          ExternalCustomAttributeDefinition.definition_type ==
              self._inflector.table_singular,
          ExternalCustomAttributeDefinition.id.in_([
              value.custom_attribute_id
              for value in self.custom_attribute_values
          ])
      )
      # also log definitions to freeze field names in time
      res["custom_attribute_definitions"] = [
          definition.log_json() for definition in defs]
    else:
      res["custom_attribute_definitions"] = []
      res["custom_attribute_values"] = []

    return res
