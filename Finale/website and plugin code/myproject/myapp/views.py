from contextlib import contextmanager
from urllib.parse import urlencode
from django.urls import reverse


import os
import threading

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required

from django.shortcuts import redirect, get_object_or_404, render
from django.template.loader import render_to_string

from django.http import JsonResponse, HttpResponse, FileResponse, Http404


from django.db.models import Q

from django.conf import settings
from myapp.myscripts.panelize_pcb_task import panelize_pcb_task
from myapp.myscripts.update_panel_file import update_panel_file
from myapp.myscripts.update_result_file import update_result_file
from myapp.myscripts.utilities import clear_messages, save_gerber_file

from .forms import DRCForm, GerberUploadForm, PanelFileForm, ResultFileForm
from .models import AuthorizedError, PanelFile, ProductionStep, UploadedFile, ResultFile
from myapp.forms import DepositForm
from .models import Ticket, UploadedFile
from .forms import TicketForm, StaffResponseForm, MessageForm

from myapp.myscripts.deposit_project import deposit_project

import myapp.myscripts.config as config

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
    context = {}  # Assign a default value to the context variable
    if request.method == 'POST':
        form = DepositForm(request.POST, request.FILES)
        if form.is_valid():

            request.session['finished'] = False
            request.session.save()

            #messages.warning(request, f"Filed submitted successfully, Analysis can take up to 2 minutes. Please Be Patient.")

            try: response = deposit_project(request)
            except: response = render(request, 'error_deposit.html')

            return response
        
    else:  # GET request
        form = DepositForm()

    return render(request, 'logged_home.html', {'form': form})



def gerber_result(request):
    context_from_data = request.session.get('context_from_data')

    not_authorized_error = False
    valid = True

    if context_from_data:
        if request.method == 'POST':
            form = DRCForm(context_from_data['drc_types'], request.POST) if context_from_data['drc_types'] else DRCForm([], request.POST)
            if form.is_valid():
                context_from_data["form"] = form
                authorized_drc_types = AuthorizedError.objects.get(id=1).authorized_error_names

                for drc_type, value in form.cleaned_data.items():
                    clear_messages(request)
                    if value and drc_type not in authorized_drc_types:
                        messages.error(request, f"Error '{drc_type}' is not allowed to be ignored.")
                        not_authorized_error = True
                    if not value:
                        valid = False
                result_file = ResultFile.objects.get(id=context_from_data["result_file_id"])
                result_file.valid = valid
                result_file.save()
                if not_authorized_error:
                    return render(request, 'gerber_result.html', context_from_data)

                # Process the form data and redirect or render success message
                del request.session['context_from_data']
                return render(request, 'gerber_success.html', context_from_data)
        else:
            form = DRCForm(context_from_data['drc_types']) if context_from_data['drc_types'] else DRCForm([])  # Use the existing DRCForm
    else:
        form = DRCForm(["You have to wait LMAO"])
    context_from_data["form"] = form
    return render(request, 'gerber_result.html', context_from_data)

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

def gerber_edit(request, file_id, ticket_id = None):
    # Retrieve the UploadedFile object based on the file_id
    try:
        result_file = ResultFile.objects.get(id=file_id)
    except ResultFile.DoesNotExist:
        # Handle the case where the UploadedFile object doesn't exist
        # You can return an error response or redirect to an appropriate page
        return render(request, 'error.html', {'message': 'Uploaded file not found'})

    context = {
        'result_file': result_file, 
        'ticket_id': ticket_id, 
    }

    if result_file.locked:
        return render(request, 'gerber_edit.html', context)

    if request.method == 'POST':
        form = ResultFileForm(request.POST, request.FILES, instance=result_file)
        form2 = DRCForm(result_file.Errors.errors_names, request.POST) if result_file.Errors.errors_names else DRCForm([], request.POST)
        context['form'] = form
        context['form2'] = form2
        if form.is_valid():
            form.save()
            result_file.uploaded_file.file.delete(save = False)
            result_file.uploaded_file.file = form.cleaned_data['uploaded_file']
            result_file.version += 1
            result_file.save()
            result_file.uploaded_file.save()
            data = update_result_file(result_file)
            request.session['context_from_data'] = data

        
            return redirect('gerber_result')
        
        if form2.is_valid():
            authorized_drc_types = AuthorizedError.objects.get(id=1).authorized_error_names
            valid = True
            authorized_errors = True
            for drc_type, value in form2.cleaned_data.items():
                if value and not drc_type in authorized_drc_types:
                    authorized_errors = False
                if not value:
                    valid = False
            result_file = ResultFile.objects.get(id=result_file.id)
            result_file.valid = valid and authorized_errors
            result_file.save()
            context['failed_form2_nae'] = authorized_errors
            context['failed_form2_nas'] = valid


            return render(request, 'gerber_edit.html', context)
            

    else:
        form = ResultFileForm(instance=result_file)
        context['form'] = form
        context['form2'] = DRCForm(result_file.Errors.errors_names, request.POST) if result_file.Errors.errors_names else DRCForm([], request.POST)

    

    # Render the template or return an appropriate response
    return render(request, 'gerber_edit.html', context)

def panel_edit(request, file_id, ticket_id = None):
    # Retrieve the PanelFile object based on the file_id
    try:
        panel_file = PanelFile.objects.get(id=file_id)
    except PanelFile.DoesNotExist:
        # Handle the case where the PanelFile object doesn't exist
        # You can return an error response or redirect to an appropriate page
        return render(request, 'error.html', {'message': 'Panel file not found'})

    context = {
        'panel_file': panel_file,
    }

    if request.method == 'POST':
        form = PanelFileForm(request.POST, request.FILES, instance=panel_file)
        context['form'] = form
        if form.is_valid():
            form.save()
            panel_file.panel_file.delete(save=False)
            panel_file.panel_file = form.cleaned_data['panel_file']
            panel_file.kicad_pcb.delete(save=False)
            panel_file.kicad_pcb = form.cleaned_data['panel_file']
            panel_file.save()

            update_panel_file(panel_file)

            return redirect('panel_result')
    else:
        form = PanelFileForm(instance=panel_file)
        context['form'] = form

    # Render the template or return an appropriate response
    return render(request, 'panel_edit.html', context)

def user_files(request):
    user = request.user  # Get the currently logged-in user
    selected_files = request.POST.getlist('selected_files')
    board_height = request.POST.getlist('board_height')
    board_width = request.POST.getlist('board_width')

    # Get the value of the "view_all_project" checkbox from the request
    view_all_project = request.POST.get('view_all_project', False) == 'on'
    view_valid = request.POST.get('view_valid', False) == 'on'

    if user.is_staff and view_all_project:
        result_files = ResultFile.objects.all()
    else:
        result_files = ResultFile.objects.filter(user=user)

    

    if view_valid: result_files = result_files.filter(valid=True)

    # Get the ticket associated with each upload file (if it exists)
    files = []
    for result_file in result_files:
        ticket = Ticket.objects.filter(result_file=result_file).first()
        files.append({'upload_file': result_file, 'ticket': ticket})

    if len(files) == 0: files = None



    return render(request, 'user_files.html', {'selected_files':selected_files, 'board_height':board_height, 'board_width':board_width, 'files':files, 'view_all_project': view_all_project, 'view_valid':view_valid,})

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
        panel_files_tmp = PanelFile.objects.filter(result_files__user=user)
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
    fit_mode = request.POST.getlist('fit_mode')
    spacing = request.POST.getlist('spacing')

    if user.is_staff:
        resultfiles = ResultFile.objects.all().filter(isToProduce = True)
    else:
        resultfiles = ResultFile.objects.filter(user=user)

    context = {'resultfiles': resultfiles, 
               'selected_files':selected_files, 
               'board_height':board_height, 
               'board_width':board_width,
               'fit_mode': fit_mode,
               'spacing': spacing,
               }
    
    return render(request, 'panelizer_kicad.html', context)

def error_handler(request):
    return render(request, 'error.html')

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
                for result_file in file_obj.result_files.all():
                    result_file.locked = PanelFile.result_files.through.objects.filter(resultfile=result_file).count() > 1
                    result_file.isInProduction = PanelFile.result_files.through.objects.filter(resultfile=result_file).count() > 1
                    result_file.save()
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

        elif file_type == 'zippedGerbers_panel':
            file_obj = PanelFile.objects.get(id=file_id).zippedGerbers
        elif file_type == 'zippedDrills_panel':
            file_obj = PanelFile.objects.get(id=file_id).zippedDrills
        elif file_type == 'kicad_pcb_file_panel':
            file_obj = PanelFile.objects.get(id=file_id).kicad_pcb

        elif file_type == 'DRCresult':
            file_obj = ResultFile.objects.get(id=file_id).DRCresult
        elif file_type == 'ERCresult':
            file_obj = ResultFile.objects.get(id=file_id).ERCresult
        elif file_type == 'uploaded_file':
            file_obj = ResultFile.objects.get(id=file_id).uploaded_file.file
        elif file_type == 'pdf_file':
            file_obj = ResultFile.objects.get(id=file_id).pdf_file.file
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

def send_project_prod(request, project_id):
    result_file = ResultFile.objects.get(id=project_id)
    if result_file.valid or request.user.is_staff:
        result_file.isToProduce = True
        result_file.productionStep = ProductionStep.OPTION_1
        result_file.amount += 1 if  result_file.amount >= 0 else 1 - result_file.amount
        result_file.save()
        

    return redirect('user_files')

def remove_project_prod(request, project_id):
    result_file = ResultFile.objects.get(id=project_id)
    if result_file.valid or request.user.is_staff:
        result_file.isToProduce = True if result_file.amount > 1 else False
        result_file.amount -= 1 if  result_file.amount > 0 else 0 
        result_file.save()
        

    return redirect('user_files')

def send_panel_prod(request, panel_id):
    panel_file = PanelFile.objects.get(id=panel_id)
    if request.user.is_staff:
        panel_file.isToProduce = True
        panel_file.isProduced = False
        panel_file.productionStep = ProductionStep.OPTION_1
        panel_file.update_status()
        panel_file.save()
        

    return redirect('user_panels')

def remove_panel_prod(request, panel_id):
    panel_file = PanelFile.objects.get(id=panel_id)
    if request.user.is_staff:
        panel_file.isToProduce = False
        panel_file.productionStep = ProductionStep.OPTION_1
        panel_file.update_status()
        panel_file.save()
        

    return redirect('user_panels')

def next_step_panel(request, panel_id):
    panel_file = PanelFile.objects.get(id=panel_id)
    if request.user.is_staff and panel_file.isToProduce:
        print(panel_file.isInProduction, panel_file.productionStep)
        panel_file.isInProduction = True
        check = panel_file.next_step()
        if not check:
            panel_file.isProduced = True
            panel_file.isToProduce = False
            panel_file.isInProduction = False

        panel_file.update_status()
        panel_file.save()
    
    return redirect('user_panels')

def previous_step_panel(request, panel_id):
    panel_file = PanelFile.objects.get(id=panel_id)
    if request.user.is_staff and panel_file.isToProduce:

        check = panel_file.previous_step()
        if not check:
            panel_file.isInProduction = False

        panel_file.update_status()
        panel_file.save()
    
    return redirect('user_panels')

def step_panel(request, panel_id):
    panel_file = PanelFile.objects.get(id=panel_id)
    if panel_file.isToProduce:
        panel_file.isToProduce = False
        panel_file.isInProduction = True
        panel_file.productionStep = ProductionStep.choices[0][0]

    elif panel_file.isInProduction:
        panel_file.isToProduce = False
        panel_file.isInProduction = True
        panel_file.next_step()
    
    if panel_file.productionStep == ProductionStep.choices[-1][0]:
        panel_file.isProduced = True
        panel_file.isInProduction = False
        panel_file.isToProduce = False

    panel_file.update_status()
    panel_file.save()
    
    return redirect('user_panels') 


#---------------------------
# --------------------------------
#Panelize Stuff --------------------------------
# --------------------------------
# --------------------------------


def run_script(request):
    if request.method == 'POST':
        selected_files = request.POST.getlist('selected_files')
        maxHeight = float(request.POST.get('board_height'))
        maxWidth = float(request.POST.get('board_width'))
        fit_mode = request.POST.get('fit_mode')
        spacing = float(request.POST.get('spacing'))

        output_file = "output_panel.kicad_pcb"

        # Call the panelize_pcb_task asynchronously
        thread = threading.Thread(target=panelize_pcb_task, args=(selected_files, maxHeight, maxWidth, spacing, fit_mode, request, output_file))
        thread.start()

        # For example, you can store it in the session
        request.session['progress'] = 0
        request.session['redirect_url'] = None
        request.session.save()

        # Render a web page to the user while the task is running
        get_progress(request)
        return render(request, 'progress.html')

    # Redirect to a relevant page if the request method is not POST
    return redirect('logged_home')  # Replace 'home' with the appropriate URL name

def get_progress(request):

    progress = request.session['progress']
    redirect_url = request.session['redirect_url']

    print(config.run_script_ad, config.max_run_script_run)

    data = {'progress': progress + (config.run_script_ad / config.max_run_script_run * 74) if progress == 11 and config.run_script_ad and config.max_run_script_run != 0 else progress,
            'redirect_url': redirect_url,
            }

    return JsonResponse(data)

def file_explorer_view(request):
    # Retrieve the selected_files and other parameters from the request if needed
    selected_files = request.GET.getlist('selected_files')
    maxHeight = float(request.GET.get('board_height'))
    maxWidth = float(request.GET.get('board_width'))
    spacing = float(request.GET.get('spacing'))
    fit_mode = request.GET.get('fit_mode')
    myPanel_id = request.GET.get('myPanel')
    filenames = request.GET.getlist('filenames')
    
    # Pass the selected_files and other parameters to the template context
    context = {
        'selected_files': selected_files,
        'maxHeight': maxHeight,
        'maxWidth': maxWidth,
        'myPanel': myPanel_id,
        'filenames': filenames,
        'fit_mode': fit_mode,
        'spacing': spacing,
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

