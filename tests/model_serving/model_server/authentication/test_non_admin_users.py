import pytest

from tests.model_serving.model_server.utils import verify_inference_response
from utilities.constants import ModelFormat, ModelStoragePath, Protocols, ModelInferenceRuntime
from utilities.inference_utils import Inference


@pytest.mark.parametrize(
    "unprivileged_model_namespace, unprivileged_s3_caikit_serverless_inference_service",
    [
        pytest.param(
            {"name": "non-admin-test"},
            {"model-dir": ModelStoragePath.FLAN_T5_SMALL},
        )
    ],
    indirect=True,
)
class TestKserveUnprivilegedUser:
    @pytest.mark.smoke
    @pytest.mark.serverless
    @pytest.mark.usefixtures("skip_if_no_deployed_openshift_serverless")
    @pytest.mark.polarion("ODS-2552")
    def test_non_admin_deploy_and_query_model(self, unprivileged_s3_caikit_serverless_inference_service):
        """Verify non admin can deploy a model and query using REST"""
        verify_inference_response(
            inference_service=unprivileged_s3_caikit_serverless_inference_service,
            runtime=ModelInferenceRuntime.CAIKIT_TGIS_RUNTIME,
            inference_type=Inference.ALL_TOKENS,
            protocol=Protocols.HTTPS,
            model_name=ModelFormat.CAIKIT,
            use_default_query=True,
        )
