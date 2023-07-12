import os
from myapp.myscripts.getStatisticsFromBoard import getMeasurement
import subprocess

def checkThisProject(path, name, configPath, temp_file_path):
    #print(f"je suis là : {os.getcwd()}")
    #print(f"Je suis lancé avec les arguments {path}, {name} et {configPath}")

    warnings = []
    errors = []
    raw = []
    

    _, KicadPcb_pathList = findKicadPcb(path) #find kicad_pcb
    if(len(KicadPcb_pathList) == 1): KicadPcb_path = KicadPcb_pathList[0]#; print(f"I will use {KicadPcb_path}")  #Use the only one found
    if(len(KicadPcb_pathList) > 1): KicadPcb_path = KicadPcb_pathList[0]#; print(f"Only {KicadPcb_pathList[0]} will be used !") #Use the first one found if multiple submitted

    trackSize, clearance, viaSize, numberOfCopperLayer = getMeasurement(KicadPcb_path)

    pcbCat, doAble = categorize(trackSize, clearance, viaSize, numberOfCopperLayer)

    if(doAble): 
        doKibotStuff(KicadPcb_path, configPath, temp_file_path) #doesKibotStuff
        #Load all the created files and Storing them

        drcs = [x for x in os.listdir() if "-drc.txt" in x]
        ercs = [x for x in os.listdir() if "-erc.txt" in x]


        if(len(drcs) > 0 and os.path.isfile(drcs[0])):
            DRCresultf = open(drcs[0], 'r')
            drc_warning, drc_warnings, drc_error, drc_errors, drc_types = handle_drc_result(DRCresultf.readlines())
        else: DRCresultf = None; drc_warning = drc_warnings = drc_error = drc_errors = drc_types = None

        if(len(ercs) > 0 and os.path.isfile(ercs[0])):
            ERCresultf = open(ercs[0], 'r')
            erc_warning, erc_warnings, erc_error, erc_errors = handle_erc_result(ERCresultf.readlines())
        else: ERCresultf = None; erc_warning = erc_warnings = erc_error = erc_errors = None



        
        

    return (drc_warning, drc_warnings, drc_error, drc_errors, drc_types,
            erc_warning, erc_warnings, erc_error, erc_errors, 
            None,
            pcbCat, doAble)
    

    

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

def doKibotStuff(KicadPcb_path, configPath, temp_file_path):
    executeKicadAction(KicadPcb_path, configPath, "drc", temp_file_path)
    executeKicadAction(KicadPcb_path, configPath, "erc", temp_file_path)
    executeKicadAction(KicadPcb_path, configPath, "gerberAndDrill", temp_file_path)
    return 

def handle_drc_result(input):

    ingress_val = ""
    ingress_bool = False

    
    warnings = []
    warning = False
    errors = []
    error = False

    types = []

    for line in input:
        line = str(line).strip()
        
        if line.startswith("["):

            index = line.index("]")
            if line[1:index] not in types: types.append(line[1:index]) 

            #stop current
            ingress_bool = False

            if "Severity: warning" in ingress_val:
                warnings.append(ingress_val)
            elif "Severity: error" in ingress_val:
                errors.append(ingress_val)
            ingress_val = ""

            #begin new

            ingress_bool = True
            ingress_val += ' ' + line

        
        elif line.startswith("**"):
            #end all
            ingress_bool = False

            if "Severity: warning" in ingress_val:
                warnings.append(ingress_val)
            elif "Severity: error" in ingress_val:
                errors.append(ingress_val)
            ingress_val = ""

        elif line.startswith("\n"):
            continue
    
        else:
            ingress_val += ' ' + line

    return (len(warnings) > 0 , warnings, len(errors) > 0, errors, types)

def handle_erc_result(input):
    warnings = []
    warning = False
    errors = []
    error = False
    for line in input:
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
    return warning, warnings, error, errors

def executeKicadAction(KicadPcb_path, configPath, action, temp_file_path):
    availableAction = ["drc", "drc-ignorecable", "erc", "gerberAndDrill", "panelized"]
    assert(action in availableAction)

    KicadPcb_path = os.path.abspath(KicadPcb_path)
    configPath = os.path.abspath(configPath)
    temp_file_path = os.path.abspath(temp_file_path)
    


    if(action == availableAction[0]):
        kibot_command = ['kibot', '-e', f'{KicadPcb_path}', '-c', f'{configPath}/drc.kibot.yaml']
        KibotProcess = subprocess.Popen(kibot_command)

    if(action == availableAction[1]):
        kibot_command = ['kibot', '-e', f'{KicadPcb_path}', '-c', f'{configPath}/drc-disconnectedIgnored.kibot.yaml']
        KibotProcess = subprocess.Popen(kibot_command)

    if(action == availableAction[2]):
        kibot_command = ['kibot', '-e', f'{KicadPcb_path}', '-c', f'{configPath}/erc.kibot.yaml']
        KibotProcess = subprocess.Popen(kibot_command)

    if(action == availableAction[3]):
        kibot_command = ['kibot', '-e', f'{KicadPcb_path}', '-c', f'{configPath}/gerberAndDrill.kibot.yaml']
        KibotProcess = subprocess.Popen(kibot_command)

    if(action == availableAction[4]):
        kibot_command = ['kibot', '-e', f'{KicadPcb_path}', '-c', f'{configPath}/panelized.kibot.yaml']
        KibotProcess = subprocess.Popen(kibot_command)
    
    KibotProcess.wait() 
    return

def categorize(trackWidth, clearance, viaSize, numberOfCopperLayer):
    #print(trackWidth, clearance, viaSize, numberOfCopperLayer)
    if numberOfCopperLayer > 2:
        return "Impossible, too many Copper Layer", False
    elif viaSize < 0.4 or trackWidth < 0.2 or clearance < 0.2:
        return "Class 5 or more, not doable yet", True    
    elif viaSize < 0.6 or trackWidth < 0.3 or clearance < 0.3:
        return "Class 4, Pretty tricky, but doable", True
    elif viaSize < 0.8 or trackWidth < 0.5 or clearance < 0.5:
        return "Class 3, expect good result", True
    else:
        return "Class 2, easy to do, expect perfect result", True

