from contextlib import contextmanager
import os
import shutil
import tempfile
from urllib.parse import urlencode
import zipfile
from django.conf import settings
from django.shortcuts import render
import functools
import concurrent.futures

from django.core.files import File

from django.http import HttpResponse, HttpResponseNotFound
import subprocess
from .forms import GerberUploadForm
from django.contrib.auth.decorators import login_required

from django.shortcuts import redirect

from .models import PanelFile, UploadedFile, ResultFile

from myapp.forms import DepositForm

from django.utils import timezone

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404

from django.http import FileResponse, Http404

from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied

from .models import Ticket, Message, UploadedFile
from .forms import TicketForm, StaffResponseForm, MessageForm

from collections import defaultdict
import pcbnew

from django.db.models import Q
from django.db.models import Subquery

import time


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
            name = f"{request.user.username} {timezone.now().date()} {timezone.now().time()}"
            
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

def open_ticket(request, file_id):
    # Retrieve the ticket associated with the specified file_id
    ticket = get_object_or_404(Ticket, result_file__id=file_id)

    # Redirect to the ticket detail page
    return redirect('ticket_detail', ticket_id=ticket.id)

def open_ticket_panel(request, file_id):
    # Retrieve the ticket associated with the specified file_id
    ticket = get_object_or_404(Ticket, panel_file__id=file_id)

    # Redirect to the ticket detail page
    return redirect('ticket_detail', ticket_id=ticket.id)

def user_files(request):
    user = request.user  # Get the currently logged-in user
    selected_files = request.POST.getlist('selected_files')
    board_height = request.POST.getlist('board_height')
    board_width = request.POST.getlist('board_width')

    # Get the value of the "view_all_project" checkbox from the request
    view_all_project = request.GET.get('view_all_project') == "on"

    if user.is_staff and view_all_project:
        result_files = ResultFile.objects.all()
    else:
        result_files = ResultFile.objects.filter(user=user)

    # Get the ticket associated with each upload file (if it exists)
    files = []
    for result_file in result_files:
        ticket = Ticket.objects.filter(result_file=result_file).first()
        files.append({'upload_file': result_file, 'ticket': ticket})

    if len(files) == 0: files = None


    return render(request, 'user_files.html', {'selected_files':selected_files, 'board_height':board_height, 'board_width':board_width, 'files':files, 'view_all_project': view_all_project})




def user_panels(request):
    user = request.user  # Get the currently logged-in user
    selected_files = request.POST.getlist('selected_files')
    board_height = request.POST.getlist('board_height')
    board_width = request.POST.getlist('board_width')

    # Get the value of the "view_all_project" checkbox from the request
    view_all_project = request.GET.get('view_all_project') == "on"

    if user.is_staff and view_all_project:
        panel_files = PanelFile.objects.all()
    else:
        panel_files_tmp = PanelFile.objects.filter(uploaded_files__user=user)
        panel_files = []
        [panel_files.append(x) for x in panel_files_tmp if not x in panel_files]


    # Get the ticket associated with each upload file (if it exists)
    files = []
    for panel_file in panel_files:
        ticket = Ticket.objects.filter(panel_file=panel_file).first()
        files.append({'upload_file': panel_file, 'ticket': ticket})

    if len(files) == 0: files = None


    return render(request, 'user_panels.html', {'selected_files':selected_files, 'board_height':board_height, 'board_width':board_width, 'files':files, 'view_all_project': view_all_project})




@staff_member_required(login_url='login')
def panelizer_kicad(request):
    user = request.user  # Get the currently logged-in user
    selected_files = request.POST.getlist('selected_files')
    board_height = request.POST.getlist('board_height')
    board_width = request.POST.getlist('board_width')

    if user.is_staff:
        resultfiles = ResultFile.objects.all()
    else:
        resultfiles = ResultFile.objects.filter(user=user)


    
    return render(request, 'panelizer_kicad.html', {'resultfiles': resultfiles, 'selected_files':selected_files, 'board_height':board_height, 'board_width':board_width})


def delete_file(request):
    if request.method == 'POST':
        file_type = request.POST.get('file_type')
        file_id = request.POST.get('file_id')
        

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

            elif file_type == 'panel_file':
                file_obj = PanelFile.objects.get(id=file_id)
                file_obj.panel_file.delete(save=False)
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

# --------------------------------
# --------------------------------
#Panelize Stuff --------------------------------
# --------------------------------
# --------------------------------

def run_script(request):
    if request.method == 'POST':
        selected_files = request.POST.getlist('selected_files')
        maxHeight = int(request.POST.get('board_height'))
        maxWidth = int(request.POST.get('board_width'))
              
        # Convert the selected file IDs into UploadedFile objects
        uploaded_files = UploadedFile.objects.filter(id__in=selected_files)

        # Update the uploaded_files list based on the selected amount
        updated_uploaded_files = []
        for file_id, file in zip(selected_files, uploaded_files):
            amount = int(request.POST.get(f'amount_{file_id}', 1))
            updated_uploaded_files.extend([file] * amount)

        output_file = "output_panel.kicad_pcb"

        ShovedIn = panelize_pcb(updated_uploaded_files, 10, output_file, (pcbnew.FromMM(maxWidth), pcbnew.FromMM(maxHeight)))

        response = HttpResponse(content_type='application/kicad_pcb')
        response['Content-Disposition'] = 'attachment; filename="output_panel.kicad_pcb"'

        # Open the zip file in binary mode and write its content to the response
        output_file_data = open(output_file, 'rb')
        #response.write(output_file.read())

        # Delete the temporary zip file
        os.remove(output_file)

        myPanel = PanelFile.objects.create(                
                user=request.user,
                filename= ','.join(ShovedIn) + f"{timezone.now()}",
                panel_file=File(output_file_data),
                description="A panel composed of " + ','.join(ShovedIn),
                uploaded_at = timezone.now()
                )
        
        #myPanel.uploaded_files.set([File(uploaded_file) for uploaded_file in uploaded_files])

        for uploaded_file in uploaded_files:
            myPanel.uploaded_files.add(uploaded_file.id)
        
        query_params = urlencode({
            'selected_files': selected_files,
            'board_height': f"{maxHeight}",
            'board_width': f"{maxWidth}",
            'myPanel': myPanel.id,
            'filenames': [get_object_or_404(UploadedFile, id=file_id).filename for file_id in selected_files]  
        })



        return redirect(f"file-explorer/?{query_params}")  # Replace 'file_explorer' with the appropriate URL name
        return response

    # Redirect to a relevant page if the request method is not POST
    return redirect('logged_home')  # Replace 'home' with the appropriate URL name




def file_explorer_view(request):
    # Retrieve the selected_files and other parameters from the request if needed
    selected_files = request.GET.getlist('selected_files')
    maxHeight = int(request.GET.get('board_height'))
    maxWidth = int(request.GET.get('board_width'))
    myPanel_id = request.GET.get('myPanel')
    filenames = request.GET.getlist('filenames')
    
    # Pass the selected_files and other parameters to the template context
    context = {
        'selected_files': selected_files,
        'maxHeight': maxHeight,
        'maxWidth': maxWidth,
        'myPanel': myPanel_id,
        'filenames':filenames
    }

    return render(request, 'file_explorer.html', context)




def download_file_view(request):
    # Retrieve the selected_files and other parameters from the request
    myPanel_id = request.POST.get('myPanel')

    # Retrieve the myPanel object using the primary key (ID)
    myPanel = get_object_or_404(PanelFile, id=myPanel_id)

    # Prepare the file for download (e.g., generate or retrieve the file)
    file_path = myPanel.panel_file.path  # Replace with the actual file path

    # Open the file in binary mode and read its content
    with open(file_path, 'rb') as file:
        file_content = file.read()

    # Create the HTTP response with the file content
    response = HttpResponse(file_content, content_type='application/kicad_pcb')
    response['Content-Disposition'] = 'attachment; filename="output_panel.kicad_pcb"'

    # Delete the temporary file if needed
    os.remove(file_path)

    return response




def panelize_pcb(uploaded_files, spacing, output_file, boxSize):
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

    rectangles = [board.GetBoardEdgesBoundingBox() for board in boards]

    #displacement, order, Failed, ShovedIn, sortedboards = fit_rectangles(rectangles, boxSize, spacing, boards)
    #sortedboards, displacement = fitPolygon(boards, boxSize)
    result = fitPolygon(boards, boxSize, pcbnew.FromMM(2.5))
    sortedboards, displacement = zip(*result)
    print([(sortedb, dis) for sortedb, dis in zip(sortedboards, displacement)])

    #sortedboards.reverse() #to be uncommented using fit_rectangles

    #Board name of the board that has this box
    ShovedIn = [board.GetFileName() for board in boards]

    absolute_displacement = pcbnew.VECTOR2I(0,0)
    for i in range(len(sortedboards)):
        #j = order[i]
        phaseDisplacement = displacement[i] #j
        if not phaseDisplacement: continue

        board = sortedboards[i] #j
        phaseDisplacement -= absolute_displacement
        absolute_displacement += phaseDisplacement
 
        panel_board = merge_boards(panel_board, board, phaseDisplacement, f"-v{i}-") #j

    movePCB(panel_board, absolute_displacement)

    # Save the panelized board to the specified output file
    pcbnew.SaveBoard(output_file, panel_board)

    return ShovedIn #, Failed



def movePCB(pcb, displacement):
    # Remember existing elements in base
    tracks = pcb.GetTracks()
    footprints = pcb.GetFootprints()
    drawings = pcb.GetDrawings()
    zonescount = pcb.GetAreaCount()

    # Move
    for track in tracks:
        track.Move(-displacement)

    for footprint in footprints:
        footprint.Move(-displacement)

    for drawing in drawings:
        drawing.Move(-displacement)

    for i in range(0, zonescount):
        pcb.GetArea(i).Move(-displacement)


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

def merge_boards(board1, board2, displacement, postfix):
    # Clone board2 to avoid modifying the original object
    pcb = board1
    pcb_tmp = board2

    # Remember existing elements in base
    tracks = pcb.GetTracks()
    footprints = pcb.GetFootprints()
    drawings = pcb.GetDrawings()
    zonescount = pcb.GetAreaCount()


    # Determine new net names
    new_netnames = {}
    for i in range(1, pcb_tmp.GetNetCount()): # 0 is unconnected net
        name = pcb_tmp.FindNet(i).GetNetname()
        new_netnames[name] = name+postfix

    with tempfilename() as fname:
        # Write addon to temporary file
        pcbnew.SaveBoard(fname, pcb_tmp)

        # Replace net names in file
        pcbtext = None
        with open(fname) as fp:
            pcbtext = fp.read()

        for (old,new) in new_netnames.items():
            pcbtext = pcbtext.replace(old,new)

        with open(fname,'w') as fp:
            fp.write(pcbtext)

        # Append new board file with modified net names
        plugin = pcbnew.IO_MGR.PluginFind(pcbnew.IO_MGR.KICAD_SEXP)
        plugin.Load(fname, pcb)


        # Move
        for track in tracks:
            track.Move(displacement)

        for footprint in footprints:
            footprint.Move(displacement)

        for drawing in drawings:
            drawing.Move(displacement)

        for i in range(0, zonescount):
            pcb.GetArea(i).Move(displacement)


    return pcb

@contextmanager
def tempfilename():
    f = tempfile.NamedTemporaryFile(delete=False)
    try:
        f.close()
        yield f.name
    finally:
        try:
            os.unlink(f.name)
        except OSError:
            pass

import math

def fit_rectangles(rectangles, boxSize, spacing, boards):

    #Get biggest to smallest list of rect.

    def sortRect(rectanglesIn):

        rectangles = rectanglesIn.copy()
        
        max_x = 0
        max_y = 0

        biggestRect = None
        biggestRect_id = None

        sortedRectangles = []
        sortedboards = []
        order = []

        for i in range(len(rectangles)):
            minArea = math.inf
            indexA = 0
            for j in range(len(rectangles)):
                if not (j in order) and rectangles[j].GetArea() < minArea:
                    minArea = rectangles[j].GetArea()
                    indexA = j
            sortedboards.append(boards[indexA])
            sortedRectangles.append(rectangles[indexA])
            order.append(indexA)

                

        return sortedRectangles, order, sortedboards
    
    


    #Auxiliary function

    def isInsideBox(rect, box):
        return box.Contains(rect)

    def next(vector):
        x,y = vector
        if x == 0:
            return (y+1, 0)
        else:
            return (x-1, y+1)

    #add one rect to an already rect mess

    def putItIn(rectangles, box, rect):
        assert all([isInsideBox(rect, box) for rect in rectangles])
        x_offset = pcbnew.ToMM(rect.GetX())
        y_offset = pcbnew.ToMM(rect.GetY())
        delta_x = 0
        delta_y = 0
        delta_x_max = pcbnew.ToMM(box.GetWidth() - rect.GetWidth())
        delta_y_max = pcbnew.ToMM(box.GetHeight() - rect.GetHeight())



        tmp_rect = rect
        tmp_rect.SetOrigin(pcbnew.VECTOR2I(0,0))

        if len(rectangles) == 0 and isInsideBox(tmp_rect, box): return (pcbnew.VECTOR2I(pcbnew.FromMM(x_offset), pcbnew.FromMM(y_offset)), tmp_rect)

        ImGood = False

        
        while not ImGood and (delta_x <= delta_x_max or delta_y < delta_y_max):

            delta_x, delta_y = next((delta_x, delta_y)) #follow a zigzag filling pattern 2048 style
            ImGood = True

            tmp_rect = pcbnew.BOX2I(pcbnew.VECTOR2I(0,0), rect.GetSize())
            tmp_rect.Move(pcbnew.VECTOR2I(pcbnew.FromMM(delta_x), pcbnew.FromMM(delta_y)))
            

            if not isInsideBox(tmp_rect, box):
                ImGood = False
                continue

            for rectHost in rectangles:
                if tmp_rect.Intersects(rectHost):
                    ImGood = False
                    break
            

        return (pcbnew.VECTOR2I(pcbnew.FromMM(-delta_x + x_offset), pcbnew.FromMM(-delta_y + y_offset)), tmp_rect) if delta_x <= delta_x_max and delta_y <= delta_y_max else None
    
    #Loving chaos 

    def goForIt(rectanglesIn, box):
        rectangles = rectanglesIn.copy()
        shovedIn = []
        Failed = []
        translation_vectors = []


        while len(rectangles) != 0:


            rect = rectangles.pop()
            value = putItIn(shovedIn, box, rect)

            if not value:
                Failed.append(rect)
                translation_vectors.append(None) #append None
            else:
                vector, rectIn =  value
                translation_vectors.append(vector)
                shovedIn.append(rectIn)

        return shovedIn, Failed, translation_vectors
    

    #Mayhem Unlocked

    for rect in rectangles:
        rect.SetX(rect.GetX() - pcbnew.FromMM(spacing))
        rect.SetY(rect.GetY() - pcbnew.FromMM(spacing))
        rect.SetHeight(rect.GetHeight() + pcbnew.FromMM(spacing))
        rect.SetWidth(rect.GetWidth() + pcbnew.FromMM(spacing))

    xBox, yBox = boxSize
    box = pcbnew.BOX2I(pcbnew.VECTOR2I(0, 0),pcbnew.VECTOR2I(xBox, yBox))

    rotation_vectors = []
    translation_vectors = []
    order = []
    sortedboards = []

    sortedRectangles,order, sortedboards = sortRect(rectangles)
    shovedIn, Failed, translation_vectors = goForIt(sortedRectangles, box)

    return translation_vectors, order, Failed, shovedIn, sortedboards


def fitPolygon(boards, boxSize, spacing):

    """  @timeit
    def move_line_chain(line_chain, vector):
        new_line_chain = pcbnew.SHAPE_LINE_CHAIN()

        # Iterate over each point in the line chain
        for point_index in range(line_chain.GetPointCount()):
            point = line_chain.GetPoint(point_index)
            new_point = point + vector  # Add the vector to each point
            new_line_chain.Append(new_point)
        
        return new_line_chain """
    
    def move_line_chain(line_chain, vector):
        new_line_chain = pcbnew.SHAPE_LINE_CHAIN()

        # Iterate over each point in the line chain using list comprehension
        [new_line_chain.Append(line_chain.GetPoint(i) + vector) for i in range(line_chain.GetPointCount())]

        return new_line_chain
    
    def is_convex(shape_line):
        segment_count = shape_line.SegmentCount()
        sign = None

        for i in range(segment_count):
            prev_index = (i - 1 + segment_count) % segment_count
            current_index = i
            next_index = (i + 1) % segment_count

            prev_segment = shape_line.CSegment(prev_index)
            current_segment = shape_line.CSegment(current_index)
            next_segment = shape_line.CSegment(next_index)

            prev_vector = pcbnew.wxPoint(prev_segment.A.x - prev_segment.B.x, prev_segment.A.y - prev_segment.B.y)
            current_vector = pcbnew.wxPoint(current_segment.A.x - current_segment.B.x, current_segment.A.y - current_segment.B.y)
            next_vector = pcbnew.wxPoint(next_segment.A.x - next_segment.B.x, next_segment.A.y - next_segment.B.y)

            # Calculate cross product
            cross_product = (prev_vector.x * current_vector.y) - (prev_vector.y * current_vector.x)


            # Checking the bend direction
            if sign == 1 and cross_product < 0: return False
            if sign == -1 and cross_product > 0: return False 
            
            # Checking the bend, stil the same ? convexe
            sign = 1 if cross_product > 0 else -1

        return True
        
    def detect_inside_box(outline1, box):
        return box.BBox().Contains(outline1.BBox())
    
    def detect_inside_shape(outline1, outline2):
        height = max(outline1.BBox().GetHeight(), outline2.BBox().GetHeight())
        segment_count_1 = outline1.SegmentCount()
        segment_count_2 = outline2.SegmentCount()
        
        for i in range(segment_count_1):
            segment = pcbnew.SEG(outline1.Segment(i).A, outline1.Segment(i).A + pcbnew.VECTOR2I(0, height))
            intersectCount = 0
            for j in range(segment_count_2):
                segment2 = pcbnew.SEG(outline2.Segment(j))
                if segment.Intersects(segment2):
                    intersectCount += 1
            if intersectCount % 2 == 1:
                return True
        return False

    def center_inside_convex(outline1, outline2_list, box, clearance=0, convex=False):
        bbox1 = outline1.BBox()  # Calculate the bounding box of outline1 once
        if not is_convex(outline1): return False, None
        # Iterate over the outlines in outline2_list
        for outline2 in outline2_list:
            if outline2 and is_convex(outline2):
                bbox2 = outline2.BBox()  # Calculate the bounding box of outline2 once

                # Calculate the center point of bbox2
                center_x = (bbox1.GetX() + bbox1.GetX() + bbox1.GetWidth()) // 2
                center_y = (bbox1.GetY() + bbox1.GetY() + bbox1.GetHeight()) // 2
                center_point = pcbnew.VECTOR2I(center_x, center_y)

                # Check if the center point is inside outline1
                if bbox2.Contains(center_point):
                    return True, outline2
            
        return False, None
    
    def detect_intersection_outline(outline1, outline2_list, box, clearance=0, convex = False):
        if isinstance(outline2_list, list):
            bbox1 = outline1.BBox()  # Calculate outline1's bounding box once

            convex |= is_convex(outline1)
            before_convex = convex

            # Iterate over outlines in outline2_list
            for outline2 in outline2_list:
                before_convex = convex
                if outline2:
                    i = 0
                    bbox2 = outline2.BBox()  # Calculate outline2's bounding box once
                    before_convex |= is_convex(outline2)
                    
                    if bbox1.Intersects(bbox2):

                        # Iterate over segments in outline1
                        for i in range(outline1.SegmentCount()):
                            segment1 = outline1.CSegment(i)

                            # Iterate over segments in outline2
                            for j in range(outline2.SegmentCount()):
                                segment2 = outline2.CSegment(j)
                                i += 1

                                # Check if the segments intersect
                                if segment1.Intersects(segment2):
                                    return True, segment2
                        
            return False, None
        

    def find_intersection_outline(outline1, outline2_list, box, clearance=0, convex = False):
        if isinstance(outline2_list, list):
            bbox1 = outline1.BBox()  # Calculate outline1's bounding box once
            if is_convex(outline1):
                # Iterate over outlines in outline2_list
                for outline2 in outline2_list:
                    if outline2 and is_convex(outline2):
                        bbox2 = outline2.BBox()  # Calculate outline2's bounding box once
                        if bbox1.Intersects(bbox2):
                            return outline2
   
            return None

    
    def detect_intersection_segment(outline1, segment2, box, clearance=0):
        segment_count_1 = outline1.SegmentCount()

        for i in range(segment_count_1):
            segment1 = outline1.CSegment(i)

            if segment1.Intersects(segment2):
                return True, segment2
        return False, None

    def next(vector, spacing):
        if spacing < pcbnew.FromMM(1):
            spacing = pcbnew.FromMM(1)

        if(vector.x == 0):
            vector.x, vector.y = vector.y + spacing, 0
        else:
            vector.x, vector.y = vector.x - spacing, vector.y + spacing
        return vector

    def copy_outline(outline: pcbnew.SHAPE_LINE_CHAIN) -> pcbnew.SHAPE_LINE_CHAIN:
        return move_line_chain(outline, pcbnew.VECTOR2I(0,0))
    
    
    @timeit
    def arrange_outline(outline, arranged_outlines, box, spacing, current_positions):
        current_pos = pcbnew.VECTOR2I(0, 0)
        intersects = False
        max_x = box.BBox().GetWidth() - outline.BBox().GetWidth()
        max_y = box.BBox().GetHeight() - outline.BBox().GetHeight()
        p = 0
        k = 0
        l = 0
        skip = 0
        normal = 0
        while not intersects and (current_pos.x < max_x or current_pos.y < max_y):

            start = time.time()
            moved_outline = move_line_chain(outline, current_pos)

            center_inside_convex_bool, center_inside_convex_outline = center_inside_convex(moved_outline, arranged_outlines, box, spacing)

            if center_inside_convex_bool:

                outline2 = center_inside_convex_outline
                if outline2:
                    distance = min(moved_outline.BBox().GetWidth(), moved_outline.BBox().GetHeight())/2
                    distance = int(distance/(spacing)) if spacing != 0 else int(distance)
                    for _ in range(int(distance) if int(distance) != 0 else 1):
                        p += 1
                        current_pos = next(current_pos,spacing)
                        if current_pos.x == 0:
                            skip += - start + time.time()
                            break
                moved_outline = move_line_chain(outline, current_pos)
                skip += - start + time.time()
                               
            else:

                start = time.time()
                intersects_bool, seg = detect_intersection_outline(moved_outline, arranged_outlines, box, spacing)
                inside_bool = detect_inside_box(moved_outline, box)

                if not intersects_bool and inside_bool:
                    intersects = True
                    arranged_outlines.append(moved_outline)
                    current_positions.append(current_pos)
                    normal += - start + time.time()
                    print(k, "I'm outside ?", l, "I'm noraml") 
                    print(p, "i'm centered ?", skip, normal)
                    return

                elif intersects_bool and seg and inside_bool:
                    intersects_bool, seg = detect_intersection_segment(moved_outline, seg, box, spacing)
                    while intersects_bool and seg:
                        l += 1
                        current_pos = next(current_pos,spacing)
                        moved_outline = move_line_chain(outline, current_pos)
                        intersects_bool, seg = detect_intersection_segment(moved_outline, seg, box, spacing)
                
                elif not inside_bool:
                    
                    while (not inside_bool) and (current_pos.x < max_x or current_pos.y < max_y):
                        k += 1
                        current_pos = next(current_pos,spacing)
                        moved_outline = move_line_chain(outline, current_pos)
                        inside_bool = detect_inside_box(moved_outline, box)
                else:
                    l += 1
                    current_pos = next(current_pos, spacing)
                normal += - start + time.time()

        normal += - start + time.time()
        print(k, "I'm outside ?", l, "I'm noraml") 
        print(p, "i'm centered ?", skip, normal)
        arranged_outlines.append(None)
        current_positions.append(None)
        return
    
    def arrange_outlines(outlines, box, spacing):
        arranged_outlines = []
        current_positions = []
        for outline in outlines:
            print(outlines.index(outline))

            arrange_outline(outline, arranged_outlines, box, spacing, current_positions)


        return arranged_outlines, current_positions 
    
    def removeArcs(outline: pcbnew.SHAPE_LINE_CHAIN) -> None:
        start = None
        end = None
        started = False
        terminated = True
        for i in range(outline.GetPointCount()):
            if outline.IsArcStart(i):
                start = i
                started = True
            if started and outline.IsArcEnd(i):
                end = i
                started = False
                terminated = False
            if not terminated:
                outline.Append(pcbnew.SEG(start, end))
                terminated = True





    Stuff = {
        'box': None, # Unique
        'boards': boards, # OneToOne
        'polygons': [pcbnew.SHAPE_POLY_SET() for _ in boards], # OneToOne
        'outlines': [], # OneToOne
        'zeroedOutlines': [], # OneToOne
        'displacement': [], # OneToOne
        'Area': [], # OneToOne
        'ArangedOutline': [], #OneToOne
        'zeroingDisplacement': [], #OneToOne
        'fullDisplacement': [], #OneToOne
    }

    spacing = spacing if spacing != 0 else pcbnew.FromMM(1)

    [board.GetBoardPolygonOutlines(polygon) for board, polygon in zip(boards, Stuff['polygons'])]

    x,y = boxSize
    Stuff['box'] = pcbnew.SHAPE_RECT(pcbnew.BOX2I(pcbnew.VECTOR2I(0,0), pcbnew.VECTOR2I(x,y))).Outline()

    [polygon.Inflate(spacing//2, 0) for polygon in Stuff['polygons']] #spacing ?

    Stuff['outlines'] = [polygon.Outline(0) for polygon in Stuff['polygons']] 
    
    

    for outline in Stuff['outlines']:
        outline.ClearArcs()
        removeArcs(outline)
        outline.SetClosed(True)
        outline.Simplify(True)
        zeroedOutline = move_line_chain(outline, -pcbnew.VECTOR2I(outline.BBox().GetX(), outline.BBox().GetY()))
        Stuff['zeroedOutlines'].append(zeroedOutline)
        Stuff['zeroingDisplacement'].append(pcbnew.VECTOR2I(outline.BBox().GetX(), outline.BBox().GetY()))
        Stuff['Area'].append(zeroedOutline.BBox().GetArea())

    # Sort the 'Area' list in ascending order and move other lists accordingly
    sorted_data = zip(Stuff['Area'], Stuff['boards'], Stuff['polygons'], Stuff['outlines'], Stuff['zeroedOutlines'], Stuff['zeroingDisplacement'])
    sorted_data = sorted(sorted_data, key=lambda x: x[0], reverse=True)

    # Unpack the sorted data into separate lists
    Stuff['Area'], Stuff['boards'], Stuff['polygons'], Stuff['outlines'], Stuff['zeroedOutlines'], Stuff['zeroingDisplacement'] = zip(*sorted_data)

    Stuff['ArangedOutline'], Stuff['displacement'] = arrange_outlines(Stuff['zeroedOutlines'], Stuff['box'], spacing)

    for displacement, zeroingDisplacement in zip(Stuff['displacement'], Stuff['zeroingDisplacement']):
        if not displacement:
            Stuff['fullDisplacement'].append(None)
            print(zeroingDisplacement)
        else: Stuff['fullDisplacement'].append(zeroingDisplacement - displacement); print(zeroingDisplacement, displacement, zeroingDisplacement - displacement)

        

    return list(zip(Stuff['boards'], Stuff['fullDisplacement']))
    


        

    


@login_required
def ticket_list(request):
    # Get the current user
    user = request.user

    # Get the value of the "view_all_tickets" checkbox from the request
    view_all_tickets = request.GET.get('view_all_tickets')

    # Get the tickets based on the user's role and checkbox value
    if user.is_staff and view_all_tickets:
        # Staff user and "view_all_tickets" checkbox is checked, see all tickets
        tickets = Ticket.objects.all()
    else:
        # Regular user or "view_all_tickets" checkbox is not checked, see own tickets and co-user tickets
        tickets = Ticket.objects.filter(Q(user=user) | Q(co_users=user))

    context = {
        'tickets': tickets,
        'view_all_tickets': view_all_tickets
    }
    return render(request, 'ticket_list.html', context)






def ticket_delete(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if request.method == 'POST':
        ticket.delete()
        return redirect('ticket_list')
    
    return redirect('ticket_detail', ticket_id=ticket_id)

@login_required
def create_ticket(request):

    if request.method == 'POST':
        form = TicketForm(request.POST, user=request.user)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.save()
            form.save_m2m()  # Save the selected co-users
            return redirect('ticket_detail', ticket.id)
    else:
        form = TicketForm(user=request.user)
    return render(request, 'ticket_create.html', {'form': form})

@login_required
def create_ticket_from(request, file_id):
    result_file = ResultFile.objects.get(id=file_id)

    if request.method == 'POST':
        form = TicketForm(request.POST, user=request.user)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.result_file = result_file
            ticket.save()
            form.save_m2m()
            return redirect('ticket_detail', ticket.id)
    else:
        form = TicketForm(user=request.user, result_file_id=result_file.id)  # Pass the result_file_id

    return render(request, 'ticket_create.html', {'form': form, 'result_file': result_file})

@login_required
def create_ticket_panel(request, file_id):
    panel_file = PanelFile.objects.all().filter(id=file_id).first()

    if request.method == 'POST':
        form = TicketForm(request.POST, user=request.user)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.panel_file = panel_file
            ticket.save()
            form.save_m2m()
            return redirect('ticket_detail', ticket.id)
    else:
        form = TicketForm(user=request.user, panel_file_id=panel_file.id)  # Pass the result_file_id

    return render(request, 'ticket_create.html', {'form': form, 'panel_file': panel_file})

def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    messages = ticket.messages.all().order_by('created_at')
    form = MessageForm()

    if request.method == 'POST':

        # Check if user clicked "Reopen Ticket" button and a reopen request has been made
        if 'useless_ticket' in request.POST and ticket.resolved and ticket.reopen_requested:     
            return redirect('ticket_list')


        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.ticket = ticket
            message.sender = request.user
            message.answeredByStaff = True if 'staff_response' in request.POST or 'unresolve_ticket' in request.POST else False
            message.save()
            form = MessageForm()

            # Check if staff member clicked "Unresolve Ticket" button
            if 'unresolve_ticket' in request.POST and request.user.is_staff:
                
                ticket.resolved = False
                ticket.save()

            # Check if user clicked "Reopen Ticket" button and a reopen request hasn't been made
            if 'reopen_ticket' in request.POST and ticket.resolved and not ticket.reopen_requested:
                ticket.reopen_requested = True
                ticket.save()
            
            
            


    resolved = ticket.resolved  # Check if ticket is resolved

    return render(request, 'ticket_detail.html', {
        'ticket': ticket,
        'messages': messages,
        'form': form,
        'user': request.user,
        'resolved': resolved,  # Pass the 'resolved' variable to the template
    })



@login_required
def ticket_answer(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    if request.method == 'POST':
        form = StaffResponseForm(request.POST)
        if form.is_valid():
            ticket.staff_response = form.cleaned_data['response']
            ticket.resolved = True
            ticket.save()
            return redirect('ticket_list')
    else:
        form = StaffResponseForm()
    return render(request, 'ticket_answer.html', {'ticket': ticket, 'form': form})


@login_required
def ticket_resolve(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id, user=request.user)
    ticket.resolved = True
    ticket.save()
    return redirect('ticket_detail', ticket_id=ticket_id)

def edit_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if request.method == 'POST':
        form = TicketForm(request.POST, instance=ticket, user=request.user)
        if form.is_valid():
            form.save()
            form.save_m2m()  # Save the updated co-users
            return redirect('ticket_detail', ticket.id)
    else:
        form = TicketForm(instance=ticket, initial={'co_users': ticket.co_users.all()})
    return render(request, 'edit_ticket.html', {'form': form, 'ticket': ticket})



def timeit(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Function '{func.__name__}' took {execution_time:.6f} seconds to execute.")
        return result
    return wrapper

