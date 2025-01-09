import pytest

from tests.model_serving.model_server.metrics.utils import run_inference_multiple_times
from tests.model_serving.model_server.utils import verify_inference_response
from utilities.constants import (
    KServeDeploymentType,
    ModelFormat,
    ModelInferenceRuntime,
    ModelStoragePath,
    Protocols,
    RuntimeTemplates,
)
from utilities.inference_utils import Inference
from utilities.monitoring import get_metrics_value, validate_metrics_value

pytestmark = pytest.mark.usefixtures("skip_if_no_deployed_openshift_serverless", "valid_aws_config", "deleted_metrics")


@pytest.mark.serverless
@pytest.mark.jira("RHOAIENG-3236", run=False)
@pytest.mark.parametrize(
    "model_namespace, s3_models_storage_uri, serving_runtime_from_template, s3_models_inference_service",
    [
        pytest.param(
            {"name": "kserve-tgis-metrics"},
            {"model-dir": ModelStoragePath.FLAN_T5_SMALL},
            {
                "name": f"{Protocols.HTTP}-{ModelInferenceRuntime.CAIKIT_TGIS_RUNTIME}",
                "template-name": RuntimeTemplates.CAIKIT_TGIS_SERVING,
                "multi-model": False,
                "enable-http": True,
            },
            {"name": f"{Protocols.HTTP}-{ModelFormat.CAIKIT}", "deployment-mode": KServeDeploymentType.SERVERLESS},
        )
    ],
    indirect=True,
)
class TestModelMetrics:
    @pytest.mark.smoke
    @pytest.mark.polarion("ODS-2555")
    @pytest.mark.dependency(name="test_model_metrics_num_success_requests")
    def test_model_metrics_num_success_requests(self, s3_models_inference_service, prometheus):
        """Verify number of successful model requests in OpenShift monitoring system (UserWorkloadMonitoring)metrics"""
        verify_inference_response(
            inference_service=s3_models_inference_service,
            runtime=ModelInferenceRuntime.CAIKIT_TGIS_RUNTIME,
            inference_type=Inference.ALL_TOKENS,
            protocol=Protocols.HTTPS,
            model_name=ModelFormat.CAIKIT,
            use_default_query=True,
        )
        validate_metrics_value(
            prometheus=prometheus,
            metrics_query="tgi_request_success",
            expected_value="1",
        )

    @pytest.mark.smoke
    @pytest.mark.polarion("ODS-2555")
    @pytest.mark.dependency(
        name="test_model_metrics_num_total_requests",
        depends=["test_model_metrics_num_success_requests"],
    )
    def test_model_metrics_num_total_requests(self, s3_models_inference_service, prometheus):
        """Verify number of total model requests in OpenShift monitoring system (UserWorkloadMonitoring)metrics"""
        total_runs = 5

        run_inference_multiple_times(
            isvc=s3_models_inference_service,
            runtime=ModelInferenceRuntime.CAIKIT_TGIS_RUNTIME,
            inference_type=Inference.ALL_TOKENS,
            protocol=Protocols.HTTPS,
            model_name=ModelFormat.CAIKIT,
            iterations=total_runs,
            run_in_parallel=True,
        )
        validate_metrics_value(
            prometheus=prometheus,
            metrics_query="tgi_request_count",
            expected_value=str(total_runs + 1),
        )

    @pytest.mark.smoke
    @pytest.mark.polarion("ODS-2555")
    @pytest.mark.dependency(depends=["test_model_metrics_num_total_requests"])
    def test_model_metrics_cpu_utilization(self, s3_models_inference_service, prometheus):
        """Verify CPU utilization data in OpenShift monitoring system (UserWorkloadMonitoring)metrics"""
        assert get_metrics_value(
            prometheus=prometheus,
            metrics_query=f"pod:container_cpu_usage:sum{{namespace='${s3_models_inference_service.namespace}'}}",
        )