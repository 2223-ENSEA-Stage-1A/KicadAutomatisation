from django.utils import timezone
import os
import shutil
import tempfile

from myapp.models import PanelFile
from myapp.myscripts.checkThisProject import checkThisProject
from django.core.files import File

from myapp.myscripts.utilities import compress_folder_to_zip, copy_file_to_temp_folder

def update_panel_file(panel_file: PanelFile):

    name = f"{panel_file.user.username} {timezone.now().date()} {timezone.now().time()}"
    _, extracted_folder_path = copy_file_to_temp_folder(panel_file.kicad_pcb.path)
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


    resultFile = panel_file

    panel_file.filename=name
    panel_file.uploaded_at = timezone.now()

    panel_file.zippedGerbers.delete(save=False)
    panel_file.zippedGerbers = zippedGerbersf

    panel_file.zippedDrills.delete(save=False)
    panel_file.zippedDrills = zippedDrillsf

    panel_file.save()

    try: shutil.rmtree(temp_file_path)
    except: print("euh ?, Gerbers")