# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

# pylint: disable=maybe-no-member, invalid-name

"""Test Risk export."""
from ggrc.models import all_models
from integration.external_app import external_api_helper
from integration.ggrc.models import factories
from integration.ggrc import TestCase
from integration.ggrc import query_helper


class TestExportRisk(query_helper.WithQueryApi, TestCase):
  """Basic Risk export tests."""

  def setUp(self):
    super(TestExportRisk, self).setUp()
    self.ext_api = external_api_helper.ExternalApiClient()
    self.client.get("/login")

  @staticmethod
  def build_full_risk_payload():
    """Build risk payload with full attributes and GCA's"""
    with factories.single_commit():
      cad_text_id = factories.ExternalCustomAttributeDefinitionFactory(
          title="text_GCA",
          definition_type="risk",
          attribute_type="Text",
      ).id
      cad_rich_text_id = factories.ExternalCustomAttributeDefinitionFactory(
          title="rich_text_GCA",
          definition_type="risk",
          attribute_type="Rich Text",
      ).id
      cad_date_id = factories.ExternalCustomAttributeDefinitionFactory(
          title="date_GCA",
          definition_type="risk",
          attribute_type="Date",
      ).id

      cad_multiselect_id = factories.ExternalCustomAttributeDefinitionFactory(
          title="multiselect_GCA",
          definition_type="risk",
          attribute_type="Multiselect",
          multi_choice_options="yes,no"
      ).id

      cad_dropdown_id = factories.ExternalCustomAttributeDefinitionFactory(
          title="dropdown_GCA",
          definition_type="risk",
          attribute_type="Dropdown",
          multi_choice_options="one,two,three,four,five"
      ).id

    return {
        "risk": {
            "custom_attribute_values": [
                {
                    "custom_attribute_id": cad_text_id,
                    "attributable_type": "Risk",
                    "attribute_value": "text_GCA_value",
                },
                {
                    "custom_attribute_id": cad_rich_text_id,
                    "attributable_type": "Risk",
                    "attribute_value": "rich_text_GCA_value",
                },
                {
                    "custom_attribute_id": cad_date_id,
                    "attributable_type": "Risk",
                    "attribute_value": "2019-12-13",
                },
                {
                    "custom_attribute_id": cad_multiselect_id,
                    "attributable_type": "Risk",
                    "attribute_value": "no",
                },
                {
                    "custom_attribute_id": cad_dropdown_id,
                    "attributable_type": "Risk",
                    "attribute_value": "three",
                },
            ],
            "last_verified_at": "2019-06-13T11:31:17",
            "review_status": "review_needed",
            "updated_at": "2019-06-14T09:38:50",
            "risk_type": "any risk type UPDATED",
            "title": "vi risk restored upd 1",
            "created_by": {
                "id": factories.PersonFactory().id,
            },
            "last_submitted_by": {
                "id": factories.PersonFactory().id,
            },
            "folder": "xxx",
            "external_slug": "RISK-141",
            "start_date": "2019-04-30",
            "status": "Draft",
            "due_date": "2019-06-01",
            "description": "any description upd 1",
            "end_date": "2019-04-30",
            "workflow_state": "some state",
            "threat_event": "any treat event",
            "review_status_display_name": "Review Needed",
            "threat_source": "any treat source NEW",
            "type": "Risk",
            "notes": "any notes NEW",
            "vulnerability": "vulnerability UPDATED",
            "last_submitted_at": "2019-06-13T11:31:13",
            "test_plan": "asmt proc NEW",
            "last_verified_by": {
                "id": factories.PersonFactory().id,
            },
            "context": None,
            "external_id": 325436,
            "created_at": "2019-04-30T09:21:11",
        }
    }

  @staticmethod
  def assert_attributes_filled(data, ignore=None):
    """Check that all attributes filled with values"""
    if ignore is None:
      ignore = set()

    for key, value in data.iteritems():
      if key not in ignore and not value:
        raise ValueError("Attribute {}:{} is empty".format(key, data[key]))

  def test_risk_all_attrs_export(self):
    """Risk with all filled attributes should be exportable"""
    response = self.ext_api.post(
        all_models.Risk, data=self.build_full_risk_payload()
    )
    self.assert201(response)
    self.assert_attributes_filled(
        response.json["risk"],
        ignore=(
            "access_control_list", "context", "custom_attribute_definitions",
            "end_date", "workflow_state", "preconditions_failed"
        )
    )

    export_query = self._make_query_dict(
        "Risk",
        expression=[
            "code",
            "=",
            response.json["risk"]["slug"],
        ],
        fields="all",
    )

    response = self.export_csv([export_query])
    self.assertIn("any treat source NEW", response.data)
    self.assertIn("any description upd 1", response.data)
