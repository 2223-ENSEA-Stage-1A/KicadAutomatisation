import pcbnew

from myapp.myscripts.utilities import timeit
import myapp.myscripts.config as config



def fit_EasyCut(boards, boxSize, spacing):
    config.run_script_ad = 0
    config.max_run_script_run = len(boards)

    def move_line_chain(line_chain, vector):
        new_line_chain = pcbnew.SHAPE_LINE_CHAIN()

        # Iterate over each point in the line chain using list comprehension
        [new_line_chain.Append(line_chain.GetPoint(i) + vector) for i in range(line_chain.GetPointCount())]

        return new_line_chain
        
    def detect_inside_box(outline1, box):
        bbox = box.BBox()
        bbox1 = outline1.BBox()
        return bbox.Contains(bbox1)

    def arrange_outline(outline, arranged_outlines, box, spacing):
        
        box_bbox = box.BBox()

        xa, ya = box_bbox.GetX(), box_bbox.GetY()
        xb, yb = box_bbox.GetX() + box_bbox.GetWidth(), box_bbox.GetY() + box_bbox.GetHeight()

        current_pos = pcbnew.VECTOR2I(xa, ya)
        moved_outline = move_line_chain(outline, current_pos)

        moved_bbox = moved_outline.BBox()
        x1, y1 = moved_bbox.GetX(), moved_bbox.GetY()
        x2, y2 = moved_bbox.GetX() + moved_bbox.GetWidth(), moved_bbox.GetY() + moved_bbox.GetHeight()

        inside_bool = detect_inside_box(moved_outline, box)

        if not inside_bool:
            return False
        
        
        box_below = pcbnew.SHAPE_RECT(x1, y2, x2 - x1, yb - y2).Outline()
        box_diag = pcbnew.SHAPE_RECT(x2, y2, xb - x2, yb - y2).Outline()
        box_right = pcbnew.SHAPE_RECT(x2, y1, xb - x2, y2 - y1).Outline()

        return box_below, box_diag, box_right, current_pos, moved_outline
    
    @timeit
    def arrange_outlines(outlines_index, outlines, box, spacing):
        arranged_outlines = [None] * len(outlines)
        current_positions = [None] * len(outlines)

        
        
        def recursive(outlines_index: list, outlines, spacing, box, current_pos, moved_outline, arranged_outlines, current_positions):
            if len(outlines_index) <= 0:
                return outlines_index, outlines, spacing, box, arranged_outlines, current_positions
            
            for outline_index in range(len(outlines_index)):
                while not outline_index in outlines_index and len(outlines_index) > 0:
                    outline_index += 1
                result = arrange_outline(outlines[outline_index], arranged_outlines, box, spacing)
                if result:
                    outlines_index.remove(outline_index)
                    index = outline_index
                    break

            if not result:
                return False
            
            box_below, box_diag, box_right, current_pos_result, moved_outline_result = result

            arranged_outlines[index] = moved_outline_result
            current_positions[index] = current_pos_result

            boxs = [box_below, box_right, box_diag]

            for box_prime in boxs:
                result = recursive(outlines_index, outlines, spacing, box_prime, current_pos, moved_outline, arranged_outlines, current_positions)
                if result:
                    outlines_index, outlines, spacing, box, arranged_outlines, current_positions = result
                    
            config.run_script_ad += 1

            return outlines_index, outlines, spacing, box, arranged_outlines, current_positions
            



        result = recursive(outlines_index, outlines, spacing, box, pcbnew.VECTOR2I(0,0), None, arranged_outlines, current_positions)

        if not result:
            return False
        
        outlines_index, outlines, spacing, box, arranged_outlines, current_positions = result

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
    Stuff['order_index'] = range(len(Stuff['outlines']))
    
    
    

    for outline in Stuff['outlines']:
        outline.ClearArcs()
        outline.SetClosed(True)
        outline.Simplify(True)
        zeroedOutline = move_line_chain(outline, -pcbnew.VECTOR2I(outline.BBox().GetX(), outline.BBox().GetY()))
        Stuff['zeroedOutlines'].append(zeroedOutline)
        Stuff['zeroingDisplacement'].append(pcbnew.VECTOR2I(outline.BBox().GetX(), outline.BBox().GetY()))
        Stuff['Area'].append(zeroedOutline.BBox().GetArea())

    # Sort the 'Area' list in ascending order and move other lists accordingly
    sorted_data = zip(Stuff['Area'], Stuff['boards'], Stuff['polygons'], Stuff['outlines'], Stuff['zeroedOutlines'], Stuff['zeroingDisplacement'], Stuff['order_index'])
    sorted_data = sorted(sorted_data, key=lambda x: x[0], reverse=True)

    

    # Unpack the sorted data into separate lists
    Stuff['Area'], Stuff['boards'], Stuff['polygons'], Stuff['outlines'], Stuff['zeroedOutlines'], Stuff['zeroingDisplacement'], Stuff['order_index'] = map(list, zip(*sorted_data))
    print(Stuff['order_index'])
    Stuff['ArangedOutline'], Stuff['displacement'] = arrange_outlines(Stuff['order_index'], Stuff['zeroedOutlines'], Stuff['box'], spacing)
    
    #Stuff['order_index'].reverse()
    #sorted_data = zip(Stuff['order_index'], Stuff['ArangedOutline'], Stuff['displacement'])
    #sorted_data = sorted(sorted_data, key=lambda x: x[0], reverse=True)
    #Stuff['order_index'], Stuff['ArangedOutline'], Stuff['displacement'] = map(list, zip(*sorted_data))


    for displacement, zeroingDisplacement in zip(Stuff['displacement'], Stuff['zeroingDisplacement']):
        if not displacement:
            Stuff['fullDisplacement'].append(None)
        else: Stuff['fullDisplacement'].append(zeroingDisplacement - displacement) 

        

    return list(zip(Stuff['boards'], Stuff['fullDisplacement']))
