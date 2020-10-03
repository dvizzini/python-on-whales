from datetime import datetime
from typing import Any, Dict, List, Optional, Union, overload

from python_on_whales.client_config import (
    ClientConfig,
    DockerCLICaller,
    ReloadableObjectFromJson,
)
from python_on_whales.utils import DockerCamelModel, format_dict_for_cli, run, to_list


class NetworkInspectResult(DockerCamelModel):
    id: str
    name: str
    created: datetime
    scope: str
    driver: str
    enable_I_pv6: bool
    internal: bool
    attachable: bool
    ingress: bool
    config_from: dict
    config_only: bool
    containers: dict
    options: dict
    labels: dict


class Network(ReloadableObjectFromJson):
    def __init__(
        self, client_config: ClientConfig, reference: str, is_immutable_id=False
    ):
        super().__init__(client_config, "id", reference, is_immutable_id)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.remove()

    def _fetch_inspect_result_json(self, reference):
        return run(self.docker_cmd + ["network", "inspect", reference])

    def _parse_json_object(self, json_object: Dict[str, Any]) -> NetworkInspectResult:
        return NetworkInspectResult.parse_obj(json_object)

    @property
    def id(self) -> str:
        return self._get_immutable_id()

    @property
    def name(self) -> List[str]:
        return self._get_inspect_result().name

    def remove(self) -> None:
        """Removes this Docker network.

        Rather than removing it manually, you can use a context manager to
        make sure the network is deleted even if an exception is raised.

        ```python
        from python_on_whales import docker

        with docker.network.create("some_name") as my_net:
            docker.run(
                "busybox",
                ["ping", "idonotexistatall.com"],
                networks=[my_net],
                remove=True,
            )
            # an exception will be raised because the container will fail
            # but the network will be removed anyway.
        ```

        """
        NetworkCLI(self.client_config).remove(self)


ValidNetwork = Union[Network, str]


class NetworkCLI(DockerCLICaller):
    def connect(self):
        raise NotImplementedError

    def create(
        self,
        name: str,
        attachable: bool = False,
        driver: Optional[str] = None,
        gateway: Optional[str] = None,
        subnet: Optional[str] = None,
        options: List[str] = [],
    ) -> Network:
        """Creates a Docker network.

        # Arguments
            name: The name of the network

        # Returns
            A `python_on_whales.Network`.
        """
        full_cmd = self.docker_cmd + ["network", "create"]
        full_cmd.add_flag("--attachable", attachable)
        full_cmd.add_simple_arg("--driver", driver)
        full_cmd.add_simple_arg("--gateway", gateway)
        full_cmd.add_simple_arg("--subnet", subnet)
        full_cmd.add_args_list("--opt", options)
        full_cmd.append(name)
        return Network(self.client_config, run(full_cmd), is_immutable_id=True)

    def disconnect(self):
        raise NotImplementedError

    @overload
    def inspect(self, x: str) -> Network:
        ...

    @overload
    def inspect(self, x: List[str]) -> List[Network]:
        ...

    def inspect(self, x: Union[str, List[str]]) -> Union[Network, List[Network]]:
        if isinstance(x, str):
            return Network(self.client_config, x)
        else:
            return [Network(self.client_config, reference) for reference in x]

    def list(self, filters: Dict[str, str] = {}) -> List[Network]:
        full_cmd = self.docker_cmd + ["network", "list", "--no-trunc", "--quiet"]
        full_cmd.add_args_list("--filter", format_dict_for_cli(filters))

        ids = run(full_cmd).splitlines()
        return [Network(self.client_config, id_, is_immutable_id=True) for id_ in ids]

    def prune(self, filters: Dict[str, str] = {}):
        full_cmd = self.docker_cmd + ["network", "prune", "--force"]
        full_cmd.add_args_list("--filter", format_dict_for_cli(filters))
        run(full_cmd)

    def remove(self, networks: Union[ValidNetwork, List[ValidNetwork]]):
        """Removes a Docker network

        # Arguments
            networks: One or more networks.
        """
        full_cmd = self.docker_cmd + ["network", "remove"]
        for network in to_list(networks):
            full_cmd.append(network)
        run(full_cmd)
