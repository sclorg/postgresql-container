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


class TestPostgreSQLDeployTemplate:

    def setup_method(self):
        self.oc_api = OpenShiftAPI(pod_name_prefix="postgresql-testing", version=VERSION)

    def teardown_method(self):
        self.oc_api.delete_project()

    @pytest.mark.parametrize(
        "template",
        [
            "postgresql-ephemeral-template.json",
            "postgresql-persistent-template.json"
        ]
    )
    def test_psql_template_inside_cluster(self, template):
        short_version = VERSION.replace(".", "")
        assert self.oc_api.deploy_template_with_image(
            image_name=IMAGE_NAME,
            template=f"examples/{template}",
            name_in_template="postgresql",
            openshift_args=[
                f"POSTGRESQL_VERSION={VERSION}{TAG}",
                f"DATABASE_SERVICE_NAME={self.oc_api.pod_name_prefix}",
                f"POSTGRESQL_USER=testu",
                f"POSTGRESQL_PASSWORD=testp",
                f"POSTGRESQL_DATABASE=testdb"
            ]
        )

        assert self.oc_api.is_pod_running(pod_name_prefix=self.oc_api.pod_name_prefix)
        assert self.oc_api.check_command_internal(
            image_name=f"registry.redhat.io/{OS}/postgresql-{short_version}",
            service_name=self.oc_api.pod_name_prefix,
            cmd="PGPASSWORD=testp pg_isready -t 15 -h <IP> -U testu -d testdb",
            expected_output="accepting connections"
        )
