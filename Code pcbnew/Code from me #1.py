from pcbnew import *
import os

filename = "abc.kicad_pcb"
output = "tmp"
print(os.getcwd() + '/' + filename)

print(os.getcwd() + '/' + output)

Board = LoadBoard(filename)
pctl = PLOT_CONTROLLER(Board)
popt = pctl.GetPlotOptions()
popt.SetOutputDirectory(output)



plot_plan = [
    ( "CuTop", F_Cu, "Top layer" ),
    ( "CuBottom", B_Cu, "Bottom layer" ),
    ( "PasteBottom", B_Paste, "Paste Bottom" ),
    ( "PasteTop", F_Paste, "Paste top" ),
    ( "SilkTop", F_SilkS, "Silk top" ),
    ( "SilkBottom", B_SilkS, "Silk top" ),
    ( "MaskTop", F_Mask, "Mask top" ),
    ( "MaskBottom", B_Mask, "Mask bottom" ),
    ( "EdgeCuts", Edge_Cuts, "Edges" ),
]

for layer_info in plot_plan:
    pctl.SetLayer(layer_info[1])
    pctl.OpenPlotfile(layer_info[0], PLOT_FORMAT_GERBER, layer_info[2])
    pctl.PlotLayer()

pctl.ClosePlot()