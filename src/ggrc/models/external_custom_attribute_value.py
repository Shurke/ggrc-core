# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""External Custom attribute value model"""

from ggrc import builder
from ggrc import db
from ggrc.models import reflection
from ggrc.models.custom_attribute_value import CustomAttributeValueBase


class ExternalCustomAttributeValue(CustomAttributeValueBase):
  """External custom attribute value model"""

  __tablename__ = 'external_custom_attribute_values'

  external_id = db.Column(db.Integer, nullable=True, unique=True)
  custom_attribute_id = db.Column(
      db.Integer,
      db.ForeignKey('external_custom_attribute_definitions.id',
                    ondelete="CASCADE")
  )

  _api_attrs = reflection.ApiAttributes(
      "id",
      "external_id",
      'custom_attribute_id',
      'attributable_id',
      'attributable_type',
      'attribute_value',
  )

  @builder.simple_property
  def is_empty(self):
    """Return True if the CAV is empty or holds a logically empty value."""
    # The CAV is considered empty when:
    # - the value is empty
    if not self.attribute_value:
      return True
    # - the type is Checkbox and the value is 0
    if (self.custom_attribute.attribute_type ==
            self.custom_attribute.ValidTypes.CHECKBOX and
            str(self.attribute_value) == "0"):
      return True
    # Otherwise it the CAV is not empty
    return False
