import numpy as np
import os
import pandas as pd
from PIL import Image
import cv2
import random
from src.xml_tools import create_base_xml, create_object_xml


class PatchGenerator():
    def __init__(self, frame, tile_size, num_tiles):
        self.tile_size = tile_size
        self.num_tiles = num_tiles
        self.frame = frame
        self.image = np.array(frame.frame)
        self.mitotic_coordinates = frame.records
    

    def generate_negative_patches(self,coordinates):
        """Generates random tiles that do NOT contain the mitotic coordinates. We pick x1 and y1
        randomly within the range of the whole image.
        We then randomly choose x2 and y2 if the patch does not contain the mitotic coordinates,
        we discard it otherwise"""
        x_image, y_image, _ = self.image.shape
        x_mitotic, y_mitotic = coordinates

        coord_x1 = []
        coord_y1 = []
        coord_x2 = []
        coord_y2 = []

        choice = [self.tile_size, -self.tile_size]

        i = 0
        while i < self.num_tiles:
            #choose x1 and y1 within the whole image
            x_choice = np.random.randint(0, x_image, 1)
            y_choice = np.random.randint(0, y_image, 1)
            #generate random x2 and y2 candidates, we then choose the ones that do
            # not contain the mitotic coordinates
            x2_candidate = x_choice + (random.choice(choice))
            y2_candidate = y_choice + (random.choice(choice))                  
            # search if choice of coordinates inside boundaries and if valid centre of \
            # coordinates. This is achieved when the value of frame.frame_mask == 0. 
            if (0 < x2_candidate[0] < x_image) \
                and (0 < x_choice[0] +int(self.frame.tile_size) < x_image)\
                and (0 < y2_candidate[0] < y_image) and (0 < y_choice[0] +int(self.frame.tile_size) < y_image)\
                and (self.frame.frame_mask[y_choice[0]+int(self.frame.tile_size/2),x_choice[0]+int(self.frame.tile_size/2)] == 0):

                coord_x1.append(x_choice)
                coord_y1.append(y_choice)

                coord_x2.append(x2_candidate)
                coord_y2.append(y2_candidate)
                i += 1
        return (coord_x1, coord_x2, coord_y1, coord_y2)

    def generate_positive_patches(self, coordinates):
        """Generates random tiles that contain the mitotic coordinates. We pick x1 and y1
        randomly within the range of the mitotic coordinates, given a tile size. We then randomly choose
        x2 and y2 if the patch contains the mitotic coordinates, we discard it otherwise"""
        x_image, y_image, _ = self.image.shape
        x_mitotic, y_mitotic = coordinates
        x_mitotic = int(x_mitotic)
        y_mitotic = int(y_mitotic)

        coord_x1 = []
        coord_y1 = []
        coord_x2 = []
        coord_y2 = []

        choice = [self.tile_size, -self.tile_size]

        i = 0

        while i < self.num_tiles:
            #we get x1,y1 randomly within the range of the tile size, centered on the mitotic coordinates
            x_choice = np.random.randint(max((x_mitotic - self.tile_size),0), min((x_mitotic + self.tile_size),x_image), 1)
            y_choice = np.random.randint(max((y_mitotic - self.tile_size),0), min((y_mitotic + self.tile_size),y_image), 1)

            #We generate x2 and y2 candidates, and we check if the mitotic coordinates are contained in the patch
            x2_candidate = x_choice + (random.choice(choice))
            y2_candidate = y_choice + (random.choice(choice))

            if (x2_candidate in range(0, x_image)) and (y2_candidate[0] in range(0, y_image)) \
            and (x2_candidate in range((x_mitotic - self.tile_size), (x_mitotic + self.tile_size))) \
            and (y2_candidate in range((y_mitotic - self.tile_size), (y_mitotic + self.tile_size))):

                coord_x1.append(x_choice)
                coord_y1.append(y_choice)

                coord_x2.append(x2_candidate)
                coord_y2.append(y2_candidate)
                i += 1
            else:
                continue

        return (coord_x1, coord_x2, coord_y1, coord_y2)
    
    

    def create_patches(self,frame):
        """calls both functions for generating positive and negative patches and stores the images in
        two separate lists (lists of numpy arrays)"""
        
        for m_coordinates in self.mitotic_coordinates:
            coordinates = (m_coordinates.x, m_coordinates.y)
            confidence = m_coordinates.confidence

            pos_x1_coord, pos_x2_coord, pos_y1_coord, pos_y2_coord = \
                self.generate_positive_patches(coordinates)
    
            
            neg_x1_coord, neg_x2_coord, neg_y1_coord, neg_y2_coord = \
                self.generate_negative_patches(coordinates)
    
    
            for i in range(self.num_tiles):
                x1_mitotic = int(min(pos_x1_coord[i], pos_x2_coord[i]))
                x2_mitotic = int(max(pos_x1_coord[i], pos_x2_coord[i]))
                y1_mitotic = int(min(pos_y1_coord[i], pos_y2_coord[i]))
                y2_mitotic = int(max(pos_y1_coord[i], pos_y2_coord[i]))
                
                individual_mitotic_patch = self.image[x1_mitotic:x2_mitotic, y1_mitotic:y2_mitotic, :]

                tile_mitosis = Tile(individual_mitotic_patch)

                record_tile = get_cell_coordinates_in_tile(x1_mitotic,y1_mitotic,\
                              coordinates[0],coordinates[1],confidence)

                tile_mitosis.update_records(record_tile)

                # Checkear si que el tile creado contiene mas de una céluala mitótica.
                for record in self.frame.records:
                    if (x1_mitotic < record.x <x2_mitotic) \
                    and (y1_mitotic < record.y <y2_mitotic) \
                    and (m_coordinates.x != record.x) \
                    and (m_coordinates.y != record.y):
                        record_tile_plus = get_cell_coordinates_in_tile(x1_mitotic,y1_mitotic,\
                              record.x,record.y,record.confidence)
                        tile_mitosis.update_records(record_tile_plus)
                
                
                self.frame.update_tiles_mitosis(tile_mitosis)
                

                x1_not_mitotic = int(min(neg_x1_coord[i], neg_x2_coord[i]))
                x2_not_mitotic = int(max(neg_x1_coord[i], neg_x2_coord[i]))
                y1_not_mitotic = int(min(neg_y1_coord[i], neg_y2_coord[i]))
                y2_not_mitotic = int(max(neg_y1_coord[i], neg_y2_coord[i]))
    
                individual_not_mitotic_patch = self.image[x1_not_mitotic:x2_not_mitotic, y1_not_mitotic:y2_not_mitotic, :]
                tile_not_mitosis = Tile(individual_not_mitotic_patch)
                self.frame.update_tiles_not_mitosis(tile_not_mitosis)
    
      
class Tile:
    """Class of all sub-frames and the specific position of mitotic cells in them."""
    def __init__(self,image):
        self.tile = image
        self.records = []
    
    def update_records(self,record):
        self.records += [record]
           

class Record:
    """Class which gathers information of the position and confidence of a cell."""
    def __init__(self, x: int, y: int, confidence: float):
        self.x = y
        self.y = x
        self.confidence = confidence


class Frame:
    """Class containg all the information gathered of an specific frame and its
    mitotic and not mitotic tiles."""
    def __init__(self,path,cells,tile_size,num_tiles=10,path_annotations=None):
        self.path = path
        self.filename = os.path.basename(path)
        self.frame = cv2.imread(path)
        self.width = self.frame.shape[0]
        self.height = self.frame.shape[1]
        self.tile_size = tile_size
        self.num_tiles = num_tiles
        self.cells = cells
        self.tiles_mitosis = []
        self.tiles_not_mitosis = []
        self.records = []
        self.path_annotations = path_annotations
        self.frame_mask = []
        
    def get_records(self):
        self.records = [Record(*cell) for cell in self.cells]
        print(f'Got records for {self.filename}')

        
    def create_mask(self):
        mask = np.zeros((self.height,self.width))
        for record in self.records:
            mask[int(record.x-(self.tile_size/2)):int(record.x+(self.tile_size/2)),
                 int(record.y-(self.tile_size/2)):int(record.y+(self.tile_size/2))] = 1
        self.frame_mask = mask

    def get_all_tiles(self):
        patchgenerator = PatchGenerator(self, self.tile_size,self.num_tiles)
        patchgenerator.create_patches(self)

    def update_tiles_mitosis(self,tile):
        self.tiles_mitosis += [tile]
    
    def update_tiles_not_mitosis(self,tile):
        self.tiles_not_mitosis += [tile]
        
    def create_annotations(self):
        delta = 15
        count = 0
        for tile_mitosis in self.tiles_mitosis:
            image = tile_mitosis.tile
            tree = create_base_xml(self,image,f"{self.filename.replace('.tiff','')}_mitosis_{count}.jpg")
            for record in tile_mitosis.records:
                coordinates = (record.x - delta, record.x  + delta, record.y - delta, record.y + delta)
                tree = create_object_xml(tree,coordinates)
            tree.write(os.path.join(self.path_annotations,'annotations',f"{self.filename.replace('.tiff','')}_mitosis_{count}.xml"))
            cv2.imwrite(os.path.join(self.path_annotations,'images',f"{self.filename.replace('.tiff','')}_mitosis_{count}.jpg"),image) 
            count += 1
        count = 0
        for tile_not_mitosis in self.tiles_not_mitosis:
            image_not = tile_not_mitosis.tile
            tree = create_base_xml(self,image,f"{self.filename.replace('.tiff','')}_notmitosis_{count}.jpg")
            tree.write(os.path.join(self.path_annotations,'annotations',f"{self.filename.replace('.tiff','')}_notmitosis_{count}.xml"))
            cv2.imwrite(os.path.join(self.path_annotations,'images',f"{self.filename.replace('.tiff','')}_notmitosis_{count}.jpg"),image_not) 
            count += 1

    def csv_annotations(self):
        delta = 15
        count = 0
        df = pd.DataFrame(columns = ["filename", "x1_left_bottom", "x2_right_bottom","y1_left_up", "y2_right_up", "classification"])
        for tile_mitosis in self.tiles_mitosis:
            for record in tile_mitosis.records:
                coord_x1, coord_x2, coord_y1, coord_y2 = (record.x - delta, record.x + delta,\
                                                          record.y - delta, record.y + delta)
                coord_x1 = max(coord_x1, 0)
                coord_x2 = min(coord_x2, self.tile_size)
                coord_y1 = max(coord_y1, 0)
                coord_y2 = min(coord_y2, self.tile_size)
                filename = str(f"{self.filename.replace('.tiff', '')}_mitosis_{count}.jpg")

                df = df.append({"filename":filename,
                            "x1_left_bottom": coord_x1,\
                            "x2_right_bottom": coord_x2,
                            "y1_left_up": coord_y1,
                            "y2_right_up": coord_y2,
                            "classification": 1 }, ignore_index=True)
                count += 1
            count = 0
            for record in self.tiles_not_mitosis:
                filename = str(f"{self.filename.replace('.tiff', '')}_notmitosis_{count}.jpg")

                df = df.append({"filename":filename,
                                "x1_left_bottom": 0, \
                                "x2_right_bottom": 0,
                                "y1_left_up": 0,
                                "y2_right_up": 0,
                                "classification": 0}, ignore_index=True)
                count +=1

        return df


## Funciones a parte ##
def get_cell_coordinates_in_tile(x1_tile : int, y1_tile : int,x_record: int, y_record: int, confidence) -> Record:
        x_tile = x_record - x1_tile
        y_tile = y_record - y1_tile    
        return Record(x_tile, y_tile, confidence)

