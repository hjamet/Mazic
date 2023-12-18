from random import randint
import pygame
from typing import List
import numpy as np

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
                    top_left=(0, 0),
                    bottom_right=(randint(0, max_edge), randint(0, max_edge)),
                )
            )

    def b_separates_rooms(self):
        """Step 2: Select the rooms so that they do not overlap.
        Make also sure that every room is sticking to another one.
        This function is meant to be call iteratively until all rooms are separated.

        Returns:
            bool: True if there are still overlapping rooms, False otherwise.
        """
        # Calculate overlapping rooms
        overlapping_area = 0
        for i, room1 in enumerate(self.rooms):
            overlapping_rooms = room1.is_overlapping(self.rooms)
            overlapping_area += sum(
                room1.overlapping_area(overlapping_room)
                for overlapping_room in overlapping_rooms[i:]
            )
        strength = np.sqrt(overlapping_area) / len(self.rooms)

        for i, room1 in enumerate(self.rooms):
            # Calculate all other rooms Gravity Center
            other_rooms = [room2 for j, room2 in enumerate(self.rooms) if j != i]
            other_rooms_centers = [room.get_center() for room in other_rooms] + [(0, 0)]
            other_rooms_gravity_center = (
                sum(other_room_center[0] for other_room_center in other_rooms_centers)
                / len(other_rooms_centers),
                sum(other_room_center[1] for other_room_center in other_rooms_centers)
                / len(other_rooms_centers),
            )

            # Calculate overlapping rooms Gravity Center
            overlapping_rooms = room1.is_overlapping(other_rooms)
            overlapping_rooms_centers = [
                room.get_center() for room in overlapping_rooms
            ]
            overlapping_rooms_gravity_center = (
                (
                    sum(
                        overlapping_room_center[0]
                        for overlapping_room_center in overlapping_rooms_centers
                    )
                    / len(overlapping_rooms_centers),
                    sum(
                        overlapping_room_center[1]
                        for overlapping_room_center in overlapping_rooms_centers
                    )
                    / len(overlapping_rooms_centers),
                )
                if len(overlapping_rooms_centers) != 0
                else None
            )

            # Move the room away from the overlapping rooms
            # Move the room towards the other rooms
            room1.move_towards(
                other_rooms_gravity_center,
                distance=strength / 2,
            )
            if overlapping_rooms_gravity_center is not None:
                room1.move_away(
                    overlapping_rooms_gravity_center,
                    distance=strength,
                )

        print(strength)

        return True

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
                        self.a_generate_rooms(nbr_rooms=20, max_edge=100)
                        generation_step += 1
                    elif generation_step == 1:
                        if not (self.b_separates_rooms()):
                            generation_step += 1
                elif event.type == pygame.QUIT:
                    return


class Room:
    """A class representing a rectangular room."""

    def __init__(self, top_left: tuple, bottom_right: tuple):
        """Create a room.

        Args:
            top_left (tuple): The coordinates of the top left corner of the room.
            bottom_right (tuple): The coordinates of the bottom right corner of the room.
        """
        self.top_left = top_left
        self.bottom_right = bottom_right

    def get_center(self):
        """Returns the coordinates of the center of the room."""
        return (
            (self.top_left[0] + self.bottom_right[0]) / 2,
            (self.top_left[1] + self.bottom_right[1]) / 2,
        )

    def is_overlapping(self, rooms=List):
        """Returns True if the room is overlapping with another one, False otherwise.

        Args:
            rooms (List[Room]): The list of rooms to check for overlapping.

        Returns:
            List[Room]: The list of rooms to check for overlapping.
        """
        overlapping = []
        for room in rooms:
            if (
                self.top_left[0] < room.bottom_right[0]
                and self.bottom_right[0] > room.top_left[0]
                and self.top_left[1] < room.bottom_right[1]
                and self.bottom_right[1] > room.top_left[1]
            ):
                overlapping.append(room)
        return overlapping

    def overlapping_area(self, room):
        """Returns the overlapping area between the room and another one.

        Args:
            room (Room): The other room.

        Returns:
            int: The overlapping area.
        """
        return max(
            0,
            min(self.bottom_right[0], room.bottom_right[0])
            - max(self.top_left[0], room.top_left[0]),
        ) * max(
            0,
            min(self.bottom_right[1], room.bottom_right[1])
            - max(self.top_left[1], room.top_left[1]),
        )

    def move_away(self, point: tuple, distance: int):
        """Move the room away from a point.

        Args:
            point (tuple): The point to move the room away from.
            distance (int): The distance to move the room away from the point.
        """
        center_x, center_y = self.get_center()
        point_x, point_y = point

        # Calculate vector
        vect = (
            (((center_x - point_x) > 0) * 2 - 1) * distance,
            (((center_y - point_y) > 0) * 2 - 1) * distance,
        )

        # Update coords
        self.top_left = (
            self.top_left[0] + vect[0],
            self.top_left[1] + vect[1],
        )
        self.bottom_right = (
            self.bottom_right[0] + vect[0],
            self.bottom_right[1] + vect[1],
        )

    def move_towards(self, point: tuple, distance: int):
        """Move the room towards a point.

        Args:
            point (tuple): The point to move the room towards.
            distance (int): The distance to move the room towards the point.
        """
        center_x, center_y = self.get_center()
        point_x, point_y = point

        # Calculate vector
        vect = (
            (((center_x - point_x) > 0) * 2 - 1) * distance,
            (((center_y - point_y) > 0) * 2 - 1) * distance,
        )

        # Update coords
        self.top_left = (
            self.top_left[0] - vect[0],
            self.top_left[1] - vect[1],
        )
        self.bottom_right = (
            self.bottom_right[0] - vect[0],
            self.bottom_right[1] - vect[1],
        )


if __name__ == "__main__":
    maze = Mazegenerator()
    maze.draw_maze()
