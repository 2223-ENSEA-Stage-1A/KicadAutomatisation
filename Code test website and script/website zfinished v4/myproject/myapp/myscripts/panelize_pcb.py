from django.utils import timezone
import shutil
import pcbnew
from celery import shared_task

from myapp.models import ResultFile
from myapp.myscripts.checkThisProject import findKicadPcb
from myapp.myscripts.fitPolygon import fitPolygon
from myapp.myscripts.fit_easyCut import fit_EasyCut
from myapp.myscripts.fit_rectangles import fit_rectangles
from myapp.myscripts.merge_boards import merge_boards
from myapp.myscripts.movePCB import movePCB
from myapp.myscripts.utilities import unzip_file


def panelize_pcb(result_files: ResultFile, spacing, fit_mode, output_file, boxSize):
    # Create a new board for the panelized version
    panel_board = pcbnew.BOARD()

    # Set the title of the board
    panel_board.board_title = "Panelized PCB"

    boards = []

    # Initialize variables for calculating panel dimensions
    max_width = 0
    total_height = 0
    link = []

    # Panelize all the PCBs from the uploaded files
    for result_file in result_files:

        # Unzip the path
        result_file_path_unzipped = f"tmp/{timezone.now()}"

        unzip_file(result_file.uploaded_file.file.path, result_file_path_unzipped)


        # Get the uploaded file's path
        _, input_file_path_list = findKicadPcb(result_file_path_unzipped)
        input_file_path = input_file_path_list[0]


        # Load the input PCB file
        board = pcbnew.LoadBoard(input_file_path)
        link.append((result_file, board))

        # Get the board dimensions
        board_width = board.GetBoardEdgesBoundingBox().GetWidth()
        board_height = board.GetBoardEdgesBoundingBox().GetHeight()

        # Update the maximum width and total height
        if board_width > max_width:
            max_width = board_width
        total_height += board_height

        # Add the board to the panelized board
        boards.append(board)

        # Remove all files in the output directory
        shutil.rmtree(result_file_path_unzipped)

    if fit_mode == 'Polygons':
        result = fitPolygon(boards, boxSize, spacing)
        sortedboards, displacement = zip(*result)
    elif fit_mode == 'Rectangles':
        result = fit_rectangles(boards, boxSize, spacing)
        sortedboards, displacement = zip(*result)
    elif fit_mode == 'EasyCut':
        result = fit_EasyCut(boards, boxSize, spacing)
        sortedboards, displacement = zip(*result)
    else:
        return
    
    ShovedIn = []

    def result_file_from_board(board_target):
        for result_file, board in link:
            if board == board_target:
                return result_file

    absolute_displacement = pcbnew.VECTOR2I(0,0)
    for i in range(len(sortedboards)):
        
        #j = order[i]
        phaseDisplacement = displacement[i] #j
        if not phaseDisplacement: continue

        

        board = sortedboards[i] #j

        ShovedIn.append(result_file_from_board(board))

        phaseDisplacement -= absolute_displacement
        absolute_displacement += phaseDisplacement
 
        panel_board = merge_boards(panel_board, board, phaseDisplacement, f"-v{i}-") #j

    movePCB(panel_board, absolute_displacement)

    # Save the panelized board to the specified output file
    pcbnew.SaveBoard(output_file, panel_board)

    return ShovedIn #, Failed



