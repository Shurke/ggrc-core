# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Structure object, required to save all meta info
required for diff building."""
import collections

import cached_property
import sqlalchemy as sa

from ggrc.models import reflection
from ggrc.access_control import role as ACR
from ggrc.access_control import roleable
from ggrc.models import mixins

Field = collections.namedtuple("Field", ["name", "mandatory"])


class MetaInfo(object):
  """Collects all meta data related to the instance."""

  def __init__(self, instance):
    self.instance = instance

  @cached_property.cached_property
  def _mandatory_attributes(self):
    """Property that saved all mandatory attrs for instance."""
    api_attrs = reflection.AttributeInfo.gather_attr_dicts(
        self.instance.__class__,
        "_aliases",
    )
    keys = set()
    for key, value in api_attrs.iteritems():
      if isinstance(value, dict) and value.get("mandatory"):
        keys.add(key)
    return keys

  @cached_property.cached_property
  def _updateable_attributes(self):
    return {
        k for k, v in
        reflection.AttributeInfo.gather_attr_dicts(
            self.instance.__class__,
            "_api_attrs").iteritems()
        if v.update
    }

  @cached_property.cached_property
  def _relationship_dict(self):
    """Generates relationships dict for self.instance, grouped by use_list."""
    relations = sa.inspection.inspect(self.instance.__class__).relationships
    relations_dict = collections.defaultdict(set)
    for rel in relations:
      if rel.key in self._updateable_attributes:
        relations_dict[rel.uselist].add(rel.key)
    descriptors = sa.inspection.inspect(
        self.instance.__class__
    ).all_orm_descriptors
    for key, proxy in dict(descriptors).iteritems():
      if key in self._updateable_attributes:

        if proxy.extension_type is sa.ext.associationproxy.ASSOCIATION_PROXY:
          relations_dict[True].add(key)

        elif proxy.extension_type is sa.ext.hybrid.HYBRID_PROPERTY:
          attribute = reflection.AttributeInfo.get_attr(
              self.instance.__class__, "_api_attrs", key)
          if isinstance(attribute, reflection.HybridAttribute):
            relations_dict[True].add(key)

    return relations_dict

  @cached_property.cached_property
  def acrs(self):
    """Return ACRs for sent instance."""
    if not isinstance(self.instance, roleable.Roleable):
      return set()
    return set(ACR.get_ac_roles_for(self.instance.type).values())

  @cached_property.cached_property
  def cads(self):
    """Return CADs for sent instance."""
    if not isinstance(self.instance, (mixins.CustomAttributable,
                                      mixins.ExternalCustomAttributable)):
      return set()
    return set(self.instance.custom_attribute_definitions)

  @cached_property.cached_property
  def fields(self):
    """Return fields Field structures for sent instance."""
    return [
        Field(c.name,
              not c.nullable or c.name in self._mandatory_attributes)
        for c in sa.inspection.inspect(self.instance.__class__).columns
        if not c.foreign_keys and c.name in self._updateable_attributes]

  @cached_property.cached_property
  def mapping_list_fields(self):
    """Return mapping list Field structures for sent instance."""
    return [Field(f, f in self._mandatory_attributes)
            for f in self._relationship_dict[True]]

  @cached_property.cached_property
  def mapping_fields(self):
    """Return mapping Field structures for sent instance."""
    return [Field(f, f in self._mandatory_attributes)
            for f in self._relationship_dict[False]]

  @property
  def mandatory(self):
    return {
        "fields": [f.name for f in self.fields if f.mandatory],
        "access_control_roles": [f.id for f in self.acrs if f.mandatory],
        "custom_attribute_definitions": [
            f.id for f in self.cads if f.mandatory
        ],
        "mapping_fields": [
            f.name for f in self.mapping_fields if f.mandatory
        ],
        "mapping_list_fields": [
            f.name for f in self.mapping_list_fields if f.mandatory
        ],
    }
