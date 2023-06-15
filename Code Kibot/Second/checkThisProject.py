import os, sys

whereAmI = os.getcwd()

def Run(name):
    print("Starting Kibot")

    os.mkdir(f"{whereAmI}/{name}-analyze")
    os.chdir(f"{whereAmI}/{name}-analyze")

    DRCstatus, ERCstatus, gerberStatus = True, True, True

    KibotProcess = os.popen(f"kibot -e ../{name}/{name}.kicad_pcb -c ../configs/drc.kibot.yaml > output_file.txt")
    KibotProcessData = KibotProcess.read()

    if(not fileExist(f"{name}-drc.txt")):
        print("Failed at DRC")
        DRCstatus = False
        print("Trying DRC Ignoring Unconnected Cable")

        KibotProcess = os.popen(f"kibot -e ../{name}/{name}.kicad_pcb -c ../configs/drc-disconnectedIgnored.kibot.yaml > output_file.txt")
        KibotProcessData = KibotProcess.read()

        if(not fileExist(f"{name}-drc.txt")):
            print("Failed at DRC while ignoring disconnected cable")
            return False
    
        DRCstatus = True
    

    KibotProcess = os.popen(f"kibot -e ../{name}/{name}.kicad_pcb -c ../configs/erc.kibot.yaml > output_file.txt")
    KibotProcessData = KibotProcess.read()

    if(not fileExist(f"{name}-erc.txt")):
        print("Failed at ERC")
        ERCstatus = False

        f = open("output_file.txt", 'r')
        data = f.readlines()
        if(len(data) != 0):
            return False

        print("Continuing nonetheless")

    
    KibotProcess = os.popen(f"kibot -e ../{name}/{name}.kicad_pcb -c ../configs/gerberAndDrill.kibot.yaml > output_file.txt")
    KibotProcessData = KibotProcess.read() 

    if(not fileExist("gerberAndDrill")):#ljfdklghdfklhkldshjgskkjhfjkl caca ici
        print("Failed at creating the Gerber and Drill files")
        gerberStatus = False
        return False

    
    print("Starting Analyzing Kibot results")

    AnalyzeSuccessfulGerberCreation(name, DRCstatus, ERCstatus, gerberStatus)

    print("done !")

    os.chdir(f"{whereAmI}")

    return True



def fileExist(path):
    return os.path.isfile(path) or os.path.isdir(path)

def contains(string, substring):
    return substring in string

def drcParser(file):
    data = file.readlines()
    returnData = []
    # Add parsing of the errors and warnings
    for line in data:
        if('@' in line):
            returnData.append(line)
    return returnData

def ercParser(file):
    data = file.readlines()
    returnData = []
    # Add parsing of the errors and warnings
    for line in data:
        if('@' in line):
            returnData.append(line)
    return returnData


def AnalyzeSuccessfulGerberCreation(name, DRCstatus, ERCstatus, gerberStatus):

    if(DRCstatus): DRCdata = open(f"{name}-drc.txt",'r')
    else: print("DRC Failed, unable to analyze this part of result")

    print(ERCstatus)

    if(ERCstatus): ERCdata = open(f"{name}-erc.txt","r") 
    else: print("ERC Failed, unable to analyze this part of result")

    if(gerberStatus): GerberData = len(os.listdir('gerberAndDrill'))
    else: print("Gerber and Drill Failed, unable to analyze this part of result")

    drcErrors = drcParser(DRCdata)
    ercErrors = ercParser(DRCdata)
    gerberFiles = os.listdir("gerberAndDrill/gerberdir")
    drillFiles = os.listdir("gerberAndDrill/drilldir")

    print(drcErrors)
    print(ercErrors)
    print(gerberFiles)
    print(drillFiles)

    print("analyzing successful attempt")


if __name__ == '__main__':
    Run(sys.argv[1])