#!/usr/bin/env python3
"""
Azure Key Vault Backup

Solution to extract & transport sensitive data from Azure Key Vaults
into external file storage (SharePoint)

Script should run as CronJob with no-concurency policy,
suitable to run in container, requires persistent volume.
"""

__author__ = "MICHAL53Q@gmail.com"
__version__ = "0.1.0"
__license__ = "MIT"

import os
import sys
import shutil
from logzero import logger

from app.modules.cache.main import Cache
from app.modules.azure_keyvault.main import AzureKeyVault
from app.modules.sharepoint.main import SharePoint


def set_exit_code(value: int) -> None:
    global exit_code
    exit_code = value


def get_exit_code() -> int:
    global exit_code
    return exit_code


def except_hook(exctype, excvalue, exctraceback):
    import traceback

    logger.error(excvalue)
    logger.error(traceback.format_tb(exctraceback))
    sys.exit(1)


# Set initial exit code
exit_code = 0

# Set default exception handler
sys.excepthook = except_hook


def get_archive_paths(path_archive: str) -> dict:
    # Get len of path_archive to substring absolute path
    len_substring_path = len(path_archive) + 1

    dir_paths = set()
    file_paths = set()
    for subdir, dirs, files in os.walk(path_archive):
        for file in files:
            full_path = os.path.join(subdir, file)
            absolute_path = os.path.dirname(full_path)
            subpath = absolute_path[len_substring_path:]

            if len(subpath) != 0:
                dir_paths.add(subpath)
            file_paths.add(full_path)

    return {
        "dir_paths": dir_paths,
        "file_paths": file_paths
    }


def clean_archive_path(path_archive: str) -> None:
    logger.info(f"clean_archive_path | cleaning archive path | path_archive: {path_archive}")
    for file in os.listdir(path_archive):
        if os.path.isdir(file):
            shutil.rmtree(f"{path_archive}/{file}")


def get_env_vars() -> tuple:
    try:
        keyvault_backup_password = os.environ['KEYVAULT_BACKUP_PASSWORD']

        keyvault_tenant_id = os.environ['KEYVAULT_TENANT_ID']
        keyvault_client_id = os.environ['KEYVAULT_CLIENT_ID']
        keyvault_client_secret = os.environ['KEYVAULT_CLIENT_SECRET']

        sharepoint_url = os.environ['SHAREPOINT_URL']
        sharepoint_dir = os.environ['SHAREPOINT_DIR']
        sharepoint_client_id = os.environ['SHAREPOINT_CLIENT_ID']
        sharepoint_client_secret = os.environ['SHAREPOINT_CLIENT_SECRET']

        path_config = os.environ['PATH_CONFIG']
        path_cache = os.environ['PATH_CACHE']
        path_archive = os.environ['PATH_ARCHIVE']
    except KeyError as exception:
        raise Exception(f"Missing ENV Variable: {exception}")

    return keyvault_backup_password, keyvault_tenant_id, keyvault_client_id, keyvault_client_secret, sharepoint_url, sharepoint_dir, sharepoint_client_id, sharepoint_client_secret, path_config, path_cache, path_archive


def compare_keyvault_data(a_keyvault_data: list, b_keyvault_data: list) -> list:
    result = []

    for a_secret in a_keyvault_data:
        a_secret_name = a_secret['name']
        a_secret_versions = a_secret['versions']

        b_secret = list(filter(lambda keyvault_data: keyvault_data['name'] == a_secret_name, b_keyvault_data))

        versions = []

        if len(b_secret) == 0:
            # If secret isn't cached yet, add all versions
            for a_secret_version in a_secret_versions:
                a_secret_version_version = a_secret_version['version']

                versions.append(a_secret_version_version)
        else:
            # Compare versions to detect changes
            b_secret_versions = b_secret[0]['versions']
            for a_secret_version in a_secret_versions:
                a_secret_version_version = a_secret_version['version']

                b_secret_version = list(filter(lambda secret_versions: secret_versions['version'] == a_secret_version_version, b_secret_versions))

                if len(b_secret_version) == 0 or b_secret_version[0] != a_secret_version:
                    versions.append(a_secret_version_version)

        # Add to changes only if versions has changes
        if len(versions) != 0:
            result.append({
                'name': a_secret_name,
                'versions': versions
            })

    return result


def sync_keyvault_data(cache: Cache, keyvault: AzureKeyVault, keyvault_name: str) -> tuple:
    # Get actual Key Vault data
    logger.info(f"sync_keyvault_data | keyvault_name: {keyvault_name} | getting actual keyvault data")
    actual_keyvault_data = get_keyvault_data(keyvault)

    # Load cached Key Vault data
    logger.info(f"sync_keyvault_data | keyvault_name: {keyvault_name} | getting cached keyvault data")
    cached_keyvault_data = cache.get_keyvault_data()

    # Compare data to find out what needs to be added and what should be removed
    logger.info(f"sync_keyvault_data | keyvault_name: {keyvault_name} | comparing data")
    to_add = compare_keyvault_data(actual_keyvault_data, cached_keyvault_data)
    to_remove = compare_keyvault_data(cached_keyvault_data, actual_keyvault_data)

    # Store actual Key Vault data in Cache
    logger.info(f"sync_keyvault_data | keyvault_name: {keyvault_name} | storing data in cache")
    cache.store_keyvault_data(actual_keyvault_data)

    return to_add, to_remove


def get_keyvault_data(keyvault: AzureKeyVault) -> None:
    # Load secrets data from Key Vault
    keyvault_secrets_name = keyvault.list_secrets_name()

    # Get Key Vault secrets and their versions
    keyvault_data = []
    for keyvault_secret_name in keyvault_secrets_name:
        secret_data = {
            'name': keyvault_secret_name,
            'versions': keyvault.get_secret_versions_data(keyvault_secret_name)
        }
        keyvault_data.append(secret_data)

    return keyvault_data


def load_config(path_config: str) -> list:
    import json

    # Check if cache exists
    if os.path.exists(path_config) is False:
        raise Exception(f"Missing Config file, path: {path_config}")

    with open(path_config) as file:
        config_data = json.load(file)
        return config_data


def backup_data(keyvault_backup_password: str, keyvault_tenant_id: str, keyvault_client_id: str, keyvault_client_secret: str, path_config: str, path_cache: str, path_archive: str) -> None:
    keyvault_names = load_config(path_config)

    try:
        for keyvault_name in keyvault_names:
            logger.info(f"backup_data | keyvault_name: {keyvault_name} | start")

            # Init modules
            cache = Cache(path_cache, keyvault_name)
            keyvault = AzureKeyVault(keyvault_tenant_id, keyvault_client_id, keyvault_client_secret, keyvault_name)

            # Sync KeyVault data and get changes
            to_add, to_remove = sync_keyvault_data(cache, keyvault, keyvault_name)

            # Archive changed secrets versions
            for secret in to_add:
                secret_name = secret['name']
                for secret_version in secret['versions']:
                    # Get data from cache
                    secret_version_data = cache.get_keyvault_data_by_version(secret_name, secret_version)

                    # Append secret value to data
                    secret_version_data['value'] = keyvault.get_secret_version_value(secret_name, secret_version)

                    # Archive secret version
                    logger.info(f"backup_data | keyvault_name: {keyvault_name} | secret_name: {secret_name} | secret_version: {secret_version} | archiving secret")
                    archive_secret_version(keyvault_name, secret_name, secret_version, path_archive, keyvault_backup_password, secret_version_data)

            logger.info(f"backup_data | keyvault_name: {keyvault_name} | finish")
    except Exception as e:
        logger.error(f"backup_data | Exception raised during backuping data | exception: {e}")
        set_exit_code(1)


def archive_secret_version(keyvault_name: str, secret_name: str, secret_version: str, path_archive: str, password: str, data: dict):
    import json
    import pyminizip

    path_secret_directory = f"{path_archive}/{keyvault_name}/{secret_name}"
    path_secret_version = f"{path_secret_directory}/{secret_version}"

    # Create directory if doesnt exists
    if not os.path.exists(path_secret_directory):
        os.makedirs(path_secret_directory)

    # Write secret into file
    with open(f"{path_secret_version}.json", 'w') as file:
        json.dump(data, file)

    # Archive to .zip
    pyminizip.compress(f"{path_secret_version}.json", None, f"{path_secret_version}.zip", password, 1)

    # Remove temporary file
    os.remove(f"{path_secret_version}.json")


def upload_changes_to_sharepoint(sharepoint_url: str, sharepoint_client_id: str, sharepoint_client_secret: str, path_archive: str, sharepoint_dir: str):
    # Get len of path_archive to substring absolute path
    len_substring_path = len(path_archive) + 1

    # Collect paths required to upload files to SharePoint
    archive_paths = get_archive_paths(path_archive)
    dir_paths = archive_paths['dir_paths']
    file_paths = archive_paths['file_paths']

    # Get SharePoint client
    shp = SharePoint(sharepoint_url, sharepoint_client_id, sharepoint_client_secret)

    # Ensure dir_paths exists in SharePoint
    for dir_path in dir_paths:
        logger.info(f"upload_changes_to_sharepoint | ensuring dir exists | sharepoint_dir: {sharepoint_dir} | dir_path: {dir_path}")
        shp.ensure_dir_exists(sharepoint_dir, dir_path)

    # Upload files to SharePoint
    for file_path in file_paths:
        full_dir_path = os.path.dirname(file_path)
        relative_dir_path = full_dir_path[len_substring_path:]

        # ignore files placed in archive path
        if relative_dir_path == "":
            continue

        logger.info(f"upload_changes_to_sharepoint | upload file | sharepoint_dir: {sharepoint_dir} | relative_dir_path: {relative_dir_path} | file_path: {file_path}")
        shp.upload_file(sharepoint_dir, relative_dir_path, file_path)

    clean_archive_path(path_archive)


def main():
    # Get ENV Variables
    keyvault_backup_password, keyvault_tenant_id, keyvault_client_id, keyvault_client_secret, sharepoint_url, sharepoint_dir, sharepoint_client_id, sharepoint_client_secret, path_config, path_cache, path_archive = get_env_vars()

    # Create dirs if doesn't exists
    if not os.path.exists(path_cache):
        os.makedirs(path_cache)

    # Create dirs if doesn't exists
    if not os.path.exists(path_archive):
        os.makedirs(path_archive)

    # Sync local data with remote
    backup_data(keyvault_backup_password, keyvault_tenant_id, keyvault_client_id, keyvault_client_secret, path_config, path_cache, path_archive)

    # Upload archived changes into sharepoint
    upload_changes_to_sharepoint(sharepoint_url, sharepoint_client_id, sharepoint_client_secret, path_archive, sharepoint_dir)

    # Exit script with exit code
    sys.exit(get_exit_code())


if __name__ == "__main__":
    main()
