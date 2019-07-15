# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Factories for ggrc models.

These are factories for generating regular ggrc models. The factories create a
model and log a post event with the model revision. These do not however
trigger signals. For tests that rely on proper signals being triggered, we must
use the object generator in the ggrc.generator module.
"""

# pylint: disable=too-few-public-methods,missing-docstring,old-style-class
# pylint: disable=no-init

import factory

from ggrc import db
from ggrc import models
from ggrc.fulltext import get_indexer
from ggrc.fulltext import mixin
from ggrc.login import noop


class ModelFactory(factory.Factory, object):

  @classmethod
  def _create(cls, target_class, *args, **kwargs):
    instance = target_class(*args, **kwargs)
    db.session.add(instance)
    if isinstance(instance, (models.CustomAttributeValue,
                             models.ExternalCustomAttributeValue)):
      cls._log_event(instance.attributable)
    if hasattr(instance, "log_json"):
      cls._log_event(instance)
    if getattr(db.session, "single_commit", True):
      db.session.commit()
    return instance

  @classmethod
  def _log_event(cls, instance, action="POST"):
    db.session.flush()
    user = cls._get_user()
    revision = models.Revision(
        instance, user.id, 'created', instance.log_json())
    event = models.Event(
        modified_by=user,
        action=action,
        resource_id=instance.id,
        resource_type=instance.type,
        revisions=[revision],
    )
    db.session.add(revision)
    db.session.add(event)

    indexer = get_indexer()
    if cls._is_reindex_needed(instance):
      indexer.delete_record(instance.id, instance.type, commit=False)
      indexer.create_record(instance, commit=False)

  @staticmethod
  def _is_reindex_needed(instance):
    # Snapshots are a special case cause they are indexed only if their
    # child_type is indexed.
    return (
        issubclass(instance.__class__, mixin.Indexed) and
        instance.REQUIRED_GLOBAL_REINDEX
    ) or isinstance(instance, models.all_models.Snapshot)

  @staticmethod
  def _get_user():
    user = models.Person.query.first()
    if not user:
      user = models.Person(
          name=noop.DEFAULT_USER_NAME,
          email=noop.DEFAULT_USER_EMAIL,
      )
      db.session.add(user)
      db.session.flush()
    return user
