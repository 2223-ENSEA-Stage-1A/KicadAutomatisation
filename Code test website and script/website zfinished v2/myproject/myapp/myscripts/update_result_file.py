from django.utils import timezone
import os
import shutil
import tempfile

from myapp.models import ResultFile
from myapp.myscripts.utilities import compress_folder_to_zip, extract_zip
from myapp.myscripts.checkThisProject import checkThisProject
from django.core.files import File

def update_result_file(result_file: ResultFile):

    name = f"{result_file.user.username} {timezone.now().date()} {timezone.now().time()}"
    extracted_folder_path = extract_zip(result_file.uploaded_file.file.path)
    temp_file_path = tempfile.mkdtemp()
    result = checkThisProject(extracted_folder_path, name, "myapp/myscripts/configs", temp_file_path)
    
    (drc_warning, drc_warnings, drc_error, drc_errors, drc_types,
    erc_warning, erc_warnings, erc_error, erc_errors, 
    raw_gerber_and_drill_result,
    pcbCat, doAble) = result

    
    drcs = [os.path.join(temp_file_path, x) for x in os.listdir() if "-drc.txt" in x]
    ercs = [os.path.join(temp_file_path, x) for x in os.listdir() if "-erc.txt" in x]

    if(len(drcs) == 1 and os.path.isfile(drcs[0])):
        DRCresultf = open(drcs[0], 'rb')
    else: DRCresultf = None

    if(len(ercs) == 1 and os.path.isfile(ercs[0])):
        ERCresultf = open(ercs[0], 'rb')
    else: ERCresultf = None


    zippedGerbersf = open(compress_folder_to_zip(os.path.join(temp_file_path, "Gerbers")), 'rb')
    zippedDrillsf = open(compress_folder_to_zip(os.path.join(temp_file_path, "Drills")), 'rb')

    # Convert file objects to Django's File objects
    zippedGerbersf = File(zippedGerbersf)
    zippedDrillsf = File(zippedDrillsf)
    DRCresultf = File(DRCresultf) if DRCresultf else None
    ERCresultf = File(ERCresultf) if ERCresultf else None

    uploadedFile = result_file.uploaded_file

    uploadedFile.filename=name
    uploadedFile.uploaded_at = timezone.now()

    uploadedFile.save()
    
    resultFile = result_file

    resultFile.filename=name
    resultFile.uploaded_at = timezone.now()

    resultFile.zippedGerbers.delete(save=False)
    resultFile.zippedGerbers = zippedGerbersf

    resultFile.zippedDrills.delete(save=False)
    resultFile.zippedDrills = zippedDrillsf

    resultFile.DRCresult.delete(save=False)
    resultFile.DRCresult = DRCresultf

    resultFile.ERCresult.delete(save=False)
    resultFile.ERCresult = ERCresultf

    resultFile.save()

    result_file_id = resultFile.id



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
    return context
