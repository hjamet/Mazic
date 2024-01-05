"""Un objet représentant une pièce du labyrinthe. Gère la construction de la salle."""
import pandas as pd
from typing import List
from EntityManager import Entity
import os

class Room:
    
    def __init__(self, name : str) -> None:
        """Charge une salle à partir d'un fichier csv généré avec le logiciel [Tiled](https://doc.mapeditor.org/en/stable/manual/export-generic/)
        
        Args:
            name (str): Nom du fichier csv à charger
        """
        # Save attributes
        self.name = name
        
        # Load csv
        self.map = self.__load_csv(name)
        
    def __load_csv(self, name : str) -> List[Entity]:
        """Charge un fichier csv et le convertit en une liste d'entités.
        
        Args:
            name (str): Nom du fichier csv à charger
        
        Returns:
            list: Liste d'entités
        """
        csv_dict = {}
        for layer_name in ["Walls", "Objects", "Floors"]:
            try:
                csv_dict[layer_name] = pd.read_csv(os.path.join("assets", "room_csv", f"{name}_{layer_name}.csv"), header=None)
            except:
                csv_dict[layer_name] = []
        
        # Check if csv is valid
        if sum(len(csv_dict[layer_name]) for layer_name in csv_dict) == 0:
            raise ValueError(f"The csv file {name} does not exist or is empty.")
        
        # Find dimensions
        self.height = len(csv_dict["Walls"])
        self.width = len(csv_dict["Walls"].columns)
        
        # Find doors
        floor_matrix = csv_dict["Floors"].values
        
            
        return []
            
        

if __name__ == "__main__":
    room = Room("room_1")