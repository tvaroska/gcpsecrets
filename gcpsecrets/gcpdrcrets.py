# Copyright 2022 Google LLC.
# SPDX-License-Identifier: Apache-2.0

from google.cloud import secretmanager
from google.api_core.exceptions import NotFound

class GCPSecrets():
    def __init__(self, project: str, cache: bool = True, raise_exceptions: bool = True):
        self.project = project
        self.client = secretmanager.SecretManagerServiceClient()

        self.versions = {}
        self.secrets = {}
        self.cache = cache
        self.raise_exceptions = raise_exceptions

    def get_current_version(self, key):
        if key in self.versions:
            return self.version[key]
        else:
            request = secretmanager.ListSecretVersionsRequest(
                parent=f'projects/{self.project}/secrets/{key}',
            )

            try:
                page_result = self.client.list_secret_versions(request=request)
            except NotFound:
                return None


            new = None
            name = None
            for response in page_result:
                if response.state == secretmanager.SecretVersion.State.ENABLED:
                    if not new or (response.create_time > new):
                        new = response.create_time
                        name = response.name
            
            if self.cache:
                self.versions[key] = name

            return name

    def __getitem__(self, key) -> bytes:

        if key in self.secrets:
            return self.secrets[key]
        else:
            name = self.get_current_version(key)
            if not name:
                if self.raise_exceptions:
                    raise KeyError(f'Secret {key} does not exists in project {self.project}')
                else:
                    return None

            request = secretmanager.AccessSecretVersionRequest(
                name=name,
            )
            response = self.client.access_secret_version(request=request)

            if self.cache:
                self.secrets[key] = response.payload.data

            return response.payload.data

    def __setitem__(self, key, value):
        raise NotImplementedError