import pcbnew
import math 


ToUnits = pcbnew.ToMM
FromUnits = pcbnew.FromMM

def getMeasurement(filename):

    pcb = pcbnew.LoadBoard(filename)

    minViaSize = math.inf
    minTrackSize = math.inf

    for item in pcb.GetTracks():
        if type(item) is pcbnew.PCB_VIA:
            pos = item.GetPosition()
            drill = item.GetDrillValue()
            width = ToUnits(item.GetWidth())
            if width < minViaSize: minViaSize = width

        elif type(item) is pcbnew.PCB_TRACK:
            start = item.GetStart()
            end = item.GetEnd()
            width = ToUnits(item.GetWidth())
            if width < minTrackSize: minTrackSize = width

    return minViaSize, minTrackSize, pcb.GetCopperLayerCount()


