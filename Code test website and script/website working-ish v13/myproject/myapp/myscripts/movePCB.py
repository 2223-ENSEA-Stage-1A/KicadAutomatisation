def movePCB(pcb, displacement):
    # Remember existing elements in base
    tracks = pcb.GetTracks()
    footprints = pcb.GetFootprints()
    drawings = pcb.GetDrawings()
    zonescount = pcb.GetAreaCount()

    # Move
    for track in tracks:
        track.Move(-displacement)

    for footprint in footprints:
        footprint.Move(-displacement)

    for drawing in drawings:
        drawing.Move(-displacement)

    for i in range(0, zonescount):
        pcb.GetArea(i).Move(-displacement)