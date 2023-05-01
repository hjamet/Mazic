from Logger import Logger
import numpy as np
from EntityManager import AnimatedEntity, Entity, Event
from typing import List


class Maze:
    def __init__(
        self,
        length: int = 40,
        width: int = 40,
        nbr_player: int = 1,
        min_room_size: int = 1,
        max_room_size: int = 40,
    ) -> None:
        """A class to generate a maze procedurally.

        Args:
            length (int): The length of the maze.
            width (int): The width of the maze.
            nbr_player (int): The number of player in the maze.
            min_room_size (int): The minimum size of a room.
            max_room_size (int): The maximum size of a room.

        """
        # Initialize logger
        self.logger = Logger(self.__class__.__name__)

        # Set attributes
        self.length = length
        self.width = width
        self.nbr_player = nbr_player
        self.min_room_size = min_room_size
        self.max_room_size = max_room_size

        # Generate the maze
        self.maze_array = self.generate()

        # Create the entities
        self.structure_entities = self.__create_entities()

    def generate(
        self,
        length: int = None,
        width: int = None,
        nbr_player: int = None,
        min_room_size: int = None,
        max_room_size: int = None,
    ) -> None:
        """Generate the maze.

        Args:
            length (int): The length of the maze.
            width (int): The width of the maze.
            nbr_player (int): The number of player in the maze.
            min_room_size (int): The minimum size of a room.
            max_room_size (int): The maximum size of a room.

        Returns:
            np.ndarray: The maze.

        """
        # Set default arguments
        if length is None:
            length = self.length
        if width is None:
            width = self.width
        if nbr_player is None:
            nbr_player = self.nbr_player
        if min_room_size is None:
            min_room_size = self.min_room_size
        if max_room_size is None:
            max_room_size = self.max_room_size

        maze_array = np.zeros((length, width))

        # Add borders walls
        maze_array = np.pad(maze_array, 1, constant_values=-2)

        # Generate the maze
        for i in range(1, length + 1):
            for j in range(1, width + 1):
                # Generate a room if there is no room at this position or if the probability is met
                if maze_array[i, j] == 0:
                    max_length = np.min(
                        [max_room_size, maze_array[i:, j].nonzero()[0][0]]
                    )
                    max_width = np.min(
                        [max_room_size, maze_array[i, j:].nonzero()[0][0]]
                    )

                    # Generate a room
                    room_length = (
                        np.random.randint(min_room_size, max_length)
                        if max_length > min_room_size
                        else min_room_size
                    )
                    room_width = (
                        np.random.randint(min_room_size, max_width)
                        if max_width > min_room_size
                        else min_room_size
                    )
                    maze_array[i : i + room_length, j : j + room_width] = 1

                    # Add walls
                    maze_array[i - 1 : i + room_length + 1, j - 1] = -2
                    maze_array[i - 1 : i + room_length + 1, j + room_width] = -2
                    maze_array[i - 1, j - 1 : j + room_width + 1] = -2
                    maze_array[i + room_length, j - 1 : j + room_width + 1] = -2

                    # Add doors
                    maze_array[np.random.randint(i, i + room_length), j - 1] = -3
                    maze_array[i - 1, np.random.randint(j, j + room_width)] = -3
                    maze_array[
                        np.random.randint(i, i + room_length), j + room_width
                    ] = -3
                    maze_array[
                        i + room_length, np.random.randint(j, j + room_width)
                    ] = -3

        # Replace last 0 by 1
        maze_array[maze_array == 0] = 1

        # Delete doors where at least 3 of the neighbours are not 1
        for i in range(1, length + 1):
            for j in range(1, width + 1):
                if maze_array[i, j] == -3:
                    neighbours = [
                        maze_array[i - 1, j],
                        maze_array[i, j - 1],
                        maze_array[i + 1, j],
                        maze_array[i, j + 1],
                    ]
                    # If the door does not lead to anything
                    if neighbours.count(1) < 2:
                        maze_array[i, j] = -2
                    # If the door is in a corner
                    elif neighbours[0] != neighbours[2]:
                        maze_array[i, j] = 1

        ## Replace borders with walls again
        maze_array[0, :] = -2
        maze_array[:, 0] = -2
        maze_array[-1, :] = -2
        maze_array[:, -1] = -2

        return maze_array

    def __create_entities(self) -> List[Entity]:
        """Create the structure entities of the maze.

        Returns:
            List[Entity]: The entities.

        """
        structure_entities = []

        # Create the floors
        for i in range(self.length + 2):
            for j in range(self.width + 2):
                if self.maze_array[i, j] == 1:
                    structure_entities.append(
                        {"entity": Floor, "kwargs": {"x": j, "y": i}}
                    )

        return structure_entities


class Floor(AnimatedEntity, Entity):
    def __init__(self, x: int, y: int):
        # Define needed assets
        self.assets_needed = {
            "idle": [np.random.choice([f"floor_{i}" for i in range(1, 9)])],
        }

        # Init parent class
        Entity.__init__(self, log_initialization=False)
        AnimatedEntity.__init__(self)

        # Set attributes
        ## Get image size
        image = self.animations["idle"][0]
        self.x = x * image.get_width()
        self.y = y * image.get_height()

        # Set animation
        self.set_animation(
            "idle",
            reverse=np.random.choice([True, False]),
            rotation=np.random.choice([0, 90, 180, 270]),
        )

    def update(self, *args, **kwargs) -> List[Event]:
        """Update the entity. (Do nothing)

        Returns:
            List[Event]: The events.

        """
        return []


# ---------------------------------------------------------------------------- #
#                                 EXAMPLE_MAZE                                 #
# ---------------------------------------------------------------------------- #

# print(Maze().generate())
