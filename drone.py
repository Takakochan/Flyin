from abc import ABC

class Drone(ABC):
    def __init__(self, id, current, path):
        