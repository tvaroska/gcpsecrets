"""
    GCS Secret Manager interface in form of Python Dictionary. Read-only for now

    usage with default project:
        secrets = GCPSecrets()
        api_key = secrets['API_KEY']

"""

from typing import Optional, Union

import google.auth
from google.api_core.exceptions import NotFound
from google.cloud import secretmanager

KEY_ERROR = "Key can be either string or tuple with 2 strings. Got {} with value {}"


class GCPSecrets:
    """
    GCS Secret Manager interface in form of Python Dictionary. Read-only for now

    usage with default project:
        secrets = GCPSecrets()
        api_key = secrets['API_KEY']

    """

    def __init__(
        self,
        project: Optional[str] = None,
        cache: Optional[bool] = True,
    ):
        if cache:
            self.versions = {}
            self.secrets = {}
        else:
            self.versions = None
            self.secrets = None
        self.cache = cache

        if project is not None:
            if not isinstance(project, str) or not project.strip():
                raise ValueError("Project must be a non-empty string")
            self.project = project
        else:
            # Get default project_id from the environment
            _, self.project = google.auth.default()
            if not self.project:
                raise ValueError(
                    "No GCP project specified and none found in Application Default Credentials. "
                    "Please provide a project explicitly or configure ADC with: gcloud auth application-default login"
                )

        self.client = secretmanager.SecretManagerServiceClient()

    def __getitem__(self, key) -> str:
        if self.cache and key in self.secrets:
            return self.secrets[key]

        return self.get(key)

    def __contains__(self, key):
        return self.contains(key)

    def __setitem__(self, key, value):
        raise NotImplementedError

    def _check_key_version(self, key: Union[str, tuple]) -> bool:
        if isinstance(key, str):
            return True
        elif isinstance(key, tuple) and len(key) == 2:
            return False
        else:
            raise ValueError(KEY_ERROR.format(type(key).__name__, key))

    def _get_address(self, secret: Union[str, tuple]):
        if isinstance(secret, tuple):
            key = secret[0]
            version = secret[1]
        else:
            key = secret
            version = "latest"

        # Return results from cache if enabled (no TTL)
        if self.cache and (key, version) in self.versions:
            return self.versions[(key, version)]

        # Get and potentially cache all the versions from the secret
        request = secretmanager.ListSecretVersionsRequest(
            parent=f"projects/{self.project}/secrets/{key}",
        )

        try:
            page_result = self.client.list_secret_versions(request=request)
        except NotFound as exc:
            raise KeyError(f"Secret '{key}' not found in project '{self.project}'") from exc

        active_versions = [
            (i.name.split("/")[-1], i.name, i.create_time)
            for i in page_result
            if i.state == 1
        ]
        latest = max(active_versions, key=lambda i: i[2])
        active_versions = {i[0]: (i[1]) for i in active_versions}
        active_versions["latest"] = latest[1]

        if self.cache:
            for ver in active_versions:
                self.versions[(key, ver)] = active_versions[ver]
            self.versions[key] = latest[1]

        return active_versions[version]

    def get(self, key: Union[str, tuple]) -> str:
        """

        get secret value

        Args:
            key (str or tuple): name of secret (str) or name and version (tuple)

        Returns:
            str: value of secret

        """
        self._check_key_version(key)
        address = self._get_address(key)

        request = secretmanager.AccessSecretVersionRequest(
            name=address,
        )
        response = self.client.access_secret_version(request=request)

        secret = response.payload.data.decode()

        if self.cache:
            self.secrets[key] = secret
            if isinstance(key, str):
                self.secrets[(key, "latest")] = secret

        return secret

    def contains(self, key: Union[str, tuple]):
        """

        check existence of key in Secrets Manager

        Args:
            key (str or tuple): name of secret (str) or name and version (tuple)

        Returns:
            bool: key exists
        """
        try:
            _ = self._get_address(key)
            return True
        except KeyError:
            return False
