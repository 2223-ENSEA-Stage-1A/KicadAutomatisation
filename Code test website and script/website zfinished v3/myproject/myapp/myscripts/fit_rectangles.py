import pcbnew

from myapp.myscripts.utilities import timeit
import myapp.myscripts.config as config



def fit_rectangles(boards, boxSize, spacing):
    config.run_script_ad = 0
    config.max_run_script_run = len(boards)

    def move_line_chain(line_chain, vector):
        new_line_chain = pcbnew.SHAPE_LINE_CHAIN()

        # Iterate over each point in the line chain using list comprehension
        [new_line_chain.Append(line_chain.GetPoint(i) + vector) for i in range(line_chain.GetPointCount())]

        return new_line_chain
        
    def detect_inside_box(outline1, box):
        return box.BBox().Contains(outline1.BBox())
    
    
    def detect_intersection_outline(outline1, outline2_list):
        if isinstance(outline2_list, list):
            bbox1 = outline1.BBox()  # Calculate outline1's bounding box once

            # Iterate over outlines in outline2_list
            for outline2 in outline2_list:
                if outline2:
                    bbox2 = outline2.BBox()  # Calculate outline2's bounding box once
                    
                    if bbox1.Intersects(bbox2):
                        return True
                                                            
                    if (bbox1.Contains(bbox2) or bbox2.Contains(bbox1)):
                        return True
                                 
            return False
        
    def find_intersection_outline(outline1, outline2_list):
        bbox1 = outline1.BBox()
        for outline2 in outline2_list:
                if outline2:
                    bbox2 = outline2.BBox()  # Calculate outline2's bounding box once
                    
                    if bbox1.Intersects(bbox2):
                        return bbox2
                                                            
                    if (bbox1.Contains(bbox2) or bbox2.Contains(bbox1)):
                        return bbox2

    def next(vector, spacing):
        if spacing < pcbnew.FromMM(1):
            spacing = pcbnew.FromMM(1)

        if(vector.x == 0):
            vector.x, vector.y = vector.y + spacing, 0
        else:
            vector.x, vector.y = vector.x - spacing, vector.y + spacing
        return vector

    @timeit
    def arrange_outline(outline, arranged_outlines, box, spacing, current_positions):
        current_pos = pcbnew.VECTOR2I(0, 0)
        intersects = False
        max_x = box.BBox().GetWidth() - outline.BBox().GetWidth()
        max_y = box.BBox().GetHeight() - outline.BBox().GetHeight()

        bbox = outline.BBox()

        while not intersects and (current_pos.x < max_x or current_pos.y < max_y):

            moved_outline = move_line_chain(outline, current_pos)

            intersects_bool = detect_intersection_outline(moved_outline, arranged_outlines)
            inside_bool = detect_inside_box(moved_outline, box)

            if not intersects_bool and inside_bool:
                intersects = True
                arranged_outlines.append(moved_outline)
                current_positions.append(current_pos)
                return

            if intersects_bool:
                bbox2 = find_intersection_outline(moved_outline, arranged_outlines)
                bbox1 = moved_outline.BBox()
                bbox = bbox1.Intersect(bbox2)
                distance = int(min(bbox.GetHeight(), bbox.GetWidth()))
                step = int(distance / spacing if spacing != 0 else pcbnew.ToMM(distance))
                for _ in range(step if step > 0 else 1):
                    current_pos = next(current_pos, spacing)
                    if current_pos.x == 0 or current_pos.y == 0:
                        break

            else:
                current_pos = next(current_pos, spacing)

        arranged_outlines.append(None)
        current_positions.append(None)
        return
    
    def arrange_outlines(outlines, box, spacing):
        arranged_outlines = []
        current_positions = []
        for outline in outlines:
            arrange_outline(outline, arranged_outlines, box, spacing, current_positions)

            config.run_script_ad += 1


        return arranged_outlines, current_positions 
    

    Stuff = {
        'box': None, # Unique
        'boards': boards, # OneToOne
        'polygons': [pcbnew.SHAPE_POLY_SET() for _ in boards], # OneToOne
        'outlines': [], # OneToOne
        'zeroedOutlines': [], # OneToOne
        'displacement': [], # OneToOne
        'Area': [], # OneToOne
        'ArangedOutline': [], #OneToOne
        'zeroingDisplacement': [], #OneToOne
        'fullDisplacement': [], #OneToOne
    }

    spacing = spacing if spacing != 0 else pcbnew.FromMM(1)

    [board.GetBoardPolygonOutlines(polygon) for board, polygon in zip(boards, Stuff['polygons'])]

    x,y = boxSize
    Stuff['box'] = pcbnew.SHAPE_RECT(pcbnew.BOX2I(pcbnew.VECTOR2I(0,0), pcbnew.VECTOR2I(x,y))).Outline()

    [polygon.Inflate(spacing//2, 0) for polygon in Stuff['polygons']] #spacing ?

    Stuff['outlines'] = [polygon.Outline(0) for polygon in Stuff['polygons']] 
    
    

    for outline in Stuff['outlines']:
        outline.ClearArcs()
        outline.SetClosed(True)
        outline.Simplify(True)
        zeroedOutline = move_line_chain(outline, -pcbnew.VECTOR2I(outline.BBox().GetX(), outline.BBox().GetY()))
        Stuff['zeroedOutlines'].append(zeroedOutline)
        Stuff['zeroingDisplacement'].append(pcbnew.VECTOR2I(outline.BBox().GetX(), outline.BBox().GetY()))
        Stuff['Area'].append(zeroedOutline.BBox().GetArea())

    # Sort the 'Area' list in ascending order and move other lists accordingly
    sorted_data = zip(Stuff['Area'], Stuff['boards'], Stuff['polygons'], Stuff['outlines'], Stuff['zeroedOutlines'], Stuff['zeroingDisplacement'])
    sorted_data = sorted(sorted_data, key=lambda x: x[0], reverse=True)

    # Unpack the sorted data into separate lists
    Stuff['Area'], Stuff['boards'], Stuff['polygons'], Stuff['outlines'], Stuff['zeroedOutlines'], Stuff['zeroingDisplacement'] = zip(*sorted_data)

    Stuff['ArangedOutline'], Stuff['displacement'] = arrange_outlines(Stuff['zeroedOutlines'], Stuff['box'], spacing)

    for displacement, zeroingDisplacement in zip(Stuff['displacement'], Stuff['zeroingDisplacement']):
        if not displacement:
            Stuff['fullDisplacement'].append(None)
        else: Stuff['fullDisplacement'].append(zeroingDisplacement - displacement) 

        

    return list(zip(Stuff['boards'], Stuff['fullDisplacement']))
