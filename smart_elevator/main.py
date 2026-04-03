"""Entry point for the Smart Elevator Management System."""

import tkinter as tk

import config
from dispatcher import Dispatcher
from elevator import Elevator
from fuzzy import FuzzyEngine
from ga import GeneticOptimizer
from gui import ElevatorGUI
from logger import SimulationLogger
from request import RequestQueueManager

DEFAULT_NUM_ELEVATORS = config.MIN_ELEVATORS
DEFAULT_NUM_FLOORS = config.MAX_FLOORS // config.MIN_ELEVATORS


def create_system(num_elevators):
    """
    Create core simulation objects and wire dependencies.

    Args:
        num_elevators: Number of elevators as int.

    Returns:
        tuple: (elevators, dispatcher, logger)
    """
    elevators = []
    for elevator_id in range(num_elevators):
        elevators.append(Elevator(elevator_id, start_floor=0))

    request_queue_manager = RequestQueueManager()
    logger = SimulationLogger()
    fuzzy_engine = FuzzyEngine()
    ga_optimizer = GeneticOptimizer()

    dispatcher = Dispatcher(
        elevators=elevators,
        request_queue_manager=request_queue_manager,
        logger=logger,
        fuzzy_engine=fuzzy_engine,
        ga_optimizer=ga_optimizer,
    )

    return elevators, dispatcher, logger


def main():
    """
    Configure system defaults and launch Tkinter GUI directly.

    Args:
        None

    Returns:
        None
    """
    config.set_building_config(DEFAULT_NUM_ELEVATORS, DEFAULT_NUM_FLOORS)

    elevators, dispatcher, logger = create_system(config.NUM_ELEVATORS)

    root = tk.Tk()
    app = ElevatorGUI(root, elevators, dispatcher, logger)
    app.visualizer.redraw(elevators, dispatcher.waiting_passengers)
    root.mainloop()


if __name__ == "__main__":
    main()
