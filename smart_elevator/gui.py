"""Tkinter GUI for running and observing the elevator simulation."""

import tkinter as tk
from tkinter import ttk

import config
from dispatcher import Dispatcher
from elevator import Elevator
from fuzzy import FuzzyEngine
from ga import GeneticOptimizer
from logger import SimulationLogger
from request import RequestQueueManager
from visualizer import ElevatorVisualizer

RIGHT_PANEL_WIDTH = 420
CANVAS_PANEL_WEIGHT = 3
CONTROL_PANEL_WEIGHT = 2
LOG_LINES_MAX = 20


class ElevatorGUI:
    """Create and control the simulation window and update loop."""

    def __init__(self, root, elevators, dispatcher, logger):
        self.root = root
        self.elevators = elevators
        self.dispatcher = dispatcher
        self.logger = logger

        self.sim_time = 0.0
        self.is_running = False
        self.after_id = None
        self.tick_size = config.SIM_TICK_INTERVAL_MS / 1000.0

        self.logger.set_elevators(self.elevators)
        self._build_layout()
        self._update_status_panel()
        self._update_log_feed()

    def _build_layout(self):
        self.root.title("Smart Elevator Management System")

        container = ttk.Frame(self.root, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        container.columnconfigure(0, weight=CANVAS_PANEL_WEIGHT)
        container.columnconfigure(1, weight=CONTROL_PANEL_WEIGHT)
        container.rowconfigure(0, weight=1)

        left_panel = ttk.Frame(container)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        right_panel = ttk.Frame(container, width=RIGHT_PANEL_WIDTH)
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.grid_propagate(False)

        self.canvas = tk.Canvas(left_panel, bg="white", highlightthickness=1, highlightbackground="#d1d5db")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.visualizer = ElevatorVisualizer(
            self.canvas,
            num_floors=config.NUM_FLOORS,
            num_elevators=len(self.elevators),
        )

        self._build_request_section(right_panel)
        self._build_simulation_section(right_panel)
        self._build_status_section(right_panel)
        self._build_log_section(right_panel)
        self._build_summary_section(right_panel)

    def _build_request_section(self, parent):
        section = ttk.LabelFrame(parent, text="New Request", padding=8)
        section.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(section, text="Pickup floor:").grid(row=0, column=0, sticky="w")
        ttk.Label(section, text="Destination:").grid(row=1, column=0, sticky="w", pady=(6, 0))

        self.pickup_entry = ttk.Entry(section)
        self.pickup_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        self.destination_entry = ttk.Entry(section)
        self.destination_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))

        submit_button = ttk.Button(section, text="Submit Request", command=self._on_submit_request)
        submit_button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        self.error_label = ttk.Label(section, text="", foreground="#b91c1c")
        self.error_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

        section.columnconfigure(1, weight=1)

    def _build_simulation_section(self, parent):
        section = ttk.LabelFrame(parent, text="Simulation", padding=8)
        section.pack(fill=tk.X, pady=(0, 8))

        self.toggle_button = ttk.Button(section, text="Start Simulation", command=self._toggle_simulation)
        self.toggle_button.pack(fill=tk.X)

        self.time_label = ttk.Label(section, text="Sim time: 0.0s")
        self.time_label.pack(anchor="w", pady=(6, 0))

    def _build_status_section(self, parent):
        section = ttk.LabelFrame(parent, text="Elevator Status", padding=8)
        section.pack(fill=tk.X, pady=(0, 8))

        self.status_labels = {}
        for elevator in self.elevators:
            label = ttk.Label(section, text="", justify=tk.LEFT)
            label.pack(anchor="w", fill=tk.X, pady=(0, 4))
            self.status_labels[elevator.id] = label

    def _build_log_section(self, parent):
        section = ttk.LabelFrame(parent, text="Log Feed", padding=8)
        section.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.log_text = tk.Text(section, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(section, orient=tk.VERTICAL, command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll.set)

        section.columnconfigure(0, weight=1)
        section.rowconfigure(0, weight=1)

    def _build_summary_section(self, parent):
        section = ttk.Frame(parent)
        section.pack(fill=tk.X)

        summary_button = ttk.Button(section, text="Show Summary", command=self._show_summary)
        summary_button.pack(fill=tk.X, pady=(0, 6))

        reset_button = ttk.Button(section, text="Reset Simulation", command=self._reset_simulation)
        reset_button.pack(fill=tk.X)

    def _set_error(self, message):
        self.error_label.config(text=message)

    def _parse_floor_inputs(self):
        pickup_raw = self.pickup_entry.get().strip()
        destination_raw = self.destination_entry.get().strip()

        try:
            pickup_floor = int(pickup_raw)
            destination_floor = int(destination_raw)
        except ValueError:
            self._set_error("Pickup and destination must be integers.")
            return None

        if pickup_floor < 0 or pickup_floor > config.NUM_FLOORS:
            self._set_error("Pickup floor out of range.")
            return None

        if destination_floor < 0 or destination_floor > config.NUM_FLOORS:
            self._set_error("Destination floor out of range.")
            return None

        if pickup_floor == destination_floor:
            self._set_error("Destination must differ from pickup floor.")
            return None

        return pickup_floor, destination_floor

    def _on_submit_request(self):
        parsed = self._parse_floor_inputs()
        if parsed is None:
            return

        pickup_floor, destination_floor = parsed
        self._set_error("")

        request_obj = self.dispatcher.assign(pickup_floor, destination_floor, sim_time=self.sim_time)
        if request_obj is None:
            self._set_error("Request rejected.")
            return

        self.pickup_entry.delete(0, tk.END)
        self.destination_entry.delete(0, tk.END)
        self._update_log_feed()
        self.visualizer.redraw(self.elevators, self.dispatcher.waiting_passengers)
        self._update_status_panel()

    def _toggle_simulation(self):
        self.is_running = not self.is_running
        if self.is_running:
            self.toggle_button.config(text="Pause Simulation")
            self._schedule_next_tick()
        else:
            self.toggle_button.config(text="Start Simulation")
            if self.after_id is not None:
                self.root.after_cancel(self.after_id)
                self.after_id = None

    def _schedule_next_tick(self):
        self.after_id = self.root.after(config.SIM_TICK_INTERVAL_MS, self._tick)

    def _tick(self):
        if not self.is_running:
            return

        self.sim_time += self.tick_size

        for elevator in self.elevators:
            elevator.update(
                self.tick_size,
                all_passengers_waiting=self.dispatcher.waiting_passengers,
                current_sim_time=self.sim_time,
                request_queue_manager=self.dispatcher.request_queue_manager,
            )

        self.dispatcher.reassign_waiting_requests(sim_time=self.sim_time)

        self.visualizer.redraw(self.elevators, self.dispatcher.waiting_passengers)
        self._update_status_panel()
        self._update_log_feed()
        self.time_label.config(text=f"Sim time: {self.sim_time:.1f}s")

        self._schedule_next_tick()

    def _reset_simulation(self):
        """Reset all runtime state without restarting the app."""
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

        self.is_running = False
        self.toggle_button.config(text="Start Simulation")
        self.sim_time = 0.0
        self.time_label.config(text="Sim time: 0.0s")
        self._set_error("")

        elevator_count = len(self.elevators)
        new_elevators = [Elevator(elevator_id, start_floor=0) for elevator_id in range(elevator_count)]

        request_queue_manager = RequestQueueManager()
        new_logger = SimulationLogger()
        fuzzy_engine = FuzzyEngine()
        ga_optimizer = GeneticOptimizer()

        new_dispatcher = Dispatcher(
            elevators=new_elevators,
            request_queue_manager=request_queue_manager,
            logger=new_logger,
            fuzzy_engine=fuzzy_engine,
            ga_optimizer=ga_optimizer,
        )

        self.elevators = new_elevators
        self.dispatcher = new_dispatcher
        self.logger = new_logger
        self.logger.set_elevators(self.elevators)

        self.pickup_entry.delete(0, tk.END)
        self.destination_entry.delete(0, tk.END)

        self.canvas.delete("all")
        self.visualizer = ElevatorVisualizer(
            self.canvas,
            num_floors=config.NUM_FLOORS,
            num_elevators=len(self.elevators),
        )

        self._update_status_panel()
        self._update_log_feed()
        self.visualizer.redraw(self.elevators, self.dispatcher.waiting_passengers)

    def _update_status_panel(self):
        for elevator in self.elevators:
            status_text = (
                f"E{elevator.id}  Floor: {elevator.current_floor:.1f}  "
                f"State: {elevator.state.value}  Load: {elevator.current_load}/{config.MAX_CAPACITY}\n"
                f"       Queue: {elevator.stop_queue}\n"
                f"       Direction: {elevator.direction}"
            )
            self.status_labels[elevator.id].config(text=status_text)

    def _format_log_line(self, entry):
        return (
            f"t={entry['sim_time']:.1f}s | {entry['event']} | "
            f"Req#{entry['req_id']} P{entry['pickup_floor']}->D{entry['dest_floor']} | "
            f"E{entry['elevator_id']} | Fuzzy {entry['fuzzy_score']:.1f}"
            + (f" | {entry['note']}" if entry['note'] else "")
        )

    def _update_log_feed(self):
        lines = [self._format_log_line(entry) for entry in self.logger.get_recent_events(LOG_LINES_MAX)]

        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        if lines:
            self.log_text.insert(tk.END, "\n".join(lines))
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)

    def _show_summary(self):
        summary_window = tk.Toplevel(self.root)
        summary_window.title("System Summary")

        text_widget = tk.Text(summary_window, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(summary_window, orient=tk.VERTICAL, command=text_widget.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.configure(yscrollcommand=scroll.set)

        text_widget.insert(tk.END, self.logger.print_summary())
        text_widget.config(state=tk.DISABLED)
