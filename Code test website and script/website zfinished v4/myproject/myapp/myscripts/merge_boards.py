from contextlib import contextmanager
import os
import tempfile
import pcbnew

def merge_boards(board1, board2, displacement, postfix):
    # Clone board2 to avoid modifying the original object
    pcb = board1
    pcb_tmp = board2

    # Remember existing elements in base
    tracks = pcb.GetTracks()
    footprints = pcb.GetFootprints()
    drawings = pcb.GetDrawings()
    zonescount = pcb.GetAreaCount()


    # Determine new net names
    new_netnames = {}
    for i in range(1, pcb_tmp.GetNetCount()): # 0 is unconnected net
        name = pcb_tmp.FindNet(i).GetNetname()
        new_netnames[name] = name+postfix

    with tempfilename() as fname:
        # Write addon to temporary file
        pcbnew.SaveBoard(fname, pcb_tmp)

        # Replace net names in file
        pcbtext = None
        with open(fname) as fp:
            pcbtext = fp.read()

        for (old,new) in new_netnames.items():
            pcbtext = pcbtext.replace(old,new)

        with open(fname,'w') as fp:
            fp.write(pcbtext)

        # Append new board file with modified net names
        plugin = pcbnew.IO_MGR.PluginFind(pcbnew.IO_MGR.KICAD_SEXP)
        plugin.Load(fname, pcb)


        # Move
        for track in tracks:
            track.Move(displacement)

        for footprint in footprints:
            footprint.Move(displacement)

        for drawing in drawings:
            drawing.Move(displacement)

        for i in range(0, zonescount):
            pcb.GetArea(i).Move(displacement)


    return pcb

@contextmanager
def tempfilename():
    f = tempfile.NamedTemporaryFile(delete=False)
    try:
        f.close()
        yield f.name
    finally:
        try:
            os.unlink(f.name)
        except OSError:
            pass
