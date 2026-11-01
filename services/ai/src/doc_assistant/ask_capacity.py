"""Bound the number of concurrent and waiting queries in one service process."""

from threading import BoundedSemaphore, Semaphore


class AskCapacity:
    def __init__(self, running: int = 2, waiting: int = 4) -> None:
        self.admitted = BoundedSemaphore(running + waiting)
        self.running = Semaphore(running)
