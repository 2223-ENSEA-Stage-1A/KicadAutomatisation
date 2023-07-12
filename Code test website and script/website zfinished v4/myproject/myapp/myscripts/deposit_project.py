from django.utils import timezone
import os
import shutil
import tempfile
from django.shortcuts import redirect

from django.urls import reverse
from myapp.forms import DepositForm
from myapp.models import ResultFile, UploadedFile, Drc_error
from myapp.myscripts.checkThisProject import checkThisProject
from django.core.files import File

from myapp.myscripts.utilities import compress_folder_to_zip, extract_zip, handle_uploaded_file

def deposit_project(request):
    form = DepositForm(request.POST, request.FILES)
    if not form.is_valid():
        return
    description = form.cleaned_data['description']
    uploaded_file = request.FILES['file']
    name = f"{request.user.username} {timezone.now().date()} {timezone.now().time()}"
    
    file_path = handle_uploaded_file(uploaded_file, name)

    extracted_folder_path = extract_zip(file_path)

    temp_file_path = tempfile.mkdtemp()

    result = checkThisProject(extracted_folder_path, name, "myapp/myscripts/configs", temp_file_path)

    (drc_warning, drc_warnings, drc_error, drc_errors, drc_types,
    erc_warning, erc_warnings, erc_error, erc_errors, 
    raw_gerber_and_drill_result,
    pcbCat, doAble) = result

    
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

    uploadedFile = UploadedFile.objects.filter(user=request.user, filename=name, description=description).first()
    count = UploadedFile.objects.filter(user=request.user, filename=name, description=description).count()
    if count == 0:
        # Create a new UploadedFile instance and save it to the database
        uploadedFile = UploadedFile.objects.create(
            user=request.user,
            filename=name,
            file=uploaded_file,
            description=description,
            uploaded_at = timezone.now()
        )
    else:
        uploadedFile.user=request.user
        uploadedFile.filename=name
        uploadedFile.file=uploaded_file
        uploadedFile.description=description
        uploadedFile.uploaded_at = timezone.now()
    
    resultFile = ResultFile.objects.all().filter(user=request.user).filter(filename=name).filter(description=description).filter(uploaded_file=uploadedFile).first()
    count = ResultFile.objects.all().filter(user=request.user).filter(filename=name).filter(description=description).filter(uploaded_file=uploadedFile).count()
    
    print("here")

    if count == 0:
        drc_error_object = Drc_error.objects.create()
        if drc_types: drc_error_object.errors_names = drc_types
        drc_error_object.save()

        resultFile = ResultFile.objects.create(
            user=request.user,
            filename=name,
            description=description,
            uploaded_at = timezone.now(),
            zippedGerbers = zippedGerbersf,
            zippedDrills = zippedDrillsf,
            DRCresult = DRCresultf,
            ERCresult = ERCresultf,
            uploaded_file = uploadedFile,
            Errors = drc_error_object
        )
        
    else :
        resultFile.user=request.user
        resultFile.filename=name
        resultFile.description=description
        resultFile.uploaded_at = timezone.now()
        resultFile.zippedGerbers = zippedGerbersf
        resultFile.zippedDrills = zippedDrillsf
        resultFile.DRCresult = DRCresultf
        resultFile.ERCresult = ERCresultf
        resultFile.uploaded_file = uploadedFile
        resultFile.Errors = drc_types

    resultFile.save()
    
    print("finished ?")

    result_file_id = resultFile.id

    print(os.getcwd())

    try: shutil.rmtree('Gerbers')
    except: print("euh ?, Gerbers")

    try: shutil.rmtree('Drills')
    except: print("euh ?, Drills")

    try: shutil.rmtree(f"ProjectToProcess")
    except: print("euh ?, ProjectToProcess/")   

    try: os.remove('Gerbers.zip')
    except: print("Gerber")

    try: os.remove('Drills.zip')
    except: print("Drills")

    try: 
        for drc in drcs:
            os.remove(drc)
    except: print("euh ?, drc")

    try:             
        for erc in ercs:
            os.remove(erc)
    except: print("euh ?, erc")

    context = {
    'doAble': doAble,   
    'drc_warning': drc_warning,
    'drc_warnings': drc_warnings,
    'drc_error': drc_error,
    'drc_errors': drc_errors,
    'erc_warning': erc_warning,
    'erc_warnings': erc_warnings,
    'erc_error': erc_error,
    'erc_errors': erc_errors,
    'pcbCat': pcbCat,
    'drc_types': drc_types,
    'result_file_id': result_file_id,
    }

    request.session['context_from_data'] = context
    request.session['progress'] = 100
    request.session['redirect_url'] = reverse('gerber_result')
    request.session.save()

    return redirect('gerber_result')
