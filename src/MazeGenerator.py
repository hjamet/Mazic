from random import randint
import pygame

WINDOW_SIZE = (1000, 1000)
"""The size of the window used to display the maze. This variable is not used in the final game, it is only used to test that the generation of the maze works correctly.""
"""


class Mazegenerator:
    """A class for generating a matrix representation of a labyrinth."""

    def __init__(self):
        """This class will produce a maze without worrying about displaying it in Pygame.
        To do this, it will perform the following operations:
        - Generate a list of rooms
        - Select the rooms so that they do not overlap
        - Select the most important rooms and delete the others
        - Create a graph from the rooms
        - Create a minimal spanning tree from the graph
        - Generation of corridors from the minimal spanning tree

        This process is inspired by the following article: https://www.gamedeveloper.com/programming/procedural-dungeon-generation-algorithm
        """
        self.rooms = []

    def a_generate_rooms(self, nbr_rooms: int, max_edge: int):
        """Step 1: Generates a list of random rectangular rooms.

        Args:
            nbr_rooms (int): The number of rooms to generate.
            max_edge (int): The maximum length of the edges of the rooms.
        """
        for _ in range(nbr_rooms):
            self.rooms.append(
                Room(
                    top_left=(
                        randint(-max_edge, max_edge),
                        randint(-max_edge, max_edge),
                    ),
                    bottom_right=(randint(0, max_edge), randint(0, max_edge)),
                )
            )

    def draw_maze(self):
        """Draw the maze in a Pygame window.

        This method is not intended to be used in the final game; it is only used to test that the maze generation works correctly.
        """
        window = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("Maze")
        pygame.display.set_icon(
            pygame.image.load("assets/frames/big_demon_idle_anim_f1.png")
        )

        generation_step = 0
        while True:
            window.fill((0, 0, 0))  # Clear the screen by filling it with black

            if len(self.rooms) != 0:
                # Center the maze
                min_x = min(room.top_left[0] for room in self.rooms)
                min_y = min(room.top_left[1] for room in self.rooms)
                max_x = max(room.bottom_right[0] for room in self.rooms)
                max_y = max(room.bottom_right[1] for room in self.rooms)

                # Calculate optimal window size
                window_width = max_x - min_x
                window_height = max_y - min_y

                # Calculate zoom
                zoom = min(1000 / window_width, 1000 / window_height) / 1.5

                for room in self.rooms:
                    top_left_x, top_left_y = room.top_left
                    bottom_right_x, bottom_right_y = room.bottom_right
                    width = bottom_right_x - top_left_x
                    height = bottom_right_y - top_left_y
                    pygame.draw.rect(
                        window,
                        (255, 255, 255),
                        (
                            int((top_left_x - min_x + WINDOW_SIZE[0] / 20) * zoom),
                            int((top_left_y - min_y + WINDOW_SIZE[1] / 20) * zoom),
                            int(width * zoom),
                            int(height * zoom),
                        ),
                        width=3,
                    )

            pygame.display.update()

            for event in pygame.event.get():
                # Iterate the generation step
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if generation_step == 0:
                        print("Generating rooms...")
                        self.a_generate_rooms(nbr_rooms=1, max_edge=100)
                elif event.type == pygame.QUIT:
                    return


class Room:
    """A class representing a rectangular room."""

    def __init__(self, top_left: tuple, bottom_right: tuple) -> None:
        """Create a room.

        Args:
            top_left (tuple): The coordinates of the top left corner of the room.
            bottom_right (tuple): The coordinates of the bottom right corner of the room.
        """
        self.top_left = top_left
        self.bottom_right = bottom_right


if __name__ == "__main__":
    maze = Mazegenerator()
    maze.draw_maze()
