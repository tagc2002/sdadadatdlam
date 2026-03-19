from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import sys
sys.path.append("C:/users/tagc2/Downloads/sdadadatdlam/backend")
from repositories.Google.AuthAPI import basicAuth

def upload_basic():
    """Insert new file.
    Returns : Id's of the file uploaded

    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """
    creds = basicAuth({})

    try:
        # create drive api client
        service = build("drive", "v3", credentials=creds)

        file_metadata = {"name": "download.jpeg"}
        media = MediaFileUpload("download.jpeg", mimetype="image/jpeg")
        # pylint: disable=maybe-no-member
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        print(f'File ID: {file.get("id")}')

    except HttpError as error:
        print(f"An error occurred: {error}")
        file = None

    return file.get("id")

def test():
    creds = basicAuth({})

    try:
        service = build("drive", "v3", credentials=creds)
        results = service.files().list(pageSize=10, fields="nextPageToken, files(id, name)").execute()
        items = results.get("files", [])
        if not items:
            print("No files found")
            return
        print("Files:")
        for item in items:
            print(f"{item['name']} ({item['id']})") # type: ignore
    except HttpError as error:
        print(f'Error: {error}')

if __name__=="__main__":
    test()