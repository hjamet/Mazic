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
        self.name = name
        
    def __load_csv(name : str) -> List[Entity]:
        """Charge un fichier csv et le convertit en une liste d'entités.
        
        Args:
            name (str): Nom du fichier csv à charger
        
        Returns:
            list: Liste d'entités
        """
        csv = pd.read_csv(os.path.join("assets", "room_csv", name + ".csv"))