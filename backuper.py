from dropbox.exceptions import ApiError, AuthError
from google.cloud import storage
import datetime
import dropbox
import config
import os
import sys

def list_files_in_dropbox_folder(dbx):
    result = dbx.files_list_folder(config.DROPBOX_KEEPASS_DIR)
    entries = result.entries
    while result.has_more:
        result = dbx.files_list_folder_continue(result.cursor)
        entries.extend(result.entries)
    print("Entries found:")
    for entry in entries:
        print(entry.name)
    return [entry.name for entry in result.entries]
    
def download_from_dropbox(dbx):
    dropbox_file_path = os.path.join(config.DROPBOX_KEEPASS_DIR, config.KEEPASS_FILENAME)
    local_file_path = os.path.join(config.LOCAL_KEEPASS_DIR, config.KEEPASS_FILENAME)
    try:
        dbx.files_download_to_file(local_file_path, dropbox_file_path)
    except ApiError as err:
        if err.user_message_text:
            print(err.user_message_text)
        else:
            print(err)
        sys.exit()
    return local_file_path

def upload_to_gcs(local_file_name, target_file_name):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = config.GCE_CREDS_FILE_PATH
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(config.GCS_BUCKET_NAME)

    blob = bucket.blob(target_file_name)
    blob.upload_from_filename(local_file_name)

if __name__ == '__main__':
    dbx = dropbox.Dropbox(config.DROPBOX_API_TOKEN)

    # Check that the access token is valid
    try:
        dbx.users_get_current_account()
    except AuthError:
        sys.exit("ERROR: Invalid dropbox access token")

    # Check that there is only one file in dropbox keepass dir (i.e. no conflicted copies)
    files = list_files_in_dropbox_folder(dbx)
    if len(files) != 1:
        print("Expected 1 file, but found {}. Dying...".format(len(files)))
        sys.exit()

    # Download keepass db file
    downloaded_file_path = download_from_dropbox(dbx)

    # Upload keepass file to GCS
    upload_to_gcs(downloaded_file_path, config.KEEPASS_FILENAME)
