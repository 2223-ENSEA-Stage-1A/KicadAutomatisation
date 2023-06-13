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


# Drill
METRIC = True
ZERO_FORMAT = GENDRILL_WRITER_BASE.DECIMAL_FORMAT
INTEGER_DIGITS = 3
MANTISSA_DIGITS = 3
MIRROR_Y_AXIS = False
HEADER = True
OFFSET = wxPoint(0,0)
MERGE_PTH_NPTH = True
DRILL_FILE = True
MAP_FILE = False
REPORTER = None


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

drill_writer = EXCELLON_WRITER(Board)
drill_writer.SetFormat(METRIC, ZERO_FORMAT, INTEGER_DIGITS, MANTISSA_DIGITS)

drill_writer.CreateDrillandMapFilesSet(output, DRILL_FILE, MAP_FILE, REPORTER)