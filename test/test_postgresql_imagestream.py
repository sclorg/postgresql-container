import os
import sys

import pytest

from container_ci_suite.openshift import OpenShiftAPI
from container_ci_suite.utils import check_variables

if not check_variables():
    print("At least one variable from IMAGE_NAME, OS, SINGLE_VERSION is missing.")
    sys.exit(1)


VERSION = os.getenv("SINGLE_VERSION")
IMAGE_NAME = os.getenv("IMAGE_NAME")
OS = os.getenv("TARGET")
TAGS = {
    "rhel8": "-el8",
    "rhel9": "-el9"
}
TAG = TAGS.get(OS, None)


class TestPostgreSQLImagestreamTemplate:

    def setup_method(self):
        self.oc_api = OpenShiftAPI(pod_name_prefix="postgresql", version=VERSION)

    def teardown_method(self):
        self.oc_api.delete_project()

    @pytest.mark.parametrize(
        "template",
        [
            "postgresql-ephemeral-template.json",
            "postgresql-persistent-template.json"
        ]
    )
    def test_psql_imagestream_template(self, template):
        os_name = ''.join(i for i in OS if not i.isdigit())
        print(os.getcwd())
        assert self.oc_api.deploy_image_stream_template(
            imagestream_file=f"imagestreams/postgresql-{os_name}.json",
            template_file=f"examples/{template}",
            app_name=self.oc_api.pod_name_prefix,
            openshift_args=[
                f"POSTGRESQL__VERSION={VERSION}{TAG}"
            ]
        )
        assert self.oc_api.is_pod_running(pod_name_prefix=self.oc_api.pod_name_prefix)
