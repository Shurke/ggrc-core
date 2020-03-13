# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

""" Module for WithEvidence mixin."""
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr

from ggrc import db
from ggrc.fulltext.attributes import MultipleSubpropertyFullTextAttr
from ggrc.models import reflection
from ggrc.models.evidence import Evidence
from ggrc.models.relationship import Relationship


class WithEvidence(object):
  """WithEvidence mixin."""

  _include_links = []

  _fulltext_attrs = [
      MultipleSubpropertyFullTextAttr('evidences_file', 'evidences_file',
                                      ['title', 'link']),
      MultipleSubpropertyFullTextAttr('evidences_url', 'evidences_url',
                                      ['link'])
  ]

  _aliases = {
      "evidences_url": {
          "display_name": "Evidence URL",
          "type": reflection.AttributeInfo.Type.SPECIAL_MAPPING,
          "description": "New line separated list of URLs.",
      },

      "evidences_file": {
          "display_name": "Attachment",
          "type": reflection.AttributeInfo.Type.SPECIAL_MAPPING,
          "description": (
              "New line separated list of evidence links and "
              "titles.\nExample:\n\nhttp://my.gdrive.link/file "
              "Title of the evidence link"
          ),
      }
  }

  @declared_attr
  def evidences(cls):  # pylint: disable=no-self-argument
    """Return evidences related for that instance."""
    return db.relationship(
        Evidence,
        primaryjoin=lambda: sa.or_(
            sa.and_(
                cls.id == Relationship.source_id,
                Relationship.source_type == cls.__name__,
                Relationship.destination_type == "Evidence",
            ),
            sa.and_(
                cls.id == Relationship.destination_id,
                Relationship.destination_type == cls.__name__,
                Relationship.source_type == "Evidence",
            )
        ),
        secondary=Relationship.__table__,
        secondaryjoin=lambda: sa.or_(
            sa.and_(
                Evidence.id == Relationship.source_id,
                Relationship.source_type == "Evidence",
            ),
            sa.and_(
                Evidence.id == Relationship.destination_id,
                Relationship.destination_type == "Evidence",
            )
        ),
        viewonly=True,
    )

  def get_evidences_by_kind(self, kind):
    return [e for e in self.evidences
            if e.kind == kind]

  @property
  def evidences_url(self):
    return self.get_evidences_by_kind(Evidence.URL)

  @property
  def evidences_file(self):
    return self.get_evidences_by_kind(Evidence.FILE)

  @classmethod
  def eager_query(cls, **kwargs):
    """Eager query classmethod."""
    return cls.eager_inclusions(
        super(WithEvidence, cls).eager_query(**kwargs),
        WithEvidence._include_links,
    ).options(
        sa.orm.subqueryload(
            'evidences',
        ).undefer_group(
            'Evidence_complete',
        ),
    )

  @staticmethod
  def _log_evidences(evidences):
    """Returns serialization of the given docs"""
    return [e.log_json() for e in evidences if e]

  def log_json(self):
    """Serialize to JSON"""
    # This query is required to refresh related documents collection after
    # they were mapped to an object. Otherwise python uses cached value,
    # which might not contain newly created documents.
    out_json = super(WithEvidence, self).log_json()
    out_json['evidences_url'] = self._log_evidences(self.evidences_url)
    out_json['evidences_file'] = self._log_evidences(self.evidences_file)
    return out_json

  @classmethod
  def indexed_query(cls):
    return super(WithEvidence, cls).indexed_query().options(
        sa.orm.subqueryload("evidences").load_only(
            "kind",
            "title",
            "link",
        ),
    )
