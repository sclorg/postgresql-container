import pytest

from container_ci_suite.openshift import OpenShiftAPI

from conftest import VARS


class TestPostgreSQLDeployTemplate:
    def setup_method(self):
        self.oc_api = OpenShiftAPI(
            pod_name_prefix="postgresql-testing",
            version=VARS.VERSION,
            shared_cluster=True,
        )

    def teardown_method(self):
        self.oc_api.delete_project()

    @pytest.mark.parametrize(
        "template",
        ["postgresql-ephemeral-template.json", "postgresql-persistent-template.json"],
    )
    def test_psql_template_inside_cluster(self, template):
        short_version = VARS.VERSION.replace(".", "")
        assert self.oc_api.deploy_template_with_image(
            image_name=VARS.IMAGE_NAME,
            template=f"examples/{template}",
            name_in_template="postgresql",
            openshift_args=[
                f"POSTGRESQL_VERSION={VARS.VERSION}",
                f"DATABASE_SERVICE_NAME={self.oc_api.pod_name_prefix}",
                "POSTGRESQL_USER=testu",
                "POSTGRESQL_PASSWORD=testp",
                "POSTGRESQL_DATABASE=testdb",
            ],
        )

        assert self.oc_api.is_pod_running(pod_name_prefix=self.oc_api.pod_name_prefix)
        assert self.oc_api.check_command_internal(
            image_name=f"registry.redhat.io/{VARS.OS}/postgresql-{short_version}",
            service_name=self.oc_api.pod_name_prefix,
            cmd="PGPASSWORD=testp pg_isready -t 15 -h <IP> -U testu -d testdb",
            expected_output="accepting connections",
        )
