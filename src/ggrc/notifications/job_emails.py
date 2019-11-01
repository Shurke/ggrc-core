# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>


"""  Import/Export notifications """

from urlparse import urljoin

from ggrc import settings
from ggrc import utils
from ggrc.notifications import common

IMPORT_COMPLETED = {
    "title": u"{filename} was imported successfully",
    "body": u"Go to import page to check details or submit new import "
            u"request.",
    "url": u"import"
}

IMPORT_BLOCKED = {
    "title": u"Could not import {filename} due to warnings",
    "body": u"Go to import page to check details or submit new import "
            u"request.",
    "url": u"import"
}

IMPORT_FAILED = {
    "title": u"[WARNING] Could not import {filename} due to errors",
    "body": u"Your Import job failed due to a server error. Please "
            u"retry import/export.",
    "url": u"import"
}

IMPORT_STOPPED = {
    "title": (u"[WARNING] Import of {filename} was stopped"),
    "body": u"The import was stopped. Only partial data was saved.",
    "url": u"import"
}

EXPORT_COMPLETED = {
    "title": u"{filename} was exported successfully",
    "body": u"Go to export page to download the result. "
            u"If the file generated for this export request "
            u"has been downloaded, you can ignore the email.",
    "url": u"export"
}

EXPORT_CRASHED = {
    "title": (u"[WARNING] Your GGRC export request did not finish due "
              u"to errors"),
    "body": u"Your Export job failed due to a server error. Please "
            u"restart the export again. Sorry for the inconveniences.",
    "url": u"export"
}

EXPORT_CRASHED_TOO_MANY_ITEMS = {
    "title": (u"[WARNING] Your GGRC export request did not finish due "
              u"to errors"),
    "body": u"Too many items. The export cannot be processed. "
            u"Please contact our support team.",
    "url": u"export"
}


def _prepare_url_import_obj(payload):
  """Create full url to saved search".

  Create saved search to insert into import notification email.

  Args:
    payload: dictionary, keys - description imported object (quantity and name
    of type of imported object), items - short url for saved search.

  Returns:
    dictionary, keys - description imported object (quantity and name of type
    of imported object), items - full url for saved search.
  """
  for description in payload:
    payload[description] = urljoin(utils.get_url_root(), payload[description])
  return payload


def send_email(template, send_to, filename="", ie_id=None, payload=None):
  """Send email"""
  subject = template["title"].format(filename=filename)
  if payload:
    payload = _prepare_url_import_obj(payload)
  url = urljoin(utils.get_url_root(), template["url"])
  if ie_id is not None:
    url = "{}#!&job_id={}".format(url, str(ie_id))

  data = {
      "body": template["body"],
      "payload": payload,
      "url": url,
      "title": subject
  }
  body = settings.EMAIL_IMPORT_EXPORT.render(import_export=data)
  common.send_email(send_to, subject, body)
