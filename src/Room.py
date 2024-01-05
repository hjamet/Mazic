"""Un objet représentant une pièce du labyrinthe. Gère la construction de la salle."""
import pandas as pd
from typing import List
from EntityManager import Entity
import os
import numpy as np


class Room:
    floor_assets = {
        485: "floor_1",
        486: "floor_2",
        487: "floor_3",
        488: "floor_4",
        489: "floor_5",
        490: "floor_6",
        491: "floor_7",
        492: "floor_8",
        493: "floor_ladder",
        494: [f"floor_spikes_anim_f{i}" for i in range(4)],
        498: "floor_stairs",
    }
    wall_assets = {
        630: "wall_banner_blue",
        631: "wall_banner_green",
        632: "wall_banner_red",
        633: "wall_banner_yellow",
        634: "wall_edge_bottom_left",
        635: "wall_edge_bottom_right",
        636: "wall_edge_left",
        637: "wall_edge_mid_left",
        638: "wall_edge_mid_right",
        639: "wall_edge_right",
        640: "wall_edge_top_left",
        641: "wall_edge_top_right",
        642: "wall_edge_tshape_bottom_left",
        643: "wall_edge_tshape_bottom_right",
        644: "wall_edge_tshape_left",
        645: "wall_edge_tshape_right",
        646: [f"wall_fountain_basin_blue_anim_f{i}" for i in range(3)],
        649: [f"wall_fountain_basin_red_anim_f{i}" for i in range(3)],
        652: [f"wall_fountain_mid_blue_anim_f{i}" for i in range(3)],
        655: [f"wall_fountain_mid_red_anim_f{i}" for i in range(3)],
        663: "wall_hole_1",
        664: "wall_hole_2",
        665: "wall_left",
        666: "wall_mid",
        667: "wall_outer_front_left",
        668: "wall_outer_front_right",
        669: "wall_outer_mid_left",
        670: "wall_outer_mid_right",
        671: "wall_outer_top_left",
        672: "wall_outer_top_right",
        673: "wall_right",
        674: "wall_top_left",
        675: "wall_top_mid",
        676: "wall_top_right",
    }

    def __init__(self, name: str) -> None:
        """Charge une salle à partir d'un fichier csv généré avec le logiciel [Tiled](https://doc.mapeditor.org/en/stable/manual/export-generic/)

        Args:
            name (str): Nom du fichier csv à charger
        """
        # Save attributes
        self.name = name

        # Load csv
        self.map = self.__load_csv(name)

    def __load_csv(self, name: str) -> List[Entity]:
        """Charge un fichier csv et le convertit en une liste d'entités.

        Args:
            name (str): Nom du fichier csv à charger

        Returns:
            list: Liste d'entités
        """
        csv_dict = {}
        for layer_name in ["Walls", "Objects", "Floors"]:
            try:
                csv_dict[layer_name] = pd.read_csv(
                    os.path.join("assets", "room_csv", f"{name}_{layer_name}.csv"),
                    header=None,
                )
            except:
                csv_dict[layer_name] = []

        # Check if csv is valid
        if sum(len(csv_dict[layer_name]) for layer_name in csv_dict) == 0:
            raise ValueError(f"The csv file {name} does not exist or is empty.")

        # Drop rows and columns with only -1 values
        for layer_name in csv_dict:
            csv_dict[layer_name].replace(-1, np.nan, inplace=True)
            csv_dict[layer_name].dropna(axis=0, how="all", inplace=True)
            csv_dict[layer_name].dropna(axis=1, how="all", inplace=True)

        # Find dimensions
        self.height = len(csv_dict["Walls"])
        self.width = len(csv_dict["Walls"].columns)

        # Find doors
        wall_and_floor = csv_dict["Walls"].copy()
        wall_and_floor.update(csv_dict["Floors"])
        wall_and_floor_matrix = wall_and_floor.to_numpy()
        first_row = wall_and_floor_matrix[0, :]
        mask = np.vectorize(lambda x: np.isnan(x) or x in self.floor_assets)(first_row)
        result = np.where(mask, True, False)

        return []


if __name__ == "__main__":
    room = Room("room_1")
