# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Util to get objects from flask.g.referenced_objects or DB if not present."""

import collections

import flask
from sqlalchemy import orm

from ggrc import db
from ggrc.models import inflector
from ggrc.models.mixins import customattributable as ca
from ggrc.models.mixins import external_customattributable as e_ca


def get(type_, id_):
  """Check flask.g.referenced_objects for the object or get it from the DB."""
  # id == 0 is a valid case if id is an int; therefore "not id" doesn't fit
  if id_ is None:
    return None

  ref_objects = getattr(flask.g, "referenced_objects", {})

  if not (isinstance(type_, type) and issubclass(type_, db.Model)):
    type_ = inflector.get_model(type_)
  # model for type_ has been removed
  if type_ is None:
    return None
  result = ref_objects.get(type_, {}).get(id_, None)

  if not result:
    result = type_.query.get(id_)

  return result


def mark_to_cache(type_, id_):
  """Mark object for warmup"""
  if not hasattr(flask.g, "referenced_objects_markers"):
    flask.g.referenced_objects_markers = collections.defaultdict(set)
  if not (isinstance(type_, type) and issubclass(type_, db.Model)):
    type_ = inflector.get_model(type_)
  if type_ is not None:
    flask.g.referenced_objects_markers[type_].add(id_)


def rewarm_cache(rewarm_type=None, skip_cad=False, undefer=False):
  """Rewarm cache on call.

  rewarm_type (type): Type of objects that should be loaded upon cache rewarm.
    If None all objects of all types in cache will be loaded.
  skip_cad (bool): Flag indicating whether custom attribute defenitions should
    be loaded for objects in cache or not. Defaults to False.
  undefer (bool): Flag indicating whether object's deferred fields should be
    undeferred upon loading or not. Defaults to False.
  """
  if not hasattr(flask.g, "referenced_objects_markers"):
    return

  if not hasattr(flask.g, "referenced_objects"):
    flask.g.referenced_objects = {}

  options = dict(skip_cad=skip_cad, undefer=undefer)
  modifiers = (
      _skip_cads,
      _undefer,
  )

  warm_cache = _get_cache_to_rewarm(rewarm_type)
  for type_, ids in warm_cache.iteritems():
    if type_ not in flask.g.referenced_objects:
      flask.g.referenced_objects[type_] = {}
    if not ids:
      continue

    query = type_.query.filter(type_.id.in_(ids))
    for modifier in modifiers:
      query = modifier(type_, query, **options)

    for obj in query:
      flask.g.referenced_objects[type_][obj.id] = obj
    _set_not_found_ids(type_, ids)


def _get_cache_to_rewarm(rewarm_type):
  """Get cache to rewarm based on `rewarm_type` provided."""
  if rewarm_type is None:
    cache = flask.g.referenced_objects_markers
    del flask.g.referenced_objects_markers
  else:
    cache = {rewarm_type: flask.g.referenced_objects_markers[rewarm_type]}
    del flask.g.referenced_objects_markers[rewarm_type]
  return cache


def _skip_cads(type_, query, skip_cad=False, **_):
  """Add `skip_cad` option on query."""
  if issubclass(type_, ca.CustomAttributable) and not skip_cad:
    query = query.options(
        orm.Load(type_).subqueryload(
            "custom_attribute_definitions"
        ).undefer_group(
            "CustomAttributeDefinition_complete"
        )
    )
  if issubclass(type_, e_ca.ExternalCustomAttributable) and not skip_cad:
    query = query.options(
        orm.Load(type_).subqueryload(
            "custom_attribute_definitions"
        ).undefer_group(
            "ExternalCustomAttributeDefinition_complete"
        )
    )
  return query


def _undefer(type_, query, undefer=False, **_):
  """Add `undefer` option on query."""
  if undefer:
    query = query.options(
        orm.Load(type_).undefer_group("{}_complete".format(type_.__name__))
    )
  return query


def _set_not_found_ids(type_, ids):
  """Set ids from `ids` not found during cache rewarm of `type_` to None."""
  for id_ in ids:
    if id_ not in flask.g.referenced_objects[type_]:
      flask.g.referenced_objects[type_][id_] = None
