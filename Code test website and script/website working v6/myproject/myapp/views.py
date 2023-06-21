import os
import shutil
import zipfile
from django.conf import settings
from django.shortcuts import render

from django.core.files import File

from django.http import HttpResponse, HttpResponseNotFound
import subprocess
from .forms import GerberUploadForm
from django.contrib.auth.decorators import login_required

from django.shortcuts import redirect

from .models import UploadedFile, ResultFile

from myapp.forms import DepositForm

from django.utils import timezone

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404

from django.http import FileResponse, Http404

from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied



from collections import defaultdict
import pcbnew














@staff_member_required(login_url='login')
def gerber_upload(request):
    if request.method == 'POST':

        form = GerberUploadForm(request.POST, request.FILES)
        if form.is_valid():
            gerber_files = request.FILES.getlist('gerber_files')
            for gerber_file in gerber_files:
                save_gerber_file(gerber_file)

            return render(request, 'gerber_upload_success.html')
    else:
        form = GerberUploadForm()
    
    return render(request, 'gerber_upload.html', {'form': form})


@login_required
def logged_home(request):
    if request.method == 'POST':
        form = DepositForm(request.POST, request.FILES)
        if form.is_valid():
            description = form.cleaned_data['description']
            uploaded_file = request.FILES['file']
            name = f"{request.user.username} {timezone.now().date()}"
            
            file_path = handle_uploaded_file(uploaded_file, name)

            extracted_folder_path = extract_zip(file_path)

            script_path = "myapp/myscripts/checkThisProject.py"
            output = execute_script(script_path, extracted_folder_path, name)
            
            response = f"Thank you. Your file {name} deposited successfully!<br><br>"
            response += "Script executed successfully.<br><br>"

            response += treatOuput(output).replace('\n', '<br>')

            #response += output.replace('\n', '<br>') #To be deleted, only used for debug


            #Load all the created files and Storing them

            drcs = [x for x in os.listdir() if "-drc.txt" in x]
            ercs = [x for x in os.listdir() if "-erc.txt" in x]

            if(len(drcs) == 1 and os.path.isfile(drcs[0])):
                DRCresultf = open(drcs[0], 'rb')
            else: DRCresultf = None

            if(len(ercs) == 1 and os.path.isfile(ercs[0])):
                ERCresultf = open(ercs[0], 'rb')
            else: ERCresultf = None
            
            zippedGerbersf = open(compress_folder_to_zip("Gerbers"), 'rb')
            zippedDrillsf = open(compress_folder_to_zip("Drills"), 'rb')

            # Convert file objects to Django's File objects
            zippedGerbersf = File(zippedGerbersf)
            zippedDrillsf = File(zippedDrillsf)
            DRCresultf = File(DRCresultf) if DRCresultf else None
            ERCresultf = File(ERCresultf) if ERCresultf else None

            # Create a new UploadedFile instance and save it to the database
            uploadedFile = UploadedFile.objects.create(
                user=request.user,
                filename=name,
                file=uploaded_file,
                description=description,
                uploaded_at = timezone.now()
            )

            resultFile = ResultFile.objects.create(
                user=request.user,
                filename=name,
                description=description,
                uploaded_at = timezone.now(),
                zippedGerbers = zippedGerbersf,
                zippedDrills = zippedDrillsf,
                DRCresult = DRCresultf,
                ERCresult = ERCresultf,
                uploaded_file = uploadedFile
            )

            resultFile.save()

            print(os.getcwd())

            try: shutil.rmtree('Gerbers')
            except: print("euh ?, Gerbers")

            try: shutil.rmtree('Drills')
            except: print("euh ?, Drills")

            try: shutil.rmtree(f"ProjectToProcess/{name}")
            except: print("euh ?, ProjectToProcess/")
            try: shutil.rmtree(f"ProjectToProcess/{name}.zip")
            except: print("euh ?, ProjectToProcess/.zip")                

            try: 
                for drc in drcs:
                    os.remove(drc)
            except: print("euh ?, drc")

            try:             
                for erc in ercs:
                    os.remove(erc)
            except: print("euh ?, erc")

            return HttpResponse(response)
    else:  # GET request
        form = DepositForm()

    return render(request, 'logged_home.html', {'form': form})


@login_required
def profile(request):
    return redirect('logged_home')

def logout(request):
    return redirect('home')

def home(request):
    return render(request, 'home.html')

def user_files(request):
    user = request.user  # Get the currently logged-in user
    selected_files = request.POST.getlist('selected_files')
    print(selected_files)

    if user.is_staff:
        resultfiles = ResultFile.objects.all()
    else:
        resultfiles = ResultFile.objects.filter(user=user)


    
    return render(request, 'user_files.html', {'resultfiles': resultfiles, 'selected_files':selected_files})

def delete_file(request):
    if request.method == 'POST':
        file_type = request.POST.get('file_type')
        file_id = request.POST.get('file_id')
        
        print(file_type, file_id)

        try:
            if file_type == 'uploaded_file':
                file_obj = UploadedFile.objects.get(id=file_id)
                file_obj.file.delete(save=False)
                file_obj.delete()
            elif file_type == 'result_file':
                
                file_obj = ResultFile.objects.get(id=file_id)
                file_obj.zippedGerbers.delete(save=False)
                file_obj.zippedDrills.delete(save=False)
                file_obj.DRCresult.delete(save=False)
                file_obj.ERCresult.delete(save=False)
                file_obj.delete()
            else:
                return JsonResponse({'success': False, 'message': 'Invalid file type.'})

            return JsonResponse({'success': True, 'message': 'File deleted successfully.'})
        except (UploadedFile.DoesNotExist, ResultFile.DoesNotExist):
            return JsonResponse({'success': False, 'message': 'File not found.'})

    return JsonResponse({'success': False, 'message': 'Invalid request.'})




def view_file(request, file_id, file_type):
    try:
        # Retrieve the file based on file_id and file_type
        if file_type == 'zippedGerbers':
            file_obj = ResultFile.objects.get(id=file_id).zippedGerbers
        elif file_type == 'zippedDrills':
            file_obj = ResultFile.objects.get(id=file_id).zippedDrills
        elif file_type == 'DRCresult':
            file_obj = ResultFile.objects.get(id=file_id).DRCresult
        elif file_type == 'ERCresult':
            file_obj = ResultFile.objects.get(id=file_id).ERCresult
        elif file_type == 'uploaded_file':
            file_obj = ResultFile.objects.get(id=file_id).uploaded_file.file
        else:
            raise Http404

        # Check if the file exists
        if not file_obj:
            raise Http404

        # Open the file as a binary file
        file = open(file_obj.path, 'rb')

        # Create a FileResponse object with the file
        response = FileResponse(file, content_type='application/zip')

        # Set the appropriate Content-Disposition header to trigger a download
        response['Content-Disposition'] = f'attachment; filename="{file_obj.name}"'

        return response

    except (ResultFile.DoesNotExist, FileNotFoundError):
        raise Http404











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
    
    return "List of Warnings <br>" + '\n'.join(warnings) + "\n\nList of Errors <br>" + '\n'.join(errors) 

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



def run_script(request):
    if request.method == 'POST':
        selected_files = request.POST.getlist('selected_files')
              
        # Convert the selected file IDs into UploadedFile objects
        uploaded_files = UploadedFile.objects.filter(id__in=selected_files)

        output_file = "output_panel.pcb"

        panelize_pcb(uploaded_files, 1, output_file)

        response = HttpResponse(content_type='application/pcb')
        response['Content-Disposition'] = 'attachment; filename="output_panel.pcb"'

        # Open the zip file in binary mode and write its content to the response
        with open(output_file, 'rb') as zip_file:
            response.write(zip_file.read())

        # Delete the temporary zip file
        os.remove(output_file)

        return response

    # Redirect to a relevant page if the request method is not POST
    return redirect('logged_home')  # Replace 'home' with the appropriate URL name


def panelize_pcb(uploaded_files, spacing, output_file):
    # Create a new board for the panelized version
    panel_board = pcbnew.BOARD()

    # Set the title of the board
    panel_board.board_title = "Panelized PCB"

    boards = []

    # Initialize variables for calculating panel dimensions
    max_width = 0
    total_height = 0

    # Panelize all the PCBs from the uploaded files
    for uploaded_file in uploaded_files:

        # Unzip the path
        uploaded_file_path_unzipped = "temp/"

        unzip_file(uploaded_file.file.path, uploaded_file_path_unzipped)


        # Get the uploaded file's path
        _, input_file_path_list = findKicadPcb(uploaded_file_path_unzipped)
        input_file_path = input_file_path_list[0]


        # Load the input PCB file
        board = pcbnew.LoadBoard(input_file_path)

        # Get the board dimensions
        board_width = board.GetBoardEdgesBoundingBox().GetWidth()
        board_height = board.GetBoardEdgesBoundingBox().GetHeight()

        # Update the maximum width and total height
        if board_width > max_width:
            max_width = board_width
        total_height += board_height

        # Add the board to the panelized board
        boards.append(board)

        # Remove all files in the output directory
        shutil.rmtree(uploaded_file_path_unzipped)

    # Calculate the panel dimensions
    panel_width = max_width
    panel_height = total_height + spacing * (len(uploaded_files) - 1)
    panel_board = pcbnew.BOARD()

    # Adjust the position of each PCB in the panel
    panel_origin_x = (panel_width - max_width) / 2
    panel_origin_y = 0

    for i in range(len(uploaded_files)):

        displacement = pcbnew.wxPoint(-panel_board.ComputeBoundingBox().GetWidth(), 0)

        board = boards[i]
        panel_board = merge_boards(panel_board, board, displacement)

    # Save the panelized board to the specified output file
    pcbnew.SaveBoard(output_file, panel_board)


def findKicadPcb(path):
    outputPath = []

    dirs = [os.path.join(path, x) for x in os.listdir(path) if os.path.isdir(os.path.join(path, x))]
    files = [os.path.join(path, x) for x in os.listdir(path) if os.path.isfile(os.path.join(path, x))]

    kicad_pcb_final = [x for x in files if x.endswith(".kicad_pcb")]

    while len(dirs) > 0 :
        dir = dirs[0]
        dirs.remove(dir)

        others, kicad_pcb = findKicadPcb(dir)

        for thing in others:
            if os.path.isdir(thing):
                dirs.append(thing)
            if os.path.isfile(thing) and thing.endswith(".kicad_pcb"):
                kicad_pcb_final.append(thing)
        for kicad_pcb_path in kicad_pcb:
            kicad_pcb_final.append(kicad_pcb_path)
        
    return dirs, kicad_pcb_final

def unzip_file(zip_file_path, output_directory):
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(output_directory)

def merge_boards(board1, board2, displacement):
    # Clone board2 to avoid modifying the original object
    merged_board = board2

    # Displace all modules and drawings in board2
    for module in merged_board.GetModules():
        module.Move(displacement)

    for drawing in merged_board.GetDrawings():
        drawing.Move(displacement)

    # Merge design settings and layers from board1
    merged_board.MergeAuxiliarySettingsFrom(board1)

    # Add modules and drawings from board1 to the merged board
    for module in board1.GetModules():
        module_copy = module.Clone()
        merged_board.Add(module_copy)

    for drawing in board1.GetDrawings():
        drawing_copy = drawing.Clone()
        merged_board.Add(drawing_copy)

    return merged_board