# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

import inspect
import sqlalchemy as sa

from ggrc.models import inflector
from ggrc.models import reflection
from ggrc.models import all_models
from ggrc.models.all_models import *  # noqa
from ggrc.models.custom_attribute_definition import init_cad_listeners
from ggrc.utils import html_cleaner
from ggrc.utils import benchmark

"""All GGRC model objects and associated utilities."""


def init_models(app):
  for model in all_models.all_models:
    inflector.register_inflections(model._inflector)


def init_hooks():
  """Initialize main and extensions related SQLAlchemy hooks."""
  from ggrc.extensions import get_extension_modules
  from ggrc.models import hooks

  hooks.init_hooks()
  for extension_module in get_extension_modules():
    ext_init_hooks = getattr(extension_module, 'init_hooks', None)
    if ext_init_hooks:
      ext_init_hooks()


def init_all_models(app):
  """Register all GGRC models services with the Flask application ``app``."""

  from ggrc.extensions import get_extension_modules

  # Usually importing the module is enough, but just in case, also invoke
  # ``init_models``
  init_models(app)
  for extension_module in get_extension_modules():
    ext_init_models = getattr(extension_module, 'init_models', None)
    if ext_init_models:
      ext_init_models(app)
  init_hooks()


def init_lazy_mixins():
  """Lazy mixins initialisation

  Mixins with `__lazy__init__` property set to True will wait with their
  initialization until after the models have been fully initialized. This is
  useful in cases where we need full model class, e.g. to hook up signaling
  logic.
  """
  for model in all_models.all_models:
    # MRO chain includes base model that we don't want to include here
    mixins = (mixin for mixin in inspect.getmro(model) if mixin != model)
    for mixin in mixins:
      if getattr(mixin, '__lazy_init__', False):
        mixin.init(model)


def init_session_monitor_cache():
  from sqlalchemy.orm.session import Session
  from sqlalchemy import event
  from ggrc.models.cache import Cache

  def update_cache_before_flush(session, flush_context, objects):
    with benchmark("update cache before flush"):
      cache = Cache.get_cache(create=True)
      if cache:
        cache.update_before_flush(session, flush_context)

  def update_cache_after_flush(session, flush_context):
    with benchmark("update cache after flush"):
      cache = Cache.get_cache(create=False)
      if cache:
        cache.update_after_flush(session, flush_context)

  def clear_cache(session):
    cache = Cache.get_cache()
    if cache:
      cache.clear()

  event.listen(Session, 'before_flush', update_cache_before_flush)
  event.listen(Session, 'after_flush', update_cache_after_flush)
  event.listen(Session, 'after_commit', clear_cache)
  event.listen(Session, 'after_rollback', clear_cache)


def init_sanitization_hooks():
  # Register event listener on all String and Text attributes to sanitize them.
  for model in all_models.all_models:  # noqa
    attr_names = reflection.AttributeInfo.gather_attrs(model, "_sanitize_html")
    for attr_name in attr_names:
      attr = getattr(model, attr_name)
      sa.event.listen(attr, 'set', html_cleaner.cleaner, retval=True)


def init_app(app):
  init_all_models(app)
  init_lazy_mixins()
  init_session_monitor_cache()
  init_sanitization_hooks()
  init_cad_listeners()

from ggrc.models.inflector import get_model  # noqa
