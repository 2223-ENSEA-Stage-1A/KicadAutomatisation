import os, sys

def Run(path, name, configPath):
    #print(f"je suis là : {os.getcwd()}")
    #print(f"Je suis lancé avec les arguments {path}, {name} et {configPath}")

    

    _, KicadPcb_pathList = findKicadPcb(path) #find kicad_pcb
    if(len(KicadPcb_pathList) == 1): KicadPcb_path = KicadPcb_pathList[0]; print(f"I will use {KicadPcb_path}")  #Use the only one found
    if(len(KicadPcb_pathList) > 1): print(f"Only {KicadPcb_pathList[0]} will be used !"); KicadPcb_path = KicadPcb_pathList[0] #Use the first one found if multiple submitted

    doKibotStuff(KicadPcb_path, configPath) #doesKibotStuff




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

def doKibotStuff(KicadPcb_path, configPath):
    drcResult = executeKicadAction(KicadPcb_path, configPath, "drc")
    ercResult = executeKicadAction(KicadPcb_path, configPath, "erc")
    gerberAndDrillResult = executeKicadAction(KicadPcb_path, configPath, "gerberAndDrill")
    print("drc Result : \n", drcResult, "---------------")
    print("erc Result : \n", ercResult, "---------------")
    print("gerber And Drill Result : \n", gerberAndDrillResult, "---------------")


    
    
def executeKicadAction(KicadPcb_path, configPath, action):
    availableAction = ["drc", "drc-ignorecable", "erc", "gerberAndDrill"]
    assert(action in availableAction)

    if(action == availableAction[0]):
        KibotProcess = os.popen(f"kibot -e '{KicadPcb_path}' -c '{configPath}/drc.kibot.yaml'")
        KibotProcessData = KibotProcess.read()
    
    if(action == availableAction[1]):
        KibotProcess = os.popen(f"kibot -e '{KicadPcb_path}' -c '{configPath}/drc-disconnectedIgnored.kibot.yaml'")
        KibotProcessData = KibotProcess.read()

    if(action == availableAction[2]):
        KibotProcess = os.popen(f"kibot -e '{KicadPcb_path}' -c '{configPath}/erc.kibot.yaml'")
        KibotProcessData = KibotProcess.read()

    if(action == availableAction[3]):
        KibotProcess = os.popen(f"kibot -e '{KicadPcb_path}' -c '{configPath}/gerberAndDrill.kibot.yaml'")
        KibotProcessData = KibotProcess.read()
        
    return KibotProcessData

   


Run(sys.argv[1], sys.argv[2], sys.argv[3])