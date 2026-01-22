import pytest

from container_ci_suite.helm import HelmChartsAPI

from conftest import VARS


class TestHelmRHELPostgresqlImageStreams:
    def setup_method(self):
        package_name = "redhat-postgresql-imagestreams"
        self.hc_api = HelmChartsAPI(
            path=VARS.TEST_DIR,
            package_name=package_name,
            tarball_dir=VARS.TEST_DIR,
            shared_cluster=True,
        )
        self.hc_api.clone_helm_chart_repo(
            repo_url="https://github.com/sclorg/helm-charts",
            repo_name="helm-charts",
            subdir="charts/redhat",
        )

    def teardown_method(self):
        self.hc_api.delete_project()

    @pytest.mark.parametrize(
        "version,registry,expected",
        [
            ("10-el8", "registry.redhat.io/rhel8/postgresql-10:latest", False),
            ("13-el8", "registry.redhat.io/rhel8/postgresql-13:latest", True),
            ("13-el9", "registry.redhat.io/rhel9/postgresql-13:latest", True),
            ("15-el8", "registry.redhat.io/rhel8/postgresql-15:latest", True),
            ("15-el9", "registry.redhat.io/rhel9/postgresql-15:latest", True),
            ("16-el8", "registry.redhat.io/rhel8/postgresql-16:latest", True),
            ("16-el9", "registry.redhat.io/rhel9/postgresql-16:latest", True),
            ("16-el10", "registry.redhat.io/rhel10/postgresql-16:latest", True),
        ],
    )
    def test_package_imagestream(self, version, registry, expected):
        assert self.hc_api.helm_package()
        assert self.hc_api.helm_installation()
        assert (
            self.hc_api.check_imagestreams(version=version, registry=registry)
            == expected
        )
