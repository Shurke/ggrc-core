# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
# pylint: disable=missing-docstring,invalid-name

import json
from random import random

import ddt
import mock

import ggrc
from ggrc import db
from ggrc.app import app
from ggrc.models.person import Person

from integration.ggrc.models import factories
from integration.ggrc.views.saved_searches.base import SavedSearchBaseTest
from integration.ggrc.views.saved_searches.initializers import (
    setup_user_role,
    get_client_and_headers,
)


@ddt.ddt
class TestSavedSearchPost(SavedSearchBaseTest):
  """Tests for saved search POST view."""

  @classmethod
  def setUpClass(cls):
    """Set up read-only test data to test GET requests."""
    super(TestSavedSearchPost, cls).setUpClass()

    email_0 = "aniki_baniki_{}@test.com".format(random())
    with app.app_context():
      cls._person_0 = Person(name="Aniki", email=email_0)
      db.session.add(cls._person_0)
      db.session.flush()

      cls._user_role = setup_user_role(cls._person_0)
      db.session.commit()

      cls._client, cls._headers = get_client_and_headers(
          app, cls._person_0,
      )

  @classmethod
  def tearDownClass(cls):
    """Clean up created user and related saved searches."""
    super(TestSavedSearchPost, cls).tearDownClass()

    db.session.delete(cls._user_role)
    db.session.delete(cls._person_0)
    db.session.commit()

  def test_0_successful_creation_of_saved_search(self):
    """Test that saved search could be created."""
    response = self._client.post(
        "/api/saved_searches",
        data=json.dumps({
            "name": "test_ss_3",
            "object_type": "Assessment",
            "search_type": "AdvancedSearch"
        }),
        headers=self._headers,
    )

    self.assertEqual(response.status, "200 OK")

    response = self._client.get(
        "/api/saved_searches/AdvancedSearch?limit=1&object_type=Assessment",
        headers=self._headers,
    )

    data = json.loads(response.data)

    self.assertEqual(len(data["values"]), 1)
    self.assertEqual(data["values"][0]["name"], "test_ss_3")

  @ddt.data(
      "Workflow",
      "TaskGroup",
      "TaskGroupTask",
      "CycleTaskGroupObjectTask"
  )
  def test_0_successful_creation_of_saved_search_non_contributed_models(
      self, object_type
  ):
    """Test that saved search could be created for non contributed models."""
    response = self._client.post(
        "/api/saved_searches",
        data=json.dumps({
            "name": "test_ss_3",
            "object_type": object_type,
            "search_type": "AdvancedSearch"
        }),
        headers=self._headers,
    )

    self.assertEqual(response.status, "200 OK")

    response = self._client.get(
        "/api/saved_searches/AdvancedSearch?limit=1&object_type={0}".format(
            object_type
        ),
        headers=self._headers,
    )

    data = json.loads(response.data)

    self.assertEqual(len(data["values"]), 1)
    self.assertEqual(data["values"][0]["name"], "test_ss_3")

  def test_1_saved_search_creation_failure_due_not_unique_name(self):
    """Test saved search creation failure if provided name is alredy taken."""
    data = self._post_saved_search({
        "name": "test_ss_3",
        "object_type": "Assessment",
        "search_type": "AdvancedSearch"
    })

    self.assertEqual(
        data["message"],
        u"Advanced Saved search for Assessment with "
        u"name 'test_ss_3' already exists",
    )
    self.assertEqual(data["code"], 400)

  def test_global_search_unique_names(self):
    """Test that we unable to save GlobalSearch with already existing name."""
    self._post_saved_search({
        "name": "test_ss_3",
        "object_type": "Assessment",
        "search_type": "GlobalSearch"
    })
    glob2 = self._post_saved_search({
        "name": "test_ss_3",
        "object_type": "Assessment",
        "search_type": "GlobalSearch"
    })

    self.assertEqual(
        glob2["message"],
        u"Global Saved search with name 'test_ss_3' already exists",
    )
    self.assertEqual(glob2["code"], 400)

  def test_2_saved_search_creation_failure_due_to_empty_name(self):
    """Test saved search creation failure if provided name is empty."""
    data = self._post_saved_search({
        "name": "",
        "object_type": "Assessment",
        "search_type": "AdvancedSearch"
    })

    self.assertEqual(data["message"], "Saved search name can't be blank")
    self.assertEqual(data["code"], 400)

  def test_saved_search_creation_empty_name_pass_if_invisible(self):
    """Test invisible saved search creation with empty name pass."""
    saved_search = self._post_saved_search({
        "name": "",
        "object_type": "Assessment",
        "search_type": "AdvancedSearch",
        "is_visible": False,

    })

    self.assertTrue(saved_search["name"])
    self.assertFalse(saved_search["is_visible"])

  def test_3_saved_search_creation_failure_due_invalid_object_type(self):
    """Test saved search creation failure with invalid object_type."""
    data = self._post_saved_search({
        "name": "test_ss_1",
        "object_type": "Overwatch",
        "search_type": "AdvancedSearch"
    })

    self.assertEqual(
        data["message"],
        u"Object of type 'Overwatch' does not support search saving",
    )
    self.assertEqual(data["code"], 400)

  def test_4_successful_creation_of_saved_search_with_filters(self):
    """Test that we able to write and read values to filters field."""
    _filter = {"expression":
               {"left":
                {"left": "Title",
                 "op": {"name": "~"},
                 "right": "one"
                 },
                "op": {"name": "AND"},
                "right": {"left": "Status",
                          "op": {"name": "IN"},
                          "right": ["Active", "Draft", "Deprecated"]
                          }
                }
               }
    response = self._client.post(
        "/api/saved_searches",
        data=json.dumps({
            "name": "test_ss_4",
            "object_type": "Assessment",
            "filters": _filter,
            "search_type": "GlobalSearch"
        }),
        headers=self._headers,
    )

    self.assertEqual(response.status, "200 OK")

    data = self._get_saved_search("Assessment")

    for saved_search in data["values"]:
      if saved_search["name"] == "test_ss_4":
        self.assertEqual(json.loads(saved_search["filters"]), _filter)

  def test_5_saved_search_creation_failure_due_invalid_type(self):
    """Test saved search creation failure with invalud search_type."""
    data = self._post_saved_search({
        "name": "test_ss_1",
        "object_type": "Assessment",
        "search_type": "Invalid Type"
    })

    self.assertEqual(
        data["message"],
        u"Invalid saved search type",
    )
    self.assertEqual(data["code"], 400)

  def test_create_saved_searches(self):
    """Test creating invisible saved search"""
    with factories.single_commit():
      user = factories.PersonFactory()

    data = [
        [u'Object type'],
        [u'Program', u'Code*', u'Title*'],
        [u'', u'PROGRAM-1', u'test1'],
        [u'', u'PROGRAM-2', u'test2'],
        [u'Object type'],
        [u'Audit', u'Code*', u'Title*'],
        [u'', u'AUDIT-1', u'2019: test1 - Audit 1'],
        [u'', u'AUDIT-2', u'2019: test1 - Audit 2'],
        [u'', u'AUDIT-3', u'2019: test1 - Audit 3'],
        [u'', u'AUDIT-4', u'2019: test2 - Audit 1'],
        [u'Object type'],
        [u'Assessment', u'Code*', u'Title*'],
        [u'', u'ASSESSMENT-1', u'asmt_test1'],
        [u'', u'ASSESSMENT-2', u'asmt_test2'],
        [u'', u'ASSESSMENT-3', u'asmt_test2_1'],
    ]
    # pylint: disable=protected-access
    with mock.patch(
        'ggrc.views.converters._create_saved_searches',
        side_effect=ggrc.views.converters._create_saved_searches
    ) as mocked:
      mocked(data, user)
      mocked.assert_called_with(data, user)
