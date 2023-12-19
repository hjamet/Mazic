from Logger import Logger
import numpy as np
import pygame

WINDOW_SIZE = (1000, 1000)
"""The size of the window used to display the maze. This variable is not used in the final game, it is only used to test that the generation of the maze works correctly.""
"""


class Mazegenerator:
    """A class for generating a matrix representation of a labyrinth."""

    def __init__(self):
        self.logger = Logger()

    def display(self, matrix: np.ndarray):
        """Displays the matrix in a window."""
        pygame.init()
        screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("Maze")
        screen.fill((255, 255, 255))
        for i in range(len(matrix)):
            for j in range(len(matrix[i])):
                if matrix[i][j] == 1:
                    pygame.draw.rect(screen, (0, 0, 0), (j * 10, i * 10, 10, 10))
        pygame.display.flip()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
