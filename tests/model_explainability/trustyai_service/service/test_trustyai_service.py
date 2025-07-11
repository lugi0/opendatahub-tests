import pytest
from ocp_resources.namespace import Namespace
from ocp_resources.trustyai_service import TrustyAIService

from tests.model_explainability.trustyai_service.constants import (
    DRIFT_BASE_DATA_PATH,
    TRUSTYAI_DB_MIGRATION_PATCH,
)
from tests.model_explainability.trustyai_service.trustyai_service_utils import (
    send_inferences_and_verify_trustyai_service_registered,
    verify_upload_data_to_trustyai_service,
    TrustyAIServiceMetrics,
    verify_trustyai_service_metric_scheduling_request,
    verify_trustyai_service_metric_delete_request,
)
from tests.model_explainability.trustyai_service.utils import (
    validate_trustyai_service_db_conn_failure,
    validate_trustyai_service_images,
)
from tests.model_explainability.trustyai_service.service.utils import (
    wait_for_trustyai_db_migration_complete_log,
    patch_trustyai_service_cr,
)
from utilities.constants import MinIo
from utilities.manifests.openvino import OPENVINO_KSERVE_INFERENCE_CONFIG


@pytest.mark.parametrize(
    "model_namespace",
    [
        pytest.param(
            {"name": "test-trustyai-service-invalid-db-cert"},
        )
    ],
    indirect=True,
)
def test_trustyai_service_with_invalid_db_cert(
    admin_client,
    current_client_token,
    model_namespace: Namespace,
    trustyai_service_with_invalid_db_cert,
):
    """Test to make sure TrustyAIService pod fails when incorrect database TLS certificate is used."""
    validate_trustyai_service_db_conn_failure(
        client=admin_client,
        namespace=model_namespace,
        label_selector=f"app.kubernetes.io/instance={trustyai_service_with_invalid_db_cert.name}",
    )


@pytest.mark.parametrize(
    "model_namespace, model_namespace_2, minio_pod, minio_data_connection, minio_data_connection_2",
    [
        pytest.param(
            {"name": "test-trustyaiservice-multins-1"},
            {"name": "test-trustyaiservice-multins-2"},
            MinIo.PodConfig.MODEL_MESH_MINIO_CONFIG,
            {"bucket": MinIo.Buckets.MODELMESH_EXAMPLE_MODELS},
            {"bucket": MinIo.Buckets.MODELMESH_EXAMPLE_MODELS},
        )
    ],
    indirect=True,
)
@pytest.mark.usefixtures("minio_pod")
class TestTrustyAIServiceMultipleNS:
    """Verifies that all the basic operations,
    i.e. registering inference requests, uploading data, scheduling and deleting metrics,
    that can be performed with a TrustyAIService metric
    (drift, in this case), work as expected when having more than one namespace."""

    def test_drift_send_inference_and_verify_trustyai_service_multiple_ns(
        self,
        admin_client,
        current_client_token,
        trustyai_service_with_pvc_storage,
        trustyai_service_with_pvc_storage_2,
        gaussian_credit_model,
        gaussian_credit_model_2,
        isvc_getter_token,
        isvc_getter_token_2,
    ) -> None:
        for trustyaiservice, inference_model, inference_token in zip(
            [trustyai_service_with_pvc_storage, trustyai_service_with_pvc_storage_2],
            [gaussian_credit_model, gaussian_credit_model_2],
            [isvc_getter_token, isvc_getter_token_2],
        ):
            send_inferences_and_verify_trustyai_service_registered(
                client=admin_client,
                token=current_client_token,
                data_path=f"{DRIFT_BASE_DATA_PATH}/data_batches",
                trustyai_service=trustyaiservice,
                inference_service=inference_model,
                inference_config=OPENVINO_KSERVE_INFERENCE_CONFIG,
                inference_token=inference_token,
            )

    def test_upload_data_to_trustyai_service_multiple_ns(
        self,
        admin_client,
        current_client_token,
        minio_data_connection,
        minio_data_connection_2,
        trustyai_service_with_pvc_storage,
        trustyai_service_with_pvc_storage_2,
    ) -> None:
        for trustyaiservice in [
            trustyai_service_with_pvc_storage,
            trustyai_service_with_pvc_storage_2,
        ]:
            verify_upload_data_to_trustyai_service(
                client=admin_client,
                trustyai_service=trustyaiservice,
                token=current_client_token,
                data_path=f"{DRIFT_BASE_DATA_PATH}/training_data.json",
            )

    def test_drift_metric_schedule_meanshift_multiple_ns(
        self,
        admin_client,
        current_client_token,
        trustyai_service_with_pvc_storage,
        trustyai_service_with_pvc_storage_2,
        gaussian_credit_model,
        gaussian_credit_model_2,
    ):
        for trustyaiservice, inference_model in zip(
            [trustyai_service_with_pvc_storage, trustyai_service_with_pvc_storage_2],
            [gaussian_credit_model, gaussian_credit_model_2],
        ):
            verify_trustyai_service_metric_scheduling_request(
                client=admin_client,
                trustyai_service=trustyaiservice,
                token=current_client_token,
                metric_name=TrustyAIServiceMetrics.Drift.MEANSHIFT,
                json_data={
                    "modelId": inference_model.name,
                    "referenceTag": "TRAINING",
                },
            )

    def test_drift_metric_delete_multiple_ns(
        self,
        admin_client,
        current_client_token,
        minio_data_connection,
        minio_data_connection_2,
        trustyai_service_with_pvc_storage,
        trustyai_service_with_pvc_storage_2,
    ):
        for trustyaiservice in [
            trustyai_service_with_pvc_storage,
            trustyai_service_with_pvc_storage_2,
        ]:
            verify_trustyai_service_metric_delete_request(
                client=admin_client,
                trustyai_service=trustyaiservice,
                token=current_client_token,
                metric_name=TrustyAIServiceMetrics.Drift.MEANSHIFT,
            )


@pytest.mark.parametrize(
    "model_namespace",
    [
        pytest.param(
            {"name": "test-validate-trustyai-service-images"},
        )
    ],
    indirect=True,
)
@pytest.mark.smoke
def test_validate_trustyai_service_image(
    admin_client,
    model_namespace: Namespace,
    related_images_refs: set[str],
    trustyai_service_with_pvc_storage: TrustyAIService,
    trustyai_operator_configmap,
):
    return validate_trustyai_service_images(
        client=admin_client,
        related_images_refs=related_images_refs,
        model_namespace=model_namespace,
        label_selector=f"app.kubernetes.io/instance={trustyai_service_with_pvc_storage.name}",
        trustyai_operator_configmap=trustyai_operator_configmap,
    )


@pytest.mark.parametrize(
    "model_namespace, minio_pod, minio_data_connection",
    [
        pytest.param(
            {"name": "validate-trustyai-db-migration"},
            MinIo.PodConfig.MODEL_MESH_MINIO_CONFIG,
            {"bucket": MinIo.Buckets.MODELMESH_EXAMPLE_MODELS},
        )
    ],
    indirect=True,
)
@pytest.mark.usefixtures("minio_pod")
def test_trustyai_service_db_migration(
    admin_client,
    current_client_token,
    mariadb,
    trustyai_db_ca_secret,
    trustyai_service_with_pvc_storage,
    gaussian_credit_model,
) -> None:
    """Verify if TrustyAI DB Migration works as expected.
    This test initializes TrustyAI Service with PVC Storage at first with a database on standby but the service is not
    configured to use it.
    Data is uploaded to the PVC, then the TrustyAI CR is patched to trigger a migration from PVC to DB storage.
    config.
    Then waits for the migration success entry in the container logs and patches the service again to remove PVC config.
    Finally, a metric is scheduled and checked if the service works as expected post migration.

    Args:
        admin_client: DynamicClient
        current_client_token: RedactedString
        mariadb: MariaDB
        trustyai_db_ca_secret: None
        trustyai_service_with_pvc_storage: TrustyAIService
        gaussian_credit_model: Generator[InferenceService, Any, Any]

    Returns:
        None
    """
    verify_upload_data_to_trustyai_service(
        client=admin_client,
        trustyai_service=trustyai_service_with_pvc_storage,
        token=current_client_token,
        data_path=f"{DRIFT_BASE_DATA_PATH}/training_data.json",
    )

    trustyai_db_migration_patched_service = patch_trustyai_service_cr(
        trustyai_service=trustyai_service_with_pvc_storage, patches=TRUSTYAI_DB_MIGRATION_PATCH
    )

    wait_for_trustyai_db_migration_complete_log(
        client=admin_client,
        trustyai_service=trustyai_db_migration_patched_service,
    )

    verify_trustyai_service_metric_scheduling_request(
        client=admin_client,
        trustyai_service=trustyai_db_migration_patched_service,
        token=current_client_token,
        metric_name=TrustyAIServiceMetrics.Drift.MEANSHIFT,
        json_data={
            "modelId": gaussian_credit_model.name,
            "referenceTag": "TRAINING",
        },
    )
