import os
import shutil
import tempfile
import time
import zipfile


from django.conf import settings
from django.contrib import messages



def handle_uploaded_file(file, name):
    # Get the original file extension
    _, extension = os.path.splitext(file.name)
    
    # Generate the new file name
    new_file_name = f"{name}{extension}"
    
    # Define the folder name
    folder_name = 'ProjectToProcess'
    
    # Create the folder if it doesn't exist
    folder_path = os.path.join(settings.MEDIA_ROOT, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    
    # Generate the file path within the folder
    file_path = os.path.join(folder_path, new_file_name)
    
    # Save the uploaded file to the local storage with the new name
    with open(file_path, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    
    return file_path

def extract_zip(file_path):
    # Create a unique folder name
    folder_name = os.path.splitext(os.path.basename(file_path))[0]
    
    # Define the folder path for extracted contents
    folder_path = os.path.join(settings.MEDIA_ROOT, 'ProjectToProcess', folder_name)
    os.makedirs(folder_path, exist_ok=True)
    
    # Extract the contents of the zip file
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(folder_path)
    
    return folder_path

def compress_folder_to_zip(folder_path):
    # Get the base name of the folder
    folder_name = os.path.basename(folder_path)
    
    # Define the output zip file path
    zip_file_path = f"{folder_name}.zip"
    
    # Create a new zip file
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Iterate over all the files and subdirectories in the folder
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                # Get the absolute file path
                file_path = os.path.join(root, file)
                
                # Calculate the relative file path within the folder
                relative_path = os.path.relpath(file_path, folder_path)
                
                # Add the file to the zip archive with the relative path
                zipf.write(file_path, arcname=relative_path)
    
    return zip_file_path

def save_gerber_file(gerber_file):
    # Determine the location where you want to save the Gerber file
    save_path = 'gerbers_to_be_handled/'
    
    # Save the Gerber file
    with open(save_path + gerber_file.name, 'wb+') as destination:
        for chunk in gerber_file.chunks():
            destination.write(chunk)

def is_staff_member(user):
    if user.is_authenticated and user.is_staff:
        return True
    return False

def copy_file_to_temp_folder(file_path):
    # Create a temporary folder
    temp_folder = tempfile.mkdtemp()

    # Get the file name from the original file path
    file_name = os.path.basename(file_path)

    # Construct the destination path in the temporary folder
    file_destination_path = os.path.join(temp_folder, file_name)

    # Copy the file to the temporary folder
    shutil.copy2(file_path, file_destination_path)

    # Return the path to the copied file in the temporary folder
    return file_destination_path, temp_folder

def unzip_file(zip_file_path, output_directory):
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(output_directory)

def timeit(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Function '{func.__name__}' took {execution_time:.6f} seconds to execute.")
        return result
    return wrapper

def clear_messages(request):
    storage = messages.get_messages(request)
    storage.used = True
    for message in storage:
        pass  # Optionally, you can perform some action with each message here
