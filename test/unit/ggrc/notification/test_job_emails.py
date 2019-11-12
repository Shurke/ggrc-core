# -*- coding: utf-8 -*-

# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Tests for the ggrc.notifications.job_emails module."""

import unittest
from mock import patch

import ddt

import ggrc
from ggrc import settings
from ggrc.app import app
from ggrc.notifications.job_emails import send_email


@ddt.ddt
class TestJobEmails(unittest.TestCase):
  """Tests for checking notification when export"""

  @classmethod
  def setUpClass(cls):
    cls.template = {
        "title": "title",
        "body": "body",
        "url": "export"
    }
    cls.user_email = "user@example.com"
    cls.subject = "title"

  @ddt.data(
      (42, "http://test/export#!&job_id=42"),
      (561, "http://test/export#!&job_id=561"),
      (None, "http://test/export")
  )
  @ddt.unpack
  def test_url_in_notification(self, ie_id, url):
    """Test for checking url in notification when exporting"""

    with patch("ggrc.notifications.common.send_email") as common_send_email:
      data = {
          "body": self.template["body"],
          "title": self.template["title"],
          "url": url
      }
      body = settings.EMAIL_IMPORT_EXPORT.render(
          import_export=data
      )
      with app.test_request_context(base_url="http://test"):
        send_email(self.template, self.user_email, "", ie_id)
      common_send_email.assert_called_with(
          self.user_email, self.subject, body
      )

  def test_prepare_url_import_obj(self):
    """Test url making for saved searches"""
    data = {
        '3 Assessment': 'objectBrowser#!assessment&saved_search=5',
        '4 Audit': 'objectBrowser#!audit&saved_search=4',
        '2 Program': 'objectBrowser#!program&saved_search=6'
    }
    expected_result = {
        '2 Program': u'http://test/objectBrowser#!program&saved_search=6',
        '4 Audit': u'http://test/objectBrowser#!audit&saved_search=4',
        '3 Assessment': u'http://test/objectBrowser#!assessment&saved_search=5'
    }
    # pylint: disable=protected-access
    with app.test_request_context(base_url='http://test'):
      result = ggrc.notifications.job_emails._prepare_url_import_obj(data)
      self.assertEquals(result, expected_result)

  def test_send_email(self):
    """Test for checking url in notification when importing"""
    payload = {
        '2 Program': u'http://test/objectBrowser#!program&saved_search=6',
        '4 Audit': u'http://test/objectBrowser#!audit&saved_search=4',
        '3 Assessment': u'http://test/objectBrowser#!assessment&saved_search=5'
    }
    template = {
        "title": "title",
        "body": "body",
        "url": u"http://test/import"
    }
    user_email = "user@example.com"
    subject = "title"
    with patch("ggrc.notifications.common.send_email") as common_send_email:
      data = {
          "body": template["body"],
          "title": template["title"],
          "url": template["url"],
          "payload": payload
      }
      body = settings.EMAIL_IMPORT_EXPORT.render(import_export=data)
      with app.test_request_context(base_url="http://test"):
        send_email(
            template, user_email, filename="", ie_id=None, payload=payload
        )
      common_send_email.assert_called_with(user_email, subject, body)
