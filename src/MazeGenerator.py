from Logger import Logger

WINDOW_SIZE = (1000, 1000)
"""The size of the window used to display the maze. This variable is not used in the final game, it is only used to test that the generation of the maze works correctly.""
"""


class Mazegenerator:
    """A class for generating a matrix representation of a labyrinth."""

    def __init__(self):
        self.logger = Logger()
