import os
import sys
from pcb_tools import gerber, panelize

# Define the input Gerber file paths for each PCB
pcb_files = [
    {
        'folder': 'path/to/pcb1/files',
        'gerbers': ['F.Cu','B.Cu','F.Paste','B.Paste','F.Silkscreen','B.Silkscreen','F.Mask','B.Mask','Edge.Cuts']
    },
    {
        'folder': 'path/to/pcb2/files',
        'gerbers': ['F.Cu','B.Cu','F.Paste','B.Paste','F.Silkscreen','B.Silkscreen','F.Mask','B.Mask','Edge.Cuts']
    },
    # Add more PCB sets as needed
    ]

def panelize(pcb_files):
    # Panelize each PCB
    for pcb_set in pcb_files:
        gerber_folder = pcb_set['folder']
        gerber_files = pcb_set['gerbers']
        
        # Load the Gerber files
        layers = []
        for gerber_file in gerber_files:
            gerber_path = os.path.join(gerber_folder, gerber_file)
            try:
                layer = gerber.read(gerber_path)
                layers.append(layer)
            except Exception as e:
                print(f'Error loading Gerber file {gerber_file}: {str(e)}')
                sys.exit(1)
        
        # Create a panel with a single copy of the PCB
        try:
            panel = panelize.single_panel(layers)
        except Exception as e:
            print(f'Error creating panel layout: {str(e)}')
            sys.exit(1)
        
        # Output the panelized Gerber files
        output_folder = os.path.join(gerber_folder, 'panelized')
        try:
            panel.write(output_folder)
        except Exception as e:
            print(f'Error writing panelized Gerber files: {str(e)}')
            sys.exit(1)
        
        print(f'Panelization complete for PCB set in folder: {gerber_folder}')
