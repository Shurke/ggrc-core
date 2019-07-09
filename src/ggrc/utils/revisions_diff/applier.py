# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Apply diff content to sent instance."""

import collections
import itertools

from sqlalchemy import inspect

from ggrc.access_control import roleable
from ggrc.access_control import role as ACR
from ggrc.models import all_models
from ggrc.models import mixins


def apply_acl(instance, content):
  """Apply ACLs."""
  any_acl_applied = False
  if not isinstance(instance, roleable.Roleable):
    return any_acl_applied
  instance_acl_dict = {(l.ac_role_id, p.id): l
                       for p, l in instance.access_control_list}
  person_ids = set()
  for role_id, data in content.get("access_control_list", {}).iteritems():
    person_ids |= {i["id"] for i in data["added"] + data["deleted"]}
  person_dict = {p.id: p for p in all_models.Person.query.filter(
      all_models.Person.id.in_(person_ids))
  }
  acr_dict = {r.id: r for r in ACR.get_ac_roles_for(instance.type).values()}
  for role_id, data in content.get("access_control_list", {}).iteritems():
    role_id = int(role_id)
    if role_id not in acr_dict:
      continue
    for add in data["added"]:
      if (role_id, add["id"]) not in instance_acl_dict:
        instance.add_person_with_role_id(person_dict[add["id"]], role_id)
        any_acl_applied = True
    for delete in data["deleted"]:
      if (role_id, delete["id"]) in instance_acl_dict:
        instance.acr_id_acl_map[role_id].remove_person(
            person_dict[delete["id"]]
        )
        any_acl_applied = True
  return any_acl_applied


def apply_cav(instance, content):
  """Apply CAVs."""
  any_cav_applied = False
  if not isinstance(instance, (mixins.CustomAttributable,
                               mixins.ExternalCustomAttributable)):
    return any_cav_applied
  cad_dict = {d.id: d for d in instance.custom_attribute_definitions}
  cav_dict = {i.custom_attribute_id: i
              for i in instance.custom_attribute_values}
  proposals = content.get("custom_attribute_values", {})
  for cad_id, value in proposals.iteritems():
    cad = cad_dict.get(int(cad_id))
    if not cad:
      # looks like CAD was removed
      continue
    if value["attribute_object"]:
      attribute_object_id = value["attribute_object"]["id"]
    else:
      attribute_object_id = None
    cav = cav_dict.get(cad.id)
    any_cav_applied = True
    if cav:
      cav.attribute_value = value["attribute_value"]
      cav.attribute_object_id = attribute_object_id
    else:
      if isinstance(instance, mixins.ExternalCustomAttributable):
        cav = all_models.ExternalCustomAttributeValue(
            custom_attribute=cad,
            attributable=instance,
            attribute_value=value["attribute_value"],
        )
      else:
        cav = all_models.CustomAttributeValue(
            custom_attribute=cad,
            attributable=instance,
            attribute_value=value["attribute_value"],
            attribute_object_id=attribute_object_id,
        )
      instance.custom_attribute_values.append(cav)
  return any_cav_applied


def _generate_mapping_field_cache(mapping_fields, mapping_list_field):
  """Returns field cache for sent mapings."""
  all_models_dict = {m.__name__: m for m in all_models.all_models}
  all_items = itertools.chain(*[itertools.chain(v['added'], v['deleted'])
                                for v in mapping_list_field.values()])
  all_items = itertools.chain(mapping_fields.values(), all_items)
  update_field = collections.defaultdict(list)
  for value in all_items:
    if value:
      update_field[all_models_dict[value["type"]]].append(value["id"])
  return {(i.type, i.id): i
          for m, ids in update_field.iteritems()
          for i in m.query.filter(m.id.in_(ids))}


def apply_mapping(instance, content):
  """Apply mappings."""
  any_mappings_applied = False
  rel_names = [r.key
               for r in inspect(instance.__class__).relationships
               if not r.uselist]
  mapping_fields = content.get("mapping_fields", {})
  mapping_list_field = content.get("mapping_list_fields", {})
  field_cache = _generate_mapping_field_cache(mapping_fields,
                                              mapping_list_field)
  for key, value in mapping_fields.iteritems():
    if key in rel_names:
      setattr(instance,
              key,
              field_cache.get((value["type"], value["id"])) if value else None)
      any_mappings_applied = True
  for key, value in mapping_list_field.iteritems():
    attr = getattr(instance, key)
    exist_items = {(i.type, i.id) for i in attr}
    for item in value["added"]:
      key = (item["type"], item["id"])
      if key in exist_items:
        continue
      attr.append(field_cache[key])
      any_mappings_applied = True
    for item in value["deleted"]:
      key = (item["type"], item["id"])
      if key not in exist_items:
        continue
      attr.remove(field_cache[key])
      any_mappings_applied = True
  return any_mappings_applied


def apply_fields(instance, content):
  """Apply field diff to instance."""
  any_fields_applied = False
  for field, value in content.get("fields", {}).iteritems():
    if hasattr(instance, field):
      setattr(instance, field, value)
      any_fields_applied = True
  return any_fields_applied


def apply_action(instance, content):
  """Apply content diff to instance."""
  applied_flags = [apply_fields(instance, content),
                   apply_acl(instance, content),
                   apply_cav(instance, content),
                   apply_mapping(instance, content)]
  return any(applied_flags)
