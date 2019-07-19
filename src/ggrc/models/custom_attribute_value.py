# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Custom attribute value model"""

from sqlalchemy import and_
from sqlalchemy import or_
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import foreign

from ggrc import builder
from ggrc import db
from ggrc import utils
from ggrc.fulltext import mixin as ft_mixin
from ggrc.models import reflection
from ggrc.models.mixins import base
from ggrc.models.revision import Revision
from ggrc.utils import url_parser


class CustomAttributeValueBase(base.ContextRBAC,
                               base.Base,
                               ft_mixin.Indexed,
                               db.Model):
  """Custom attribute value base class"""
  __abstract__ = True

  REQUIRED_GLOBAL_REINDEX = False

  attributable_type = db.Column(db.String)
  attributable_id = db.Column(db.Integer)
  attribute_value = db.Column(db.String, nullable=False, default=u"")

  _fulltext_attrs = ["attribute_value"]

  _sanitize_html = ["attribute_value"]

  # pylint: disable=protected-access
  # This is just a mapping for accessing local functions so protected access
  # warning is a false positive
  _validator_map = {
      "Text": lambda self: self._validate_text(),
      "Rich Text": lambda self: self._validate_rich_text(),
      "Date": lambda self: self._validate_date(),
      "Dropdown": lambda self: self._validate_dropdown(),
      "Multiselect": lambda self: self._validate_multiselect(),
  }
  TYPES_NO_RICHTEXT_VALIDATE = ["Control"]

  @property
  def attributable_attr(self):
    return '{0}_custom_attributable'.format(self.attributable_type)

  @property
  def attributable(self):
    return getattr(self, self.attributable_attr)

  @attributable.setter
  def attributable(self, value):
    self.attributable_id = value.id if value is not None else None
    self.attributable_type = value.__class__.__name__ if value is not None \
        else None
    return setattr(self, self.attributable_attr, value)

  @staticmethod
  def _extra_table_args(_):
    return (
        db.UniqueConstraint('attributable_id', 'custom_attribute_id'),
    )

  @property
  def latest_revision(self):
    """Latest revision of CAV (used for comment precondition check)."""
    # TODO: make eager_query fetch only the first Revision
    return self._related_revisions[0]

  def get_reindex_pair(self):
    return self.attributable_type, self.attributable_id

  @classmethod
  def eager_query(cls, **kwargs):
    query = super(CustomAttributeValueBase, cls).eager_query(**kwargs)
    query = query.options(
        orm.subqueryload('_related_revisions'),
        orm.joinedload('custom_attribute'),
    )
    return query

  @declared_attr
  def _related_revisions(cls):  # pylint: disable=no-self-argument
    """Returns related revisions."""
    def join_function():
      """Function to join CAV to its latest revision."""
      resource_id = foreign(Revision.resource_id)
      resource_type = foreign(Revision.resource_type)
      return and_(resource_id == cls.id,
                  resource_type == cls.__name__)

    return db.relationship(
        Revision,
        primaryjoin=join_function,
        viewonly=True,
        order_by=Revision.created_at.desc(),
    )

  def _validate_dropdown(self):
    """Validate dropdown option."""
    valid_options = set(self.custom_attribute.multi_choice_options.split(","))
    if self.attribute_value:
      self.attribute_value = self.attribute_value.strip()
      if self.attribute_value not in valid_options:
        raise ValueError("Invalid custom attribute dropdown option: {v}, "
                         "expected one of {l}"
                         .format(v=self.attribute_value, l=valid_options))

  def _validate_date(self):
    """Convert date format."""
    if self.attribute_value:
      # Validate the date format by trying to parse it
      self.attribute_value = utils.convert_date_format(
          self.attribute_value,
          utils.DATE_FORMAT_ISO,
          utils.DATE_FORMAT_ISO,
      )

  def _validate_text(self):
    """Trim whitespaces."""
    if self.attribute_value:
      self.attribute_value = self.attribute_value.strip()

  def _validate_rich_text(self):
    """Add tags for links."""
    if self.attributable_type not in self.TYPES_NO_RICHTEXT_VALIDATE:
      self.attribute_value = url_parser.parse(self.attribute_value)

  def _validate_multiselect(self):
    """Validate multiselect checkbox values."""
    if self.attribute_value:
      valid_options = set(
          self.custom_attribute.multi_choice_options.split(","))
      attr_values = set(self.attribute_value.split(","))
      if not attr_values.issubset(valid_options):
        raise ValueError("Invalid custom attribute multiselect options {act}. "
                         "Expected some of {exp}".format(act=attr_values,
                                                         exp=valid_options))

  def validate(self):
    """Validate custom attribute value."""
    # pylint: disable=protected-access
    attributable_type = self.attributable._inflector.table_singular
    if not self.custom_attribute:
      raise ValueError("Custom attribute definition not found: Can not "
                       "validate custom attribute value")
    if self.custom_attribute.definition_type != attributable_type:
      raise ValueError("Invalid custom attribute definition used.")
    validator = self._validator_map.get(self.custom_attribute.attribute_type)
    if validator:
      validator(self)


class CustomAttributeValue(CustomAttributeValueBase):
  """Custom attribute value model"""

  __tablename__ = 'custom_attribute_values'

  # When the attribute is of a mapping type this will hold the id of the mapped
  # object while attribute_value will hold the type name.
  # For example an instance of attribute type Map:Person will have a person id
  # in attribute_object_id and string 'Person' in attribute_value.
  attribute_object_id = db.Column(db.Integer)

  custom_attribute_id = db.Column(
      db.Integer,
      db.ForeignKey('custom_attribute_definitions.id',
                    ondelete="CASCADE")
  )

  _api_attrs = reflection.ApiAttributes(
      'custom_attribute_id',
      'attributable_id',
      'attributable_type',
      'attribute_value',
      'attribute_object',
      reflection.Attribute('preconditions_failed',
                           create=False,
                           update=False),
  )

  # pylint: disable=protected-access
  _validator_map = {
      "Text": lambda self: self._validate_text(),
      "Rich Text": lambda self: self._validate_rich_text(),
      "Date": lambda self: self._validate_date(),
      "Dropdown": lambda self: self._validate_dropdown(),
      "Multiselect": lambda self: self._validate_multiselect(),
      "Map:Person": lambda self: self._validate_map_object(),
      "Checkbox": lambda self: self._validate_checkbox(),
  }

  @property
  def attribute_object(self):
    """Fetch the object referred to by attribute_object_id.

    Use backrefs defined in CustomAttributeMapable.

    Returns:
        A model instance of type specified in attribute_value
    """
    try:
      return getattr(self, self._attribute_object_attr)
    except:  # pylint: disable=bare-except
      return None

  @attribute_object.setter
  def attribute_object(self, value):
    """Set attribute_object_id via whole object.

    Args:
        value: model instance
    """
    if value is None:
      # We get here if "attribute_object" does not get resolved.
      # TODO: make sure None value can be set for removing CA attribute object
      # value
      return None
    self.attribute_object_id = value.id
    return setattr(self, self._attribute_object_attr, value)

  @property
  def attribute_object_type(self):
    """Fetch the mapped object pointed to by attribute_object_id.

    Returns:
       A model of type referenced in attribute_value
    """
    attr_type = self.custom_attribute.attribute_type
    if not attr_type.startswith("Map:"):
      return None
    return self.attribute_object.__class__.__name__

  @property
  def _attribute_object_attr(self):
    """Compute the relationship property based on object type.

    Returns:
        Property name
    """
    attr_type = self.custom_attribute.attribute_type
    if not attr_type.startswith("Map:"):
      return None
    return 'attribute_{0}'.format(self.attribute_value)

  @classmethod
  def mk_filter_by_custom(cls, obj_class, custom_attribute_id):
    """Get filter for custom attributable object.

    This returns an exists filter for the given predicate, matching it to
    either a custom attribute value, or a value of the matched object.

    Args:
      obj_class: Class of the attributable object.
      custom_attribute_id: Id of the attribute definition.
    Returns:
      A function that will generate a filter for a given predicate.
    """
    from ggrc.models import all_models
    attr_def = all_models.CustomAttributeDefinition.query.filter_by(
        id=custom_attribute_id
    ).first()
    if attr_def and attr_def.attribute_type.startswith("Map:"):
      map_type = attr_def.attribute_type[4:]
      map_class = getattr(all_models, map_type, None)
      if map_class:
        fields = [getattr(map_class, name, None)
                  for name in ["email", "title", "slug"]]
        fields = [field for field in fields if field is not None]

        def filter_by_mapping(predicate):
          return cls.query.filter(
              (cls.custom_attribute_id == custom_attribute_id) &
              (cls.attributable_type == obj_class.__name__) &
              (cls.attributable_id == obj_class.id) &
              (map_class.query.filter(
                  (map_class.id == cls.attribute_object_id) &
                  or_(*[predicate(f) for f in fields])).exists())
          ).exists()
        return filter_by_mapping

    def filter_by_custom(predicate):
      return cls.query.filter(
          (cls.custom_attribute_id == custom_attribute_id) &
          (cls.attributable_type == obj_class.__name__) &
          (cls.attributable_id == obj_class.id) &
          predicate(cls.attribute_value)
      ).exists()
    return filter_by_custom

  def _validate_checkbox(self):
    """Set falsy value to zero."""
    if not self.attribute_value:
      self.attribute_value = "0"

  def _validate_map_object(self):
    """Validate and correct mapped object values

    Mapped object custom attribute is only valid if both attribute_value and
    attribute_object_id are set. To keep the custom attribute api consistent
    with other types, we allow setting the value to a string containing both
    in this way "attribute_value:attribute_object_id". This validator checks
    Both scenarios and changes the string value to proper values needed by
    this custom attribute.
    """
    self._extract_object_id_from_value()
    self._validate_map_type()
    self._validate_object_existence()

  def _extract_object_id_from_value(self):
    """Extract attribute_object_id from attribute_value"""
    if self.attribute_value and ":" in self.attribute_value:
      value, id_ = self.attribute_value.split(":")
      self.attribute_value = value
      self.attribute_object_id = id_

  def _validate_map_type(self):
    """Validate related CAD attribute_type and provided attribute_value

    Related custom attribute definition's attribute_type column must starts
    with "Map:".

    Example:
      "Map:Person" - for mapping with Person model

    Provided attribute_value should match to custom attribute definition's
    attribute_type. If definition have "Map:Person" attribute_type,
    attribute_value must be "Person".
    """
    from ggrc.models import all_models

    mapping_prefix = 'Map:'

    defined_type = self.custom_attribute.attribute_type
    if not defined_type.startswith(mapping_prefix):
      raise ValueError('Invalid definition type: %s expected mapping' %
                       defined_type)

    if not self.attribute_value:
      return

    try:
      expected_type = defined_type.split(mapping_prefix)[1]
    except IndexError:
      raise ValueError("Invalid definition type: mapping type didn't provided")

    if self.attribute_value != expected_type:
      raise ValueError('Invalid attribute type: %s expected %s' %
                       (self.attribute_value, expected_type))

    related_model = getattr(all_models, self.attribute_value)
    if not related_model or not issubclass(related_model, db.Model):
      raise ValueError('Invalid attribute type: %s' % self.attribute_value)

  def _validate_object_existence(self):
    """Validate existence of provided attribute_object_id

    To verify that attribute type is correct,
    must be called after '_validate_map_type()' method.
    """
    from ggrc.models import all_models

    if not self.attribute_object_id:
      return

    related_model = getattr(all_models, self.attribute_value)
    related_object = related_model.query.filter_by(
        id=self.attribute_object_id)

    object_existence = db.session.query(related_object.exists()).scalar()

    if not object_existence:
      raise ValueError('Invalid attribute value: %s' %
                       self.custom_attribute.title)

  def _clone(self, obj):
    """Clone a custom value to a new object."""
    data = {
        "custom_attribute_id": self.custom_attribute_id,
        "attributable_id": obj.id,
        "attributable_type": self.attributable_type,
        "attribute_value": self.attribute_value,
        "attribute_object_id": self.attribute_object_id
    }
    ca_value = self.__class__(**data)
    db.session.add(ca_value)
    db.session.flush()
    return ca_value

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
    # - the type is a mapping and the object value id is empty
    if (self.attribute_object_type is not None and
            not self.attribute_object_id):
      return True
    # Otherwise it the CAV is not empty
    return False

  @builder.simple_property
  def preconditions_failed(self):
    """A list of requirements self introduces that are unsatisfied.

    Returns:
      [str] - a list of unsatisfied requirements; possible items are: "value" -
              missing mandatory value, "comment" - missing mandatory comment,
              "evidence" - missing mandatory evidence.

    """
    failed_preconditions = []
    if self.custom_attribute.mandatory and self.is_empty:
      failed_preconditions += ["value"]
    if (self.custom_attribute.attribute_type ==
            self.custom_attribute.ValidTypes.DROPDOWN):
      failed_preconditions += self._check_dropdown_requirements()
    return failed_preconditions or None

  def _check_dropdown_requirements(self):
    """Check mandatory comment and mandatory evidence for dropdown CAV."""
    failed_preconditions = []
    options_to_flags = self.multi_choice_options_to_flags(
        self.custom_attribute,
    )
    flags = options_to_flags.get(self.attribute_value)
    if flags:
      for requirement in flags.keys():
        if not flags[requirement]:
          continue
        if requirement == "comment":
          failed_preconditions += self._check_mandatory_comment()
        else:
          failed_preconditions += self.attributable \
                                      .check_mandatory_requirement(requirement)

    return failed_preconditions

  def _check_mandatory_comment(self):
    """Check presence of mandatory comment."""
    if hasattr(self.attributable, "comments"):
      comment_found = any(
          self.custom_attribute_id == (comment
                                       .custom_attribute_definition_id) and
          self.latest_revision.id == comment.revision_id
          for comment in self.attributable.comments
      )
    else:
      comment_found = False
    if not comment_found:
      return ["comment"]
    return []

  @staticmethod
  def multi_choice_options_to_flags(cad):
    """Parse mandatory comment and evidence flags from dropdown CA definition.

    Args:
      cad - a CA definition object

    Returns:
      {option_value: Flags} - a dict from dropdown options values to dict
                              where keys "comment", "evidence" and "url"
                              corresponds to the values from
                              multi_choice_mandatory bitmasks
    """

    def make_flags(multi_choice_mandatory):
      flags_mask = int(multi_choice_mandatory)
      return {
          "comment": flags_mask & (cad
                                   .MultiChoiceMandatoryFlags
                                   .COMMENT_REQUIRED),
          "evidence": flags_mask & (cad
                                    .MultiChoiceMandatoryFlags
                                    .EVIDENCE_REQUIRED),
          "url": flags_mask & (cad
                               .MultiChoiceMandatoryFlags
                               .URL_REQUIRED),
      }

    if not cad.multi_choice_options or not cad.multi_choice_mandatory:
      return {}
    return dict(zip(
        cad.multi_choice_options.split(","),
        (make_flags(mask)
         for mask in cad.multi_choice_mandatory.split(",")),
    ))

  def log_json_base(self):
    res = super(CustomAttributeValue, self).log_json_base()

    if self.attribute_object_id is not None and \
       self._attribute_object_attr is not None:
      res["attribute_object"] = self.attribute_object

    return res
