import pcbnew

from myapp.myscripts.utilities import timeit
import myapp.myscripts.config as config



def fitPolygon(boards, boxSize, spacing):
    config.run_script_ad = 0
    config.max_run_script_run = len(boards)

    def move_line_chain(line_chain, vector):
        new_line_chain = pcbnew.SHAPE_LINE_CHAIN()

        # Iterate over each point in the line chain using list comprehension
        [new_line_chain.Append(line_chain.GetPoint(i) + vector) for i in range(line_chain.GetPointCount())]

        return new_line_chain
    
    def is_convex(shape_line: pcbnew.SHAPE_LINE_CHAIN):
        segment_count = shape_line.SegmentCount()
        sign = None



        for i in range(segment_count):
            prev_index = (i - 1) if i == 1 else (i - 1 + segment_count) % segment_count
            current_index = i

            prev_segment = shape_line.CSegment(prev_index)
            current_segment = shape_line.CSegment(current_index)
            prev_vector_x = prev_segment.A.x - prev_segment.B.x
            prev_vector_y = prev_segment.A.y - prev_segment.B.y
            current_vector_x = current_segment.A.x - current_segment.B.x
            current_vector_y = current_segment.A.y - current_segment.B.y

            # Calculate cross product
            cross_product = (prev_vector_x * current_vector_y) - (prev_vector_y * current_vector_x)


            # Checking the bend direction
            if sign == 1 and cross_product < 0: return False
            elif sign == -1 and cross_product > 0: return False 
            
            # Checking the bend, stil the same ? convexe
            sign = 1 if cross_product > 0 else -1

        return True
        
    def detect_inside_box(outline1, box):
        return box.BBox().Contains(outline1.BBox())
    
    def detect_inside_shape(outline1, outline2):
        height = max(outline1.BBox().GetHeight(), outline2.BBox().GetHeight(),outline1.BBox().GetWidth(), outline2.BBox().GetWidth())
        segment_count_1 = outline1.SegmentCount()
        segment_count_2 = outline2.SegmentCount()
        
        for i in range(segment_count_1):
            segment = pcbnew.SEG(outline1.CSegment(i).B, outline1.CSegment(i).B + pcbnew.VECTOR2I(height * 10, 0))
            intersectCount = 0
            for j in range(segment_count_2):
                segment2 = pcbnew.SEG(outline2.CSegment(j))
                if segment.Intersects(segment2):
                    intersectCount += 1

            if (intersectCount % 2) == 1:
                return True
        return False

    def center_inside_convex(outline1, outline2_list, box, clearance=0, convex=False):
        bbox1 = outline1.BBox()  # Calculate the bounding box of outline1 once
        if not is_convex(outline1): return False, None
        # Iterate over the outlines in outline2_list
        for outline2 in outline2_list:
            if outline2 and is_convex(outline2):
                bbox2 = outline2.BBox()  # Calculate the bounding box of outline2 once

                # Calculate the center point of bbox2
                center_x = (bbox1.GetX() + bbox1.GetX() + bbox1.GetWidth()) // 2
                center_y = (bbox1.GetY() + bbox1.GetY() + bbox1.GetHeight()) // 2
                center_point = pcbnew.VECTOR2I(center_x, center_y)

                # Check if the center point is inside outline1
                if bbox2.Contains(center_point):
                    return True, outline2
            
        return False, None
    
    def detect_intersection_outline(outline1, outline2_list, box, clearance=0):
        if isinstance(outline2_list, list):
            bbox1 = outline1.BBox()  # Calculate outline1's bounding box once

            convex = is_convex(outline1)

            # Iterate over outlines in outline2_list
            for outline2 in outline2_list:
                if outline2:
                    i = 0
                    bbox2 = outline2.BBox()  # Calculate outline2's bounding box once
                    full_convex = is_convex(outline2) and convex
                    
                    if bbox1.Intersects(bbox2):
                        # Iterate over segments in outline1
                        for i in range(outline1.SegmentCount()):
                            segment1 = outline1.CSegment(i)

                            # Iterate over segments in outline2
                            for j in range(outline2.SegmentCount()):
                                segment2 = outline2.CSegment(j)
                                i += 1

                                # Check if the segments intersect
                                if segment1.Intersects(segment2):
                                    return True, segment2
                                
                        if not full_convex :
                            test = detect_inside_shape(outline1, outline2)
                            test2 = detect_inside_shape(outline2, outline1)
                            if test or test2 :
                                return True, None                             
                                

                    if (bbox1.Contains(bbox2) or bbox2.Contains(bbox1)):
                        
                        if full_convex:
                            return True, None
                        
                        test = detect_inside_shape(outline1, outline2)
                        test2 = detect_inside_shape(outline2, outline1)
                        if test or test2 :
                            return True, None             

                        
            return False, None
        

    def find_intersection_outline(outline1, outline2_list, box, clearance=0, convex = False):
        if isinstance(outline2_list, list):
            bbox1 = outline1.BBox()  # Calculate outline1's bounding box once
            if is_convex(outline1):
                # Iterate over outlines in outline2_list
                for outline2 in outline2_list:
                    if outline2 and is_convex(outline2):
                        bbox2 = outline2.BBox()  # Calculate outline2's bounding box once
                        if bbox1.Intersects(bbox2):
                            return outline2
   
            return None

    
    def detect_intersection_segment(outline1, segment2, box, clearance=0):
        segment_count_1 = outline1.SegmentCount()

        for i in range(segment_count_1):
            segment1 = outline1.CSegment(i)

            if segment1.Intersects(segment2):
                return True, segment2
            
        return False, None

    def next(vector, spacing):
        if spacing < pcbnew.FromMM(1):
            spacing = pcbnew.FromMM(1)

        if(vector.x == 0):
            vector.x, vector.y = vector.y + spacing, 0
        else:
            vector.x, vector.y = vector.x - spacing, vector.y + spacing
        return vector

    def copy_outline(outline: pcbnew.SHAPE_LINE_CHAIN) -> pcbnew.SHAPE_LINE_CHAIN:
        return move_line_chain(outline, pcbnew.VECTOR2I(0,0))
    
    
    @timeit
    def arrange_outline(outline, arranged_outlines, box, spacing, current_positions):
        current_pos = pcbnew.VECTOR2I(0, 0)
        intersects = False
        max_x = box.BBox().GetWidth() - outline.BBox().GetWidth()
        max_y = box.BBox().GetHeight() - outline.BBox().GetHeight()

        while not intersects and (current_pos.x < max_x or current_pos.y < max_y):

            moved_outline = move_line_chain(outline, current_pos)

            center_inside_convex_bool, center_inside_convex_outline = center_inside_convex(moved_outline, arranged_outlines, box, spacing)

            if center_inside_convex_bool:

                outline2 = center_inside_convex_outline
                if outline2:
                    distance = min(moved_outline.BBox().GetWidth(), moved_outline.BBox().GetHeight())
                    distance = int(distance/(spacing)) if spacing != 0 else int(distance/1000000)
                    for _ in range(int(distance) if int(distance) != 0 else 1):
                        current_pos = next(current_pos,spacing)
                        if current_pos.x == 0 or current_pos.y == 0 :
                            break
                moved_outline = move_line_chain(outline, current_pos)
                               
            else:

                intersects_bool, seg = detect_intersection_outline(moved_outline, arranged_outlines, box, spacing)
                inside_bool = detect_inside_box(moved_outline, box)

                if not intersects_bool and inside_bool:
                    intersects = True
                    arranged_outlines.append(moved_outline)
                    current_positions.append(current_pos)
                    return

                elif intersects_bool and seg and inside_bool:
                    current_pos = next(current_pos,spacing)
                    moved_outline = move_line_chain(outline, current_pos)
                    intersects_bool, seg = detect_intersection_segment(moved_outline, seg, box, spacing)
                    while intersects_bool and seg:
                        current_pos = next(current_pos,spacing)
                        moved_outline = move_line_chain(outline, current_pos)
                        intersects_bool, seg = detect_intersection_segment(moved_outline, seg, box, spacing)
                
                elif not inside_bool:
                    
                    while (not inside_bool) and (current_pos.x < max_x or current_pos.y < max_y):
                        current_pos = next(current_pos,spacing)
                        moved_outline = move_line_chain(outline, current_pos)
                        inside_bool = detect_inside_box(moved_outline, box)
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
    
    def removeArcs(outline: pcbnew.SHAPE_LINE_CHAIN) -> None:
        start = None
        end = None
        started = False
        terminated = True
        for i in range(outline.GetPointCount()):
            if outline.IsArcStart(i):
                start = i
                started = True
            if started and outline.IsArcEnd(i):
                end = i
                started = False
                terminated = False
            if not terminated:
                outline.Append(pcbnew.SEG(start, end))
                terminated = True





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
