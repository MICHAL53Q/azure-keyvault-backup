from office365.runtime.auth.client_credential import ClientCredential
from office365.sharepoint.client_context import ClientContext


class SharePoint:
    def __init__(self, url: str, client_id: str, client_secret: str) -> None:
        self.client = ClientContext(url).with_credentials(ClientCredential(client_id, client_secret))

    def upload_file(self, root_dir: str, target_dir: str, file_path: str):
        # Get upload folder
        if target_dir == "":
            target_folder = self.client.web.get_folder_by_server_relative_path(f"{root_dir}")
        else:
            target_folder = self.client.web.get_folder_by_server_relative_path(f"{root_dir}/{target_dir}")

        # Upload file to sharepoint
        size_chunk = 50000000
        target_folder.files.create_upload_session(file_path, size_chunk).execute_query()

    def ensure_dir_exists(self, root_dir: str, target_dir: str):
        self.client.web.ensure_folder_path(f"{root_dir}/{target_dir}").execute_query()
