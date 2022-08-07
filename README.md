# Azure Key Vault Backup

Solution to extract & transport data from Azure Key Vault (SaaS)
into external file storage (SharePoint)

Script should run as CronJob with no-concurency policy,
suitable to run in container, requires persistent volume.

Through Azure Key Vault REST API application list all secrets with their versions and cache them in file storage (sensitive data are ommited).
If there are incremental changes, they are packed into .zip files protected by password and trasported into external storage (SharePoint)

If non-critical error happen, script will keep running but exit code will be 1,
if run is without error exit code is 0

# Requirements

## Linux container with persitent volume

Application is running in container with mounted peristent volume as file storage

## Service Principal

Azure Service Principal with following permissions into target Azure Key Vaults:

| Name                      | Permissions |
| ------------------------- | ----------- |
| <b>Secret Permissions</b> | Get, List   |

## SharePoint

SharePoint site with App-Only service account with following permissions:

```
<AppPermissionRequests AllowAppOnlyPolicy="true">
  <AppPermissionRequest Scope="http://sharepoint/content/tenant" Right="FullControl" />
</AppPermissionRequests>
```

[SharePoint App-Only Docs](https://docs.microsoft.com/en-us/sharepoint/dev/solution-guidance/security-apponly-azureacs)

# Configs

## Environment

| Name                     | Example                                           | Description                                       |
| ------------------------ | ------------------------------------------------- | ------------------------------------------------- |
| KEYVAULT_BACKUP_PASSWORD | myStrongPassword                                  | ZIP password                                      |
| KEYVAULT_TENANT_ID       | 00000000-0000-0000-0000-000000000000              | (Azure Key Vault) Service Principal Tenant ID     |
| KEYVAULT_CLIENT_ID       | 00000000-0000-0000-0000-000000000000              | (Azure Key Vault) Service Principal Client ID     |
| KEYVAULT_CLIENT_SECRET   | xxxxxxxxxxxxxxxxxxxxxxxxx                         | (Azure Key Vault) Service Principal Client Secret |
| SHAREPOINT_URL           | https://organization.sharepoint.com/sites/backups | SharePoint URL                                    |
| SHAREPOINT_DIR           | Documents/Azure_Key_Vault                         | SharePoint upload directory path                  |
| SHAREPOINT_CLIENT_ID     | 00000000-0000-0000-0000-000000000000              | SharePoint Client ID                              |
| SHAREPOINT_CLIENT_SECRET | xxxxxxxxxxxxxxxxxxxxxxxxx                         | SharePoint Client Secret                          |
| PATH_CONFIG              | /etc/azure-keyvault-backup.json                   | Path where configs can be found                   |
| PATH_CACHE               | /mnt/cache                                        | Path where cache will be made                     |
| PATH_ARCHIVE             | /mnt/archive                                      | Path where archive will be made                   |

## Files

### azure-keyvault-backup.json

JSON file containing array with Azure Key Vault names

```json
["my-awesome-keyvault", "secret-data"]
```

# File structure

```
.
├── app                                 # App folder
├── configs                             # Contains environment files (for local development)
│   ├── test.env                        # Contains sensitive data which are injected into docker-compose.yaml
│   └── azure-keyvault-backup.json      # JSON array with Azure Key Vault names
└── tmp                                 # Mounted storage for application data
    ├── archive                         # Contains backup archives (cleaned after every success run)
    └── cache                           # Contains cache data
```

# Installation

## Requirements

- Docker running Linux containers (for local development)
- Service Principal for Azure Key Vault
- Sharepoint App-Only credentials

## Create configs

### ./configs/test.env

```bash
cat << EOF > ./configs/test.env
KEYVAULT_BACKUP_PASSWORD=xxx

KEYVAULT_TENANT_ID=00000000-0000-0000-0000-000000000000
KEYVAULT_CLIENT_ID=00000000-0000-0000-0000-000000000000
KEYVAULT_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxx

SHAREPOINT_URL=https://organization.sharepoint.com/sites/backups
SHAREPOINT_DIR=Documents/Azure_Key_Vault
SHAREPOINT_CLIENT_ID=00000000-0000-0000-0000-000000000000
SHAREPOINT_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxx
EOF
```

### ./configs/azure-keyvault-backup.json

```bash
cat << EOF > ./configs/azure-keyvault-backup.json
["my-awesome-keyvault", "secret-data"]
EOF
```

## Run container

```
docker-compose --env-file ./configs/test.env up --build
```

## Run container inactivelly & attach to it

You will need uncomment following section in <i>docker-compose.yaml</i>

```
    # stdin_open: true
    # tty: true
    # command: tail -f /dev/null
```

and run following command

```
docker-compose --env-file ./configs/test.env up --build -d && docker exec -it azure-keyvault-backup sh
```
