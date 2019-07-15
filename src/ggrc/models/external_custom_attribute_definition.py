# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""External Custom attribute definition module"""

from sqlalchemy.sql.schema import UniqueConstraint

from ggrc import db
from ggrc.models import reflection
from ggrc.models.custom_attribute_definition \
    import CustomAttributeDefinitionBase


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
  internal_id = db.Column(db.Integer, nullable=True, unique=True)
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

  def log_json(self):
    """Add extra fields to be logged in CADs."""
    results = super(ExternalCustomAttributeDefinition, self).log_json()
    results["default_value"] = self.default_value
    results["definition_id"] = self.definition_id
    return results
