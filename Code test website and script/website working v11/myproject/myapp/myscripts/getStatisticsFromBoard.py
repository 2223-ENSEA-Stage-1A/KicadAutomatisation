import pcbnew
import math 
import sys


ToUnits = pcbnew.ToMM
FromUnits = pcbnew.FromMM

def getMeasurement(filename):

    pcb = pcbnew.LoadBoard(filename)
    pcbDesign = pcb.GetDesignSettings()

    minViaSize = math.inf
    minTrackSize = math.inf
    minClearance = 	pcbDesign.GetSmallestClearanceValue()

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



    return minTrackSize, pcbnew.ToMM(minClearance), minViaSize, pcb.GetCopperLayerCount()

