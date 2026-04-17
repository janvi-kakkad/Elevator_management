"""Canvas visualizer for smooth elevator shaft rendering in Tkinter."""

import tkinter as tk

import config
from elevator import ElevatorState

CANVAS_WIDTH = 600
CANVAS_HEIGHT = 600
MARGIN_X = 20
MARGIN_Y = 20
LABEL_WIDTH = 50
SHAFT_GAP = 12
CAR_WIDTH = 46
CAR_HEIGHT = 24
MARKER_SIZE = 6

COLOR_UP = "#3b82f6"
COLOR_DOWN = "#16a34a"
COLOR_IDLE = "#9ca3af"
COLOR_DOOR = "#facc15"
COLOR_PICKUP = "#f97316"
COLOR_DEST = "#ef4444"
COLOR_GRID = "#d1d5db"
COLOR_TEXT = "#111827"


class ElevatorVisualizer:
    """Draw and update elevator shaft graphics on a Tkinter canvas."""

    def __init__(self, canvas, num_floors, num_elevators):
        """
        Build persistent canvas items for shaft animation.

        Args:
            canvas: Tkinter Canvas widget.
            num_floors: Highest floor index as int.
            num_elevators: Number of elevators as int.

        Returns:
            None
        """
        self.canvas = canvas
        self.num_floors = num_floors
        self.num_elevators = num_elevators

        self.floor_label_items = {}
        self.car_items = {}
        self.car_text_items = {}
        self.pickup_marker_items = {}
        self.dest_marker_items = {}

        self._setup_geometry()
        self._create_static_grid()
        self._create_dynamic_items()

    def _setup_geometry(self):
        """
        Precompute geometry values for floor and shaft mapping.

        Args:
            None

        Returns:
            None
        """
        self.canvas.config(width=CANVAS_WIDTH, height=CANVAS_HEIGHT)

        floor_count = self.num_floors + 1
        usable_height = CANVAS_HEIGHT - (MARGIN_Y * 2)
        if floor_count > 1:
            self.floor_step = usable_height / float(floor_count - 1)
        else:
            self.floor_step = float(usable_height)

        shaft_zone_left = MARGIN_X + LABEL_WIDTH
        shaft_zone_width = CANVAS_WIDTH - shaft_zone_left - MARGIN_X
        self.column_width = shaft_zone_width / float(self.num_elevators)

    def _floor_to_y(self, floor_value):
        """
        Convert a floor value into pixel y position.

        Args:
            floor_value: Floor as float.

        Returns:
            float: Canvas y coordinate.
        """
        return CANVAS_HEIGHT - MARGIN_Y - (float(floor_value) * self.floor_step)

    def _shaft_left(self, elevator_id):
        """
        Compute left x of one elevator shaft column.

        Args:
            elevator_id: Elevator identifier as int.

        Returns:
            float: Left x coordinate for shaft.
        """
        base_left = MARGIN_X + LABEL_WIDTH
        return base_left + (self.column_width * elevator_id)

    def _create_static_grid(self):
        """
        Draw floor lines, labels, and shaft boundaries once.

        Args:
            None

        Returns:
            None
        """
        for floor in range(self.num_floors + 1):
            y = self._floor_to_y(floor)
            self.canvas.create_line(MARGIN_X, y, CANVAS_WIDTH - MARGIN_X, y, fill=COLOR_GRID)
            label = self.canvas.create_text(
                MARGIN_X + LABEL_WIDTH - 8,
                y,
                text=str(floor),
                anchor=tk.E,
                fill=COLOR_TEXT,
                font=("TkDefaultFont", 10, "normal"),
            )
            self.floor_label_items[floor] = label

        for elevator_id in range(self.num_elevators):
            left = self._shaft_left(elevator_id)
            right = left + self.column_width - SHAFT_GAP
            self.canvas.create_rectangle(
                left,
                MARGIN_Y,
                right,
                CANVAS_HEIGHT - MARGIN_Y,
                outline=COLOR_GRID,
            )

    def _create_dynamic_items(self):
        """
        Create car and stop-marker items that will be updated each tick.

        Args:
            None

        Returns:
            None
        """
        for elevator_id in range(self.num_elevators):
            left = self._shaft_left(elevator_id)
            right = left + self.column_width - SHAFT_GAP
            center_x = (left + right) / 2.0
            start_y = self._floor_to_y(0)

            car = self.canvas.create_rectangle(
                center_x - (CAR_WIDTH / 2.0),
                start_y - (CAR_HEIGHT / 2.0),
                center_x + (CAR_WIDTH / 2.0),
                start_y + (CAR_HEIGHT / 2.0),
                fill=COLOR_IDLE,
                outline=COLOR_TEXT,
            )
            text = self.canvas.create_text(
                center_x,
                start_y,
                text=f"? E{elevator_id}",
                fill=COLOR_TEXT,
                font=("TkDefaultFont", 9, "bold"),
            )

            self.car_items[elevator_id] = car
            self.car_text_items[elevator_id] = text
            self.pickup_marker_items[elevator_id] = {}
            self.dest_marker_items[elevator_id] = {}

            marker_x_pickup = center_x - CAR_WIDTH
            marker_x_dest = center_x + CAR_WIDTH

            for floor in range(self.num_floors + 1):
                y = self._floor_to_y(floor)
                pickup_marker = self.canvas.create_oval(
                    marker_x_pickup - MARKER_SIZE,
                    y - MARKER_SIZE,
                    marker_x_pickup + MARKER_SIZE,
                    y + MARKER_SIZE,
                    fill=COLOR_PICKUP,
                    outline="",
                    state=tk.HIDDEN,
                )
                dest_marker = self.canvas.create_oval(
                    marker_x_dest - MARKER_SIZE,
                    y - MARKER_SIZE,
                    marker_x_dest + MARKER_SIZE,
                    y + MARKER_SIZE,
                    fill=COLOR_DEST,
                    outline="",
                    state=tk.HIDDEN,
                )
                self.pickup_marker_items[elevator_id][floor] = pickup_marker
                self.dest_marker_items[elevator_id][floor] = dest_marker

    def _car_style(self, state, elevator_id):
        """
        Get symbol text and fill color for an elevator state.

        Args:
            state: ElevatorState value.
            elevator_id: Elevator identifier as int.

        Returns:
            tuple: (symbol_text, fill_color)
        """
        if state == ElevatorState.MOVING_UP:
            return f"? E{elevator_id}", COLOR_UP
        if state == ElevatorState.MOVING_DOWN:
            return f"? E{elevator_id}", COLOR_DOWN
        if state == ElevatorState.DOOR_OPEN:
            return f"[ E{elevator_id} ]", COLOR_DOOR
        if state == ElevatorState.DOOR_HOLDING:
            return f"[H E{elevator_id}]", COLOR_DOOR
        if state == ElevatorState.DOOR_CLOSING:
            return f"] E{elevator_id} [", COLOR_DOOR
        return f"? E{elevator_id}", COLOR_IDLE

    def _update_floor_highlights(self, elevators):
        """
        Bold floor labels when any elevator is exactly on that floor.

        Args:
            elevators: List of elevator objects.

        Returns:
            None
        """
        occupied = set()
        for elevator in elevators:
            floor_int = int(round(elevator.current_floor))
            if abs(elevator.current_floor - floor_int) < 0.1:
                occupied.add(floor_int)

        for floor, item_id in self.floor_label_items.items():
            font_weight = "bold" if floor in occupied else "normal"
            self.canvas.itemconfig(item_id, font=("TkDefaultFont", 10, font_weight))

    def _update_markers(self, elevators, waiting_passengers):
        """
        Show pickup and destination markers per elevator queue context.

        Args:
            elevators: List of elevator objects.
            waiting_passengers: List of Passenger objects.

        Returns:
            None
        """
        pickup_map = {}
        dest_map = {}

        for elevator in elevators:
            pickup_map[elevator.id] = set()
            dest_map[elevator.id] = set()

        for passenger in waiting_passengers:
            request = passenger.request
            if request.assigned_to is None:
                continue
            if request.assigned_to not in pickup_map:
                continue
            if not passenger.boarded:
                pickup_map[request.assigned_to].add(request.pickup_floor)
            if not request.served:
                dest_map[request.assigned_to].add(request.destination_floor)

        for elevator in elevators:
            elevator_id = elevator.id
            for floor in range(self.num_floors + 1):
                pickup_state = tk.NORMAL if floor in pickup_map[elevator_id] else tk.HIDDEN
                dest_state = tk.NORMAL if floor in dest_map[elevator_id] else tk.HIDDEN
                self.canvas.itemconfig(self.pickup_marker_items[elevator_id][floor], state=pickup_state)
                self.canvas.itemconfig(self.dest_marker_items[elevator_id][floor], state=dest_state)

    def redraw(self, elevators, waiting_passengers):
        """
        Update elevator car positions and marker visibility per tick.

        Args:
            elevators: List of elevator objects.
            waiting_passengers: List of Passenger objects.

        Returns:
            None
        """
        for elevator in elevators:
            elevator_id = elevator.id
            left = self._shaft_left(elevator_id)
            right = left + self.column_width - SHAFT_GAP
            center_x = (left + right) / 2.0
            center_y = self._floor_to_y(elevator.current_floor)

            self.canvas.coords(
                self.car_items[elevator_id],
                center_x - (CAR_WIDTH / 2.0),
                center_y - (CAR_HEIGHT / 2.0),
                center_x + (CAR_WIDTH / 2.0),
                center_y + (CAR_HEIGHT / 2.0),
            )
            self.canvas.coords(self.car_text_items[elevator_id], center_x, center_y)

            symbol, fill_color = self._car_style(elevator.state, elevator_id)
            self.canvas.itemconfig(self.car_items[elevator_id], fill=fill_color)
            self.canvas.itemconfig(self.car_text_items[elevator_id], text=symbol)

        self._update_markers(elevators, waiting_passengers)
        self._update_floor_highlights(elevators)
