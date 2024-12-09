from kubernetes.dynamic import DynamicClient
from ocp_resources.namespace import Namespace
from ocp_resources.service import Service
from ocp_resources.model_registry import ModelRegistry
from kubernetes.dynamic.exceptions import ResourceNotFoundError

from tests.utils import ProtocolNotSupported
from utilities.constants import Protocols
from tests.model_registry.constants import ModelRegistryEndpoints


def get_mr_service_by_label(client: DynamicClient, ns: Namespace, mr_instance: ModelRegistry) -> Service:
    """
    Args:
        client (DynamicClient): OCP Client to use.
        ns (Namespace): Namespace object where to find the Service
        mr_instance (ModelRegistry): Model Registry instance

    Returns:
        Service: The matching Service

    Raises:
        ResourceNotFoundError: if no service is found.
    """
    if svc := [
        svcs
        for svcs in Service.get(
            dyn_client=client,
            namespace=ns.name,
            label_selector=f"app={mr_instance.name},component=model-registry",
        )
    ]:
        return svc[0]

    raise ResourceNotFoundError(f"{mr_instance.name} has no Service")


def get_endpoint_from_mr_service(client: DynamicClient, svc: Service, protocol: str) -> str | ProtocolNotSupported:
    if protocol == Protocols.REST:
        return svc.instance.metadata.annotations["routing.opendatahub.io/external-address-rest"]
    elif protocol == Protocols.GRPC:
        return svc.instance.metadata.annotations["routing.opendatahub.io/external-address-grpc"]
    else:
        raise ProtocolNotSupported(protocol)


def generate_register_model_command(endpoint: str, token: str) -> str:
    auth_header = f" -H 'Authorization: Bearer {token}'"
    content_header = " -H 'Content-Type: application/json'"
    data = ' -d \'{"name": "model-name", "description": "test-model", "owner": "opendatahub-tests-client", "externalId": "1", "state": "LIVE"}\''
    cmd = (
        "curl -k "
        + auth_header
        + content_header
        + data
        + " "
        + Protocols.HTTPS
        + "://"
        + endpoint
        + ModelRegistryEndpoints.REGISTERED_MODELS
    )
    return cmd
