"""
Test module for ONNX  model served by Triton via KServe.

Validates inference using REST and gRPC protocols with both raw and serverless deployment modes.
"""

from typing import Any

import pytest
from ocp_resources.inference_service import InferenceService
from ocp_resources.pod import Pod
from simple_logger.logger import get_logger

from utilities.constants import Protocols
from tests.model_serving.model_runtime.triton.basic_model_deployment.utils import validate_inference_request, load_json
from tests.model_serving.model_runtime.triton.constant import (
    BASE_RAW_DEPLOYMENT_CONFIG,
    BASE_SERVERLESS_DEPLOYMENT_CONFIG,
    MODEL_PATH_PREFIX,
    TRITON_GRPC_ONNX_INPUT_PATH,
    TRITON_REST_ONNX_INPUT_PATH,
)

LOGGER = get_logger(name=__name__)

ONNX_MODEL_NAME = "densenetonnx"

MODEL_STORAGE_URI_DICT = {"model-dir": f"{MODEL_PATH_PREFIX}"}

pytestmark = pytest.mark.usefixtures(
    "root_dir", "valid_aws_config", "triton_rest_serving_runtime_template", "triton_grpc_serving_runtime_template"
)


@pytest.mark.parametrize(
    ("protocol", "model_namespace", "s3_models_storage_uri", "triton_serving_runtime", "triton_inference_service"),
    [
        pytest.param(
            {"protocol_type": Protocols.REST},
            {"name": "onnx-raw"},
            MODEL_STORAGE_URI_DICT,
            {**BASE_RAW_DEPLOYMENT_CONFIG},
            {
                "name": "densenetonnx-raw-rest",
                **BASE_RAW_DEPLOYMENT_CONFIG,
            },
            id="densenetonnx-raw-rest-deployment",
        ),
        pytest.param(
            {"protocol_type": Protocols.GRPC},
            {"name": "onnx-raw"},
            MODEL_STORAGE_URI_DICT,
            {**BASE_RAW_DEPLOYMENT_CONFIG},
            {
                "name": "densenetonnx-raw-grpc",
                **BASE_RAW_DEPLOYMENT_CONFIG,
            },
            id="densenetonnx-raw-grpc-deployment",
        ),
        pytest.param(
            {"protocol_type": Protocols.REST},
            {"name": "onnx-serverless"},
            MODEL_STORAGE_URI_DICT,
            {**BASE_SERVERLESS_DEPLOYMENT_CONFIG},
            {
                "name": "densenetonnx-serverless-rest",
                **BASE_SERVERLESS_DEPLOYMENT_CONFIG,
            },
            id="densenetonnx-serverless-rest-deployment",
        ),
        pytest.param(
            {"protocol_type": Protocols.GRPC},
            {"name": "onnx-serverless"},
            MODEL_STORAGE_URI_DICT,
            {**BASE_SERVERLESS_DEPLOYMENT_CONFIG},
            {
                "name": "densenetonnx-serverless-grpc",
                **BASE_SERVERLESS_DEPLOYMENT_CONFIG,
            },
            id="densenetonnx-serverless-grpc-deployment",
        ),
    ],
    indirect=True,
)
class TestONNXModel:
    """
    Test class for onnx inference using Triton on KServe.

    Covers:
    - REST and gRPC protocols
    - Raw and serverless modes
    - Snapshot validation of inference results
    """

    def test_onnx_inference(
        self,
        triton_inference_service: InferenceService,
        triton_pod_resource: Pod,
        triton_response_snapshot: Any,
        protocol: str,
        root_dir: str,
    ) -> None:
        """
        Run inference and validate against snapshot.

        Args:
            triton_inference_service: The deployed InferenceService object
            triton_pod_resource: The pod running the model server
            triton_response_snapshot: Expected response snapshot
            protocol: REST or gRPC
            root_dir: Root directory for test execution
        """
        input_path = TRITON_GRPC_ONNX_INPUT_PATH if protocol == Protocols.GRPC else TRITON_REST_ONNX_INPUT_PATH
        input_query = load_json(path=input_path)

        validate_inference_request(
            pod_name=triton_pod_resource.name,
            isvc=triton_inference_service,
            response_snapshot=triton_response_snapshot,
            input_query=input_query,
            model_name=ONNX_MODEL_NAME,
            protocol=protocol,
            root_dir=root_dir,
        )
