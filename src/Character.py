from src.Logger import Logger


class Character:
    def __init__(self, name: str) -> None:
        # Saves *args
        self.name = name

        # Instantiates Logger
        self.logger = Logger(f"{self.__class__.__name__}_{self.name}")
