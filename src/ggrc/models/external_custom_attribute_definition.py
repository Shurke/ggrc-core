# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""External Custom attribute definition module"""

import re

from sqlalchemy.orm import validates
from sqlalchemy.sql.schema import UniqueConstraint

from ggrc import db
from ggrc.access_control import role as acr
from ggrc.models import reflection
from ggrc.models.custom_attribute_definition \
  import get_inflector_model_name_dict
from ggrc.models.custom_attribute_definition \
  import CustomAttributeDefinitionBase
from ggrc.utils import errors
from ggrc.utils import validators


class ExternalCustomAttributeDefinition(CustomAttributeDefinitionBase):
  """External Custom attribute definition model."""

  VALID_TYPES = {
      "Text": "Text",
      "Rich Text": "Rich Text",
      "Dropdown": "Dropdown",
      "Multiselect": "Multiselect",
      "Date": "Date",
  }

  __tablename__ = 'external_custom_attribute_definitions'

  id = db.Column(db.Integer, primary_key=True, autoincrement=False)
  external_id = db.Column(db.Integer, nullable=True, unique=True)
  definition_id = None

  attribute_values = db.relationship('ExternalCustomAttributeValue',
                                     backref='custom_attribute',
                                     cascade='all, delete-orphan')

  _root_attribute = "custom_attribute_definition"

  _extra_table_args = (
      UniqueConstraint('definition_type',
                       'title',
                       name='uq_custom_attribute'),
      db.Index('ix_custom_attributes_title', 'title')
  )

  _include_links = [
      'definition_type',
      'attribute_type',
      'multi_choice_options',
      'mandatory',
      'helptext',
      'placeholder',
  ]

  _api_attrs = reflection.ApiAttributes(
      "id",
      "external_id",
      reflection.Attribute("default_value",
                           read=True,
                           create=False,
                           update=False),
      reflection.Attribute("definition_id",
                           read=True,
                           create=False,
                           update=False),
      *_include_links
  )

  @property
  def definition_attr(self):
    return '{0}_definition'.format(self.definition_type)

  @property
  def definition(self):
    return getattr(self, self.definition_attr)

  @definition.setter
  def definition(self, value):
    if hasattr(value, '_inflector'):
      self.definition_type = value._inflector.table_singular
    else:
      self.definition_type = ''
    return setattr(self, self.definition_attr, value)

  @validates("title", "definition_type")
  def validate_title(self, key, value):
    """Validate CAD title/name uniqueness.

    Note: title field is used for storing CAD names.
    CAD names need to follow 6 uniqueness rules:
      1) Names must not match any attribute name on any existing object.
      2) Object level CAD names must not match any global CAD name.
      3) Object level CAD names can clash, but not for the same Object
         instance. This means we can have two CAD with a name "my cad", with
         different attributable_id fields.
      4) Names must not match any existing custom attribute role name
      5) Names should not contains special values (.validate_name_correct)
      6) Names should be stripped

    Third rule is handled by the database with unique key uq_custom_attribute
    (`definition_type`,`definition_id`,`title`).

    This validator should check for name collisions for 1st and 2nd rule.

    This validator works, because definition_type is never changed. It only
    gets set when the cad is created and after that only title filed can
    change. This makes validation using both fields possible.

    Args:
      value: custom attribute definition name

    Returns:
      value if the name passes all uniqueness checks.
    """

    value = value if value is None else re.sub(r"\s+", " ", value).strip()

    if key == "title":
      validators.validate_name_correctness(value)

    if key == "title" and self.definition_type:
      orig_name = value
      definition_type = self.definition_type
    elif key == "definition_type" and self.title:
      orig_name = self.title
      definition_type = value.lower()
    else:
      return value

    name = orig_name.lower()
    if name in self._get_reserved_names(definition_type):
      raise ValueError(
          errors.DUPLICATE_RESERVED_NAME.format(attr_name=orig_name)
      )

    if (self._get_global_ecad_names(definition_type).get(name) is not None and
            self._get_global_ecad_names(definition_type).get(name) != self.id):
      raise ValueError(errors.DUPLICATE_GCAD_NAME.format(attr_name=orig_name))

    self.assert_acr_exist(orig_name, definition_type)

    return value

  @staticmethod
  def assert_acr_exist(name, definition_type):
    """Validate that there is no ACR with provided name."""
    model_name = get_inflector_model_name_dict()[definition_type]
    acrs = {i.lower() for i in acr.get_custom_roles_for(model_name).values()}
    if name.lower() in acrs:
      raise ValueError(
          errors.DUPLICATE_CUSTOM_ROLE.format(role_name=name)
      )
