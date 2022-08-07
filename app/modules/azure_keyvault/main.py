from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient


class AzureKeyVault:
    def __init__(self, tenant_id: str, client_id: str, client_secret: str, keyvault_name: str) -> None:
        vault_url = f"https://{keyvault_name}.vault.azure.net/"

        credentials = ClientSecretCredential(tenant_id, client_id, client_secret)
        self.__client = SecretClient(vault_url, credentials)

    def list_secrets_name(self) -> set:
        secrets = self.__client.list_properties_of_secrets()

        result = set()
        for secret in secrets:
            secret_name = secret.name
            result.add(secret_name)

        return result

    def get_secret_versions_data(self, secret_name: str) -> list:
        secret_versions = self.__client.list_properties_of_secret_versions(secret_name)

        result = list()
        for secret_version in secret_versions:
            secret_version_data = {
                'version': secret_version.version,
                'enabled': secret_version.enabled,
                'content_type': secret_version.content_type,
                'created_on': (secret_version.created_on.isoformat() if secret_version.created_on else None),
                'updated_on': (secret_version.updated_on.isoformat() if secret_version.updated_on else None),
                'not_before': (secret_version.not_before.isoformat() if secret_version.not_before else None),
                'expires_on': (secret_version.expires_on.isoformat() if secret_version.expires_on else None),
                'tags': secret_version.tags,
                'managed': secret_version.managed
            }
            result.append(secret_version_data)

        return result

    def get_secret_version_value(self, secret_name: str, secret_version: str) -> str:
        return self.__client.get_secret(secret_name, secret_version).value
