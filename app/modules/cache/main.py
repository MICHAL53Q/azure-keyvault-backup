import json
import os


class Cache:
    def __init__(self, path_cache: str, keyvault_name: str) -> None:
        self.__file_path = f"{path_cache}/{keyvault_name}.json"

    def store_keyvault_data(self, keyvault_data: list):
        with open(self.__file_path, 'w') as file:
            json.dump(keyvault_data, file)

    def get_keyvault_data(self) -> list:
        # Check if cache exists
        if os.path.exists(self.__file_path) is False:
            return []

        with open(self.__file_path) as file:
            keyvault_data = json.load(file)
            return keyvault_data

    def get_keyvault_data_by_version(self, secret_name: str, secret_version: str) -> list:
        if os.path.exists(self.__file_path) is False:
            raise Exception(f"get_keyvault_data_by_version | Cache file is missing")

        with open(self.__file_path) as file:
            keyvault_data = json.load(file)

        secret = list(filter(lambda keyvault_data: keyvault_data['name'] == secret_name, keyvault_data))

        if len(secret) == 0:
            raise Exception(f"get_keyvault_data_by_version | Secret is missing")

        secret_version = list(filter(lambda secret_versions: secret_versions['version'] == secret_version, secret[0]['versions']))
        if len(secret_version) == 0:
            raise Exception(f"get_keyvault_data_by_version | Secret version is missing")

        return secret_version[0]
