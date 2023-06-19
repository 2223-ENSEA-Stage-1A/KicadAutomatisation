import os
import zipfile
from django.conf import settings
from django.shortcuts import render
from myapp.forms import DepositForm
from django.http import HttpResponse
import subprocess

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

def execute_script(script_path, folder_path, name):
    iAmThere = os.getcwd()

    # Change directory to the extracted folder
    #os.chdir(folder_path)
    
    # Execute the script and capture the output
    result = subprocess.run(['python', script_path, folder_path, name, "myapp/myscripts/configs"], capture_output=True, text=True)

    # Retrieve the captured output, return code, and combine them
    output = result.stdout + result.stderr
    
    os.chdir(iAmThere)

    return output

def treatOuput(output):
    output = output.split('\n')
    warnings = []
    warning = False
    errors = []
    error = False
    for line in output:
        if line.startswith("WARNING") and "W058" in line:
            error = False
            warnings.append(line)
            warning = True
        elif warning and line.strip().startswith("@"):
            warnings[-1] = warnings[-1] + line
        elif line.startswith("ERROR"):
            warning = False
            errors.append(line)
            error = True
        elif error and line.strip().startswith("@"):
            errors[-1] = errors[-1] + line
        else:
            error = False
            warning = False
    
    return "List of warnings <br>" + '\n'.join(warnings) + "\n\nList of Errors <br>" + '\n'.join(errors) 


def home(request):
    if request.method == 'POST':
        form = DepositForm(request.POST, request.FILES)
        if form.is_valid():
            name = form.cleaned_data['name']
            uploaded_file = request.FILES['file']
            
            # Save the uploaded file locally with the provided name
            file_path = handle_uploaded_file(uploaded_file, name)

            # Extract the contents of the zip file
            extracted_folder_path = extract_zip(file_path)
            
            # Execute the script and capture the output
            script_path = "myapp/myscripts/checkThisProject.py"
            output = execute_script(script_path, extracted_folder_path, name)
            
            # Provide a response with the output
            response = f"Thank you. Your file {name} deposited successfully!<br><br>"
            response += "Script executed successfully.<br><br>"

            response += treatOuput(output).replace('\n', '<br>')

            #response += output.replace('\n', '<br>') #To be deleted
            
            return HttpResponse(response)
    else:  # GET request
        form = DepositForm()

    return render(request, 'home.html', {'form': form})
