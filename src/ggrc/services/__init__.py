# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""All GGRC REST services."""

from ggrc.services import common
from ggrc.services.registry import service
from ggrc.services.resources import external_internal


def contributed_services():
  """The list of all GGRC collection services as a list of
  (url, ModelClass) tuples.
  """
  import ggrc.models.all_models as models
  from ggrc.access_control import role
  from ggrc.models import review
  from ggrc.services.resources import access_controle_role
  from ggrc.services.resources import assessment
  from ggrc.services.resources import audit
  from ggrc.services.resources import external
  from ggrc.services.resources import issue
  from ggrc.services.resources import person
  from ggrc.services.resources import related_assessments
  from ggrc.services.resources import relationship
  from ggrc.services.resources import snapshot

  return [
      service('background_tasks', models.BackgroundTask),
      service('access_groups', models.AccessGroup),
      service('audits', models.Audit, audit.AuditResource),
      service('calendar_events', models.CalendarEvent),
      service('contexts', models.Context),
      service('controls', models.Control, external.ExternalResource),
      service('assessments', models.Assessment, assessment.AssessmentResource),
      service('assessment_templates', models.AssessmentTemplate),
      service('comments', models.Comment),
      service('external_comments', models.ExternalComment),
      service('internal_custom_attribute_definitions',
              models.CustomAttributeDefinition),
      service('external_custom_attribute_definitions',
              models.ExternalCustomAttributeDefinition,
              external.ExternalCADResource),
      service('data_assets', models.DataAsset),
      service('directives', models.Directive, common.ReadOnlyResource),
      service('contracts', models.Contract),
      service('evidence', models.Evidence),
      service('policies', models.Policy),
      service('regulations', models.Regulation),
      service('standards', models.Standard),
      service('documents', models.Document),
      service('events', models.Event, common.ReadOnlyResource),
      service('facilities', models.Facility),
      service('markets', models.Market),
      service('object_people', models.ObjectPerson),
      service('objectives', models.Objective),
      service('options', models.Option),
      service('org_groups', models.OrgGroup),
      service('vendors', models.Vendor),
      service('people', models.Person, person.PersonResource),
      service('people_profiles', models.PersonProfile),
      service('products', models.Product),
      service('projects', models.Project),
      service('programs', models.Program),
      service('relationships',
              models.Relationship,
              relationship.RelationshipResource),
      service('revisions', models.Revision, common.ReadOnlyResource),
      service('requirements', models.Requirement),
      service('risks', models.Risk, external.ExternalResource),
      service('threats', models.Threat),
      service('systems_or_processes',
              models.SystemOrProcess,
              common.ReadOnlyResource),
      service('systems',
              models.System,
              external_internal.ExternalInternalResource),
      service('processes', models.Process),
      service('metrics', models.Metric),
      service('notification_configs', models.NotificationConfig),
      service('issues', models.Issue, issue.IssueResource),
      service('snapshots', models.Snapshot, snapshot.SnapshotResource),
      service('access_control_roles', role.AccessControlRole,
              access_controle_role.AccessControlRoleResource),
      service('labels', models.Label),
      service('proposals', models.Proposal),
      service('related_assessments', None,
              related_assessments.RelatedAssessmentsResource),
      service('technology_environments', models.TechnologyEnvironment),
      service('product_groups', models.ProductGroup),
      service('reviews', review.Review),
      service('key_reports', models.KeyReport),
      service('account_balances', models.AccountBalance),
  ]


def all_services():
  """Get services from all modules."""
  from ggrc.extensions import get_extension_modules

  services = contributed_services()

  for extension_module in get_extension_modules():
    contributions = getattr(extension_module, 'contributed_services', None)
    if contributions:
      if callable(contributions):
        contributions = contributions()
      services.extend(contributions)
  return services


def init_extra_services(app):
  """Add extra service url rules."""
  from ggrc.login import login_required

  from ggrc.services.search import search
  app.add_url_rule(
      '/search', 'search', login_required(search))

  from ggrc.services.suggest import suggest
  app.add_url_rule('/people/suggest', 'suggest', login_required(suggest))

  init_cad_router(app)


def init_cad_router(app):
  """Register /api/custom_attribute_definitions endpoint with router logic"""
  from ggrc.services import CustomAttributeDefinition as cad_service
  from ggrc.models import all_models
  from ggrc.models.mixins import ExternalCustomAttributable

  ecad_models = {model._inflector.table_singular
                 for model in all_models.all_models
                 if issubclass(model, ExternalCustomAttributable)}

  def router(*args, **kwargs):
    """Route request to eCAD resource

    Route request to eCAD resource if definition_type object
    is ExternalCustomAttributable
    """
    from flask import request

    definition_type = (
        request.values.get("definition_type")
    ) or (
        request.json and
        request.json[0].get(
            "custom_attribute_definition", {}
        ).get(
            "definition_type"
        )
    )
    if definition_type in ecad_models:
      view_func = app.view_functions["ExternalCustomAttributeDefinition"]
    else:
      view_func = app.view_functions["CustomAttributeDefinition"]
    return view_func(*args, **kwargs)

  url = "/api/custom_attribute_definitions"
  app.add_url_rule(
      url,
      defaults={cad_service.pk: None},
      endpoint="custom_attribute_definitions_router",
      view_func=router,
      methods=["GET", "POST", "PATCH"])
  app.add_url_rule(
      "{url}/<{type}:{pk}>".format(url=url,
                                   type=cad_service.pk_type,
                                   pk=cad_service.pk),
      endpoint="custom_attribute_definitions_router",
      view_func=router,
      methods=["GET", "PUT", "DELETE"])


def init_all_services(app):
  """Register all GGRC REST services with the Flask application ``app``."""
  from ggrc.extensions import get_extension_modules
  from ggrc.login import login_required

  for entry in all_services():
    entry.service_class.add_to(
        app,
        '/api/{0}'.format(entry.name),
        entry.model_class,
        decorators=(login_required,),
    )

  init_extra_services(app)
  for extension_module in get_extension_modules():
    ext_extra_services = getattr(extension_module, 'init_extra_services', None)
    if ext_extra_services:
      ext_extra_services(app)
