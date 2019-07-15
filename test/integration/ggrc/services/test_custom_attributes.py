# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
"""Tests for PUT and POST requests for objects with custom attributes

These tests include:
- Creating an object with custom attributes (POST request).
- Editing existing custom attributes on an object.
- Adding custom attributes to existing object.

"""

import ddt

from ggrc import utils
from ggrc import models
from ggrc import builder
from ggrc.models import all_models
from ggrc.models.mixins import customattributable

from integration.ggrc.api_helper import Api
from integration.ggrc.services import TestCase
from integration.ggrc.generator import ObjectGenerator
from integration.ggrc.models import factories


class ProductTestCase(TestCase):
  """Test case for Product post and put requests."""

  def setUp(self):
    super(ProductTestCase, self).setUp()
    self.generator = ObjectGenerator()
    self.client.get("/login")

  def _put(self, url, data, extra_headers=None):
    """Perform a put request."""
    headers = {'X-Requested-By': 'Unit Tests'}
    headers.update(extra_headers)
    return self.client.put(
        url,
        content_type='application/json',
        data=utils.as_json(data),
        headers=headers,
    )

  def _post(self, data):
    """Perform a post request."""
    return self.client.post(
        "/api/products",
        content_type='application/json',
        data=utils.as_json(data),
        headers={'X-Requested-By': 'Unit Tests'},
    )


@ddt.ddt
class TestGlobalCustomAttributes(ProductTestCase):
  """Tests for API updates for custom attribute values."""

  def test_custom_attribute_post(self):
    """Test post object with custom attributes."""
    gen = self.generator.generate_custom_attribute
    _, cad = gen("product", attribute_type="Text", title="normal text")
    pid = models.Person.query.first().id

    product_data = [{
        "product": {
            "kind": None,
            "owners": [],
            "custom_attribute_values": [{
                "attribute_value": "my custom attribute value",
                "custom_attribute_id": cad.id,
            }],
            "contact": {
                "id": pid,
                "href": "/api/people/{}".format(pid),
                "type": "Person"
            },
            "title": "simple product",
            "description": "",
            "secondary_contact": None,
            "notes": "",
            "url": "",
            "documents_reference_url": "",
            "slug": "",
            "context": None,
        },
    }]

    response = self._post(product_data)
    ca_json = response.json[0][1]["product"]["custom_attribute_values"][0]
    self.assertIn("attributable_id", ca_json)
    self.assertIn("attributable_type", ca_json)
    self.assertIn("attribute_value", ca_json)
    self.assertIn("id", ca_json)
    self.assertEqual(ca_json["attribute_value"], "my custom attribute value")

    product = models.Product.eager_query().first()
    self.assertEqual(len(product.custom_attribute_values), 1)
    self.assertEqual(product.custom_attribute_values[0].attribute_value,
                     "my custom attribute value")

  @ddt.data(
      ("objective", "Objective title")
  )
  @ddt.unpack
  def test_create_from_ggrcq(self, definition_type, title):
    """Test create definition only for GGRCQ."""
    api = Api()
    payload = [
        {
            "custom_attribute_definition": {
                "attribute_type": "Text",
                "context": {"id": None},
                "definition_type": definition_type,
                "helptext": "",
                "mandatory": False,
                "modal_title": "Title",
                "placeholder": "",
                "title": title
            }
        }
    ]

    with api.as_external():
      response = api.post(all_models.CustomAttributeDefinition, payload)
      self.assertEqual(response.status_code, 200)

  @ddt.data(
      ("control", "Control title")
  )
  @ddt.unpack
  def test_create_from_ggrc(self, definition_type, title):
    """Test create definition not allowed for GGRC."""
    api = Api()
    payload = [
        {
            "custom_attribute_definition": {
                "attribute_type": "Text",
                "context": {"id": None},
                "definition_type": definition_type,
                "helptext": "Some text",
                "mandatory": False,
                "modal_title": "Modal title",
                "placeholder": "Placeholder",
                "title": title
            }
        }
    ]
    response = api.post(all_models.CustomAttributeDefinition, payload)
    self.assertEqual(response.status_code, 405)

  def test_custom_attribute_put_add(self):
    """Test edits with adding new CA values."""
    gen = self.generator.generate_custom_attribute
    _, cad = gen("product", attribute_type="Text", title="normal text")
    pid = models.Person.query.first().id

    product_data = [{
        "product": {
            "kind": None,
            "owners": [],
            "contact": {
                "id": pid,
                "href": "/api/people/{}".format(pid),
                "type": "Person"
            },
            "title": "simple product",
            "description": "",
            "secondary_contact": None,
            "notes": "",
            "url": "",
            "documents_reference_url": "",
            "slug": "",
            "context": None,
        },
    }]

    response = self._post(product_data)
    product_url = response.json[0][1]["product"]["selfLink"]
    headers = self.client.get(product_url).headers

    product_data[0]["product"]["custom_attribute_values"] = [{
        "attribute_value":
        "added value",
        "custom_attribute_id":
        cad.id,
    }]

    response = self._put(
        product_url,
        product_data[0],
        extra_headers={
            'If-Unmodified-Since': headers["Last-Modified"],
            'If-Match': headers["Etag"],
        })

    product = response.json["product"]

    self.assertEqual(len(product["custom_attribute_values"]), 1)
    ca_json = product["custom_attribute_values"][0]
    self.assertIn("attributable_id", ca_json)
    self.assertIn("attributable_type", ca_json)
    self.assertIn("attribute_value", ca_json)
    self.assertIn("id", ca_json)
    self.assertEqual(ca_json["attribute_value"], "added value")

    product = models.Product.eager_query().first()
    self.assertEqual(len(product.custom_attribute_values), 1)
    self.assertEqual(product.custom_attribute_values[0].attribute_value,
                     "added value")

    headers = self.client.get(product_url).headers

    product_data[0]["product"]["custom_attribute_values"] = [{
        "attribute_value":
        "edited value",
        "custom_attribute_id":
        cad.id,
    }]

    response = self._put(
        product_url,
        product_data[0],
        extra_headers={
            'If-Unmodified-Since': headers["Last-Modified"],
            'If-Match': headers["Etag"],
        })

    product = response.json["product"]
    ca_json = product["custom_attribute_values"][0]
    self.assertIn("attributable_id", ca_json)
    self.assertIn("attributable_type", ca_json)
    self.assertIn("attribute_value", ca_json)
    self.assertIn("id", ca_json)
    self.assertEqual(ca_json["attribute_value"], "edited value")

  def test_custom_attribute_get(self):
    """Check if get returns the whole CA value and not just the stub."""
    gen = self.generator.generate_custom_attribute
    _, cad = gen("product", attribute_type="Text", title="normal text")
    pid = models.Person.query.first().id

    product_data = [{
        "product": {
            "kind": None,
            "owners": [],
            "custom_attribute_values": [{
                "attribute_value": "my custom attribute value",
                "custom_attribute_id": cad.id,
            }],
            "contact": {
                "id": pid,
                "href": "/api/people/{}".format(pid),
                "type": "Person",
            },
            "title": "simple product",
            "description": "",
            "secondary_contact": None,
            "notes": "",
            "url": "",
            "documents_reference_url": "",
            "slug": "",
            "context": None,
        },
    }]

    response = self._post(product_data)
    product_url = response.json[0][1]["product"]["selfLink"]
    get_response = self.client.get(product_url)
    product = get_response.json["product"]
    self.assertIn("custom_attribute_values", product)
    self.assertEqual(len(product["custom_attribute_values"]), 1)
    cav = product["custom_attribute_values"][0]
    self.assertIn("custom_attribute_id", cav)
    self.assertIn("attribute_value", cav)
    self.assertIn("id", cav)

  @ddt.data(
      (" abc ", "abc"),
      ("    abc  abc ", "abc abc"),
      ("abc", "abc"),
      ("", ""),
  )
  @ddt.unpack
  def test_cad_title_strip(self, title, validated_title):
    """Test CAD title strip on validation."""
    with factories.single_commit():
      cad = factories.CustomAttributeDefinitionFactory(
          definition_type="control",
          attribute_type=all_models.CustomAttributeDefinition.ValidTypes.TEXT,
          title=title,
      )
    cad_resp = self.generator.api.get(cad, cad.id)
    self.assert200(cad_resp)
    self.assertEquals(cad_resp.json['custom_attribute_definition']['title'],
                      validated_title)

  def test_cad_title_strip_unique(self):
    """Test CAD title stripped should be unique."""
    factories.CustomAttributeDefinitionFactory(
        definition_type="objective",
        attribute_type=all_models.CustomAttributeDefinition.ValidTypes.TEXT,
        title="abc",
    )
    with self.assertRaises(ValueError):
      factories.CustomAttributeDefinitionFactory(
          definition_type="objective",
          attribute_type=all_models.CustomAttributeDefinition.ValidTypes.TEXT,
          title=" abc ",
      )

  @ddt.data(
      (all_models.CustomAttributeDefinition.ValidTypes.TEXT, ""),
      (all_models.CustomAttributeDefinition.ValidTypes.RICH_TEXT, ""),
      (all_models.CustomAttributeDefinition.ValidTypes.DROPDOWN, ""),
      (all_models.CustomAttributeDefinition.ValidTypes.CHECKBOX, "0"),
      (all_models.CustomAttributeDefinition.ValidTypes.DATE, ""),
  )
  @ddt.unpack
  def test_get_cad_default(self, cad_type, default_value):
    """Check default_value for cad via object and direct cad api."""
    with factories.single_commit():
      objective = factories.ObjectiveFactory()
      cad = factories.CustomAttributeDefinitionFactory(
          definition_type="objective",
          attribute_type=cad_type,
      )
    cad_id = cad.id
    objective_id = objective.id
    objective_resp = self.generator.api.get(objective, objective_id)
    cad_resp = self.generator.api.get(cad, cad_id)
    self.assert200(cad_resp)
    self.assert200(objective_resp)
    self.assertIn("custom_attribute_definitions",
                  objective_resp.json["objective"])
    _cads = objective_resp.json["objective"]["custom_attribute_definitions"]
    self.assertEqual(1, len(_cads))
    cad_json = _cads[0]
    self.assertEqual(cad_id, cad_json["id"])
    self.assertIn("default_value", cad_json)
    self.assertEqual(default_value, cad_json["default_value"])
    self.assertIn("custom_attribute_definition", cad_resp.json)
    self.assertIn("default_value",
                  cad_resp.json["custom_attribute_definition"])
    self.assertEqual(
        default_value,
        cad_resp.json["custom_attribute_definition"]["default_value"])

  @ddt.data((True, "1"), (True, "true"), (True, "TRUE"), (False, "0"),
            (False, "false"), (False, "FALSE"))
  @ddt.unpack
  def test_filter_by_mandatory(self, flag_value, filter_value):
    """Filter CADs by mandatory flag if it's {0} and filter_value is {1}."""
    with factories.single_commit():
      cads = {
          f: factories.CustomAttributeDefinitionFactory(
              mandatory=f, definition_type="control")
          for f in [True, False]
      }
    resp = self.generator.api.get_query(
        all_models.CustomAttributeDefinition,
        "ids={}&mandatory={}".format(",".join(
            [str(c.id) for c in cads.values()]), filter_value),
    )
    self.assert200(resp)
    cad_collection = resp.json["custom_attribute_definitions_collection"]
    resp_cad_ids = [
        i["id"] for i in cad_collection["custom_attribute_definitions"]
    ]
    self.assertEqual([cads[flag_value].id], resp_cad_ids)

  CAD_MODELS = [
      m for m in all_models.all_models
      if issubclass(m, customattributable.CustomAttributable)
  ]

  @ddt.data(*CAD_MODELS)
  def test_filter_by_definition_type(self, definition_model):
    """Filter {0.__name__} CADs by definition_type."""

    with factories.single_commit():
      cads = {
          model: factories.CustomAttributeDefinitionFactory(
              definition_type=model._inflector.table_singular)
          for model in self.CAD_MODELS
      }
    filter_params = "ids={}&definition_type={}".format(
        ",".join([str(c.id) for c in cads.values()]),
        definition_model._inflector.table_singular,
    )
    resp = self.generator.api.get_query(all_models.CustomAttributeDefinition,
                                        filter_params)
    self.assert200(resp)
    cad_collection = resp.json["custom_attribute_definitions_collection"]
    resp_cad_ids = [
        i["id"] for i in cad_collection["custom_attribute_definitions"]
    ]
    self.assertEqual([cads[definition_model].id], resp_cad_ids)


class TestOldApiCompatibility(ProductTestCase):
  """Test Legacy CA values API.

  These tests check that the old way of setting custom attribute values still
  works and that If both ways are used, the legacy code is ignored.
  """

  def test_custom_attribute_post_both(self):
    """Test post with both custom attribute api options.

    This tests tries to set a custom attribute on the new and the old way at
    once. The old option should be ignored and the new value should be set.
    """
    gen = self.generator.generate_custom_attribute
    _, cad = gen("product", attribute_type="Text", title="normal text")
    cad_json = builder.json.publish(cad.__class__.query.get(cad.id))
    cad_json = builder.json.publish_representation(cad_json)
    pid = models.Person.query.first().id

    product_data = [{
        "product": {
            "kind": None,
            "owners": [],
            "custom_attribute_definitions":[
                cad_json,
            ],
            "custom_attribute_values": [{
                "attribute_value": "new value",
                "custom_attribute_id": cad.id,
            }],
            "custom_attributes": {
                cad.id: "old value",
            },
            "contact": {
                "id": pid,
                "href": "/api/people/{}".format(pid),
                "type": "Person"
            },
            "title": "simple product",
            "description": "",
            "secondary_contact": None,
            "notes": "",
            "url": "",
            "documents_reference_url": "",
            "slug": "",
            "context": None
        },
    }]

    response = self._post(product_data)
    ca_json = response.json[0][1]["product"]["custom_attribute_values"][0]
    self.assertEqual(ca_json["attribute_value"], "new value")

    product = models.Product.eager_query().first()
    self.assertEqual(len(product.custom_attribute_values), 1)
    self.assertEqual(product.custom_attribute_values[0].attribute_value,
                     "new value")

  def test_custom_attribute_post_old(self):
    """Test post with old style custom attribute values.

    This tests that the legacy way of setting custom attribute values still
    works.
    """
    gen = self.generator.generate_custom_attribute
    _, cad = gen("product", attribute_type="Text", title="normal text")
    cad_json = builder.json.publish(cad.__class__.query.get(cad.id))
    cad_json = builder.json.publish_representation(cad_json)
    pid = models.Person.query.first().id

    product_data = [{
        "product": {
            "kind": None,
            "owners": [],
            "custom_attribute_definitions":[
                cad_json,
            ],
            "custom_attribute_values": [{
                "id": 1,
                "href": "/api/custom_attribute_values/1",
                "type": "CustomAttributeValues",
            }],
            "custom_attributes": {
                cad.id: "old value",
            },
            "contact": {
                "id": pid,
                "href": "/api/people/{}".format(pid),
                "type": "Person",
            },
            "title": "simple product",
            "description": "",
            "secondary_contact": None,
            "notes": "",
            "url": "",
            "documents_reference_url": "",
            "slug": "",
            "context": None,
        },
    }]

    response = self._post(product_data)
    self.assert200(response)
    ca_json = response.json[0][1]["product"]["custom_attribute_values"][0]
    self.assertEqual(ca_json["attribute_value"], "old value")

    product = models.Product.eager_query().first()
    self.assertEqual(len(product.custom_attribute_values), 1)
    self.assertEqual(product.custom_attribute_values[0].attribute_value,
                     "old value")
