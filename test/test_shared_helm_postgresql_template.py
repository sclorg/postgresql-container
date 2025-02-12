import os
import sys

import pytest

from pathlib import Path

from container_ci_suite.helm import HelmChartsAPI
from container_ci_suite.utils import check_variables

if not check_variables():
    print("At least one variable from IMAGE_NAME, OS, VERSION is missing.")
    sys.exit(1)

test_dir = Path(os.path.abspath(os.path.dirname(__file__)))


VERSION = os.getenv("VERSION")
IMAGE_NAME = os.getenv("IMAGE_NAME")
OS = os.getenv("TARGET")

TAGS = {
    "rhel8": "-el8",
    "rhel9": "-el9"
}
TAG = TAGS.get(OS, None)


class TestHelmPostgresqlPersistent:

    def setup_method(self):
        package_name = "redhat-postgresql-persistent"
        path = test_dir
        self.hc_api = HelmChartsAPI(path=path, package_name=package_name, tarball_dir=test_dir)
        self.hc_api.clone_helm_chart_repo(
            repo_url="https://github.com/sclorg/helm-charts", repo_name="helm-charts",
            subdir="charts/redhat"
        )

    def teardown_method(self):
        self.hc_api.delete_project()

    def test_package_persistent(self):
        self.hc_api.package_name = "redhat-postgresql-imagestreams"
        assert self.hc_api.helm_package()
        assert self.hc_api.helm_installation()
        self.hc_api.package_name = "redhat-postgresql-persistent"
        assert self.hc_api.helm_package()
        assert self.hc_api.helm_installation(
            values={
                ".image.tag": f"{VERSION}{TAG}",
                ".namespace": self.hc_api.namespace
            }
        )
        assert self.hc_api.is_pod_running(pod_name_prefix="postgresql-persistent")
        assert self.hc_api.test_helm_chart(expected_str=["accepting connection"])
