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

def execute_script(script_path, folder_path, name):
    iAmThere = os.getcwd()

    # Change directory to the extracted folder
    #os.chdir(folder_path)
    
    # Execute the script and capture the output
    result = subprocess.run(['python', script_path, folder_path, name, "myapp/myscripts/configs"], capture_output=True, text=True)

    # Retrieve the captured output, return code, and combine them
    output = result.stdout # + result.stderr
    
    os.chdir(iAmThere)

    return output

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
            response += output.replace('\n', '<br>')
            
            return HttpResponse(response)
    else:  # GET request
        form = DepositForm()

    return render(request, 'home.html', {'form': form})
