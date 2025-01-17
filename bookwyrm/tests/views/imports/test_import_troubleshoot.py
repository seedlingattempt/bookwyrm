""" test for app action functionality """
from unittest.mock import patch
from django.template.response import TemplateResponse
from django.test import TestCase
from django.test.client import RequestFactory
from bookwyrm.tests.validate_html import validate_html

from bookwyrm import models, views


class ImportTroubleshootViews(TestCase):
    """goodreads import views"""

    def setUp(self):
        """we need basic test data and mocks"""
        self.factory = RequestFactory()
        with patch("bookwyrm.suggested_users.rerank_suggestions_task.delay"), patch(
            "bookwyrm.activitystreams.populate_stream_task.delay"
        ):
            self.local_user = models.User.objects.create_user(
                "mouse@local.com",
                "mouse@mouse.mouse",
                "password",
                local=True,
                localname="mouse",
            )
        models.SiteSettings.objects.create()

    def test_import_troubleshoot_get(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.ImportTroubleshoot.as_view()
        import_job = models.ImportJob.objects.create(user=self.local_user, mappings={})
        request = self.factory.get("")
        request.user = self.local_user
        with patch("bookwyrm.tasks.app.AsyncResult") as async_result:
            async_result.return_value = []
            result = view(request, import_job.id)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_retry_import(self):
        """retry failed items"""
        view = views.ImportTroubleshoot.as_view()
        import_job = models.ImportJob.objects.create(
            user=self.local_user, privacy="unlisted", mappings={}
        )
        request = self.factory.post("")
        request.user = self.local_user

        with patch("bookwyrm.importers.Importer.start_import"):
            view(request, import_job.id)

        self.assertEqual(models.ImportJob.objects.count(), 2)
        retry_job = models.ImportJob.objects.last()

        self.assertTrue(retry_job.retry)
        self.assertEqual(retry_job.user, self.local_user)
        self.assertEqual(retry_job.privacy, "unlisted")
