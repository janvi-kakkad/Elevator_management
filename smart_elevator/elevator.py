"""Elevator state machine and LOOK-based movement logic."""

from enum import Enum

import config


class ElevatorState(Enum):
    """Represent all runtime states for one elevator car."""

    IDLE = "IDLE"
    MOVING_UP = "MOVING_UP"
    MOVING_DOWN = "MOVING_DOWN"
    DOOR_OPEN = "DOOR_OPEN"
    DOOR_CLOSING = "DOOR_CLOSING"
    DOOR_HOLDING = "DOOR_HOLDING"


class Elevator:
    """Model one elevator and update it on every simulation tick."""

    def __init__(self, elevator_id, start_floor=0):
        self.id = elevator_id
        self.current_floor = float(start_floor)
        self.state = ElevatorState.IDLE
        self.direction = config.DIRECTION_IDLE
        self.stop_queue = []
        self.passengers = []
        self.current_load = 0
        self.total_floors_traveled = 0.0
        self.door_timer = 0.0
        self.door_hold_timer = 0.0

    def _is_at_floor(self, floor):
        return abs(self.current_floor - float(floor)) < 0.1

    def _nearest_stop(self):
        if not self.stop_queue:
            return None
        return min(self.stop_queue, key=lambda stop: abs(stop - self.current_floor))

    def get_service_direction(self):
        """Infer serving direction, including door states with pending intent."""
        if self.state == ElevatorState.MOVING_UP:
            return config.DIRECTION_UP
        if self.state == ElevatorState.MOVING_DOWN:
            return config.DIRECTION_DOWN

        if self.direction in (config.DIRECTION_UP, config.DIRECTION_DOWN):
            return self.direction

        if not self.stop_queue:
            return config.DIRECTION_IDLE

        nearest = self._nearest_stop()
        if nearest is None:
            return config.DIRECTION_IDLE
        if nearest > self.current_floor:
            return config.DIRECTION_UP
        if nearest < self.current_floor:
            return config.DIRECTION_DOWN
        return config.DIRECTION_IDLE

    def _set_motion_toward(self, target_floor):
        if target_floor is None:
            self.state = ElevatorState.IDLE
            self.direction = config.DIRECTION_IDLE
            return

        if self._is_at_floor(target_floor):
            self.current_floor = float(target_floor)
            self.state = ElevatorState.DOOR_OPEN
            self.door_timer = float(config.DOOR_OPEN_TIME)
            return

        if target_floor > self.current_floor:
            self.direction = config.DIRECTION_UP
            self.state = ElevatorState.MOVING_UP
            return

        self.direction = config.DIRECTION_DOWN
        self.state = ElevatorState.MOVING_DOWN

    def is_passing_by_eligible(self, floor, direction):
        service_direction = self.get_service_direction()

        if service_direction == config.DIRECTION_UP:
            return direction == config.DIRECTION_UP and self.current_floor < floor

        if service_direction == config.DIRECTION_DOWN:
            return direction == config.DIRECTION_DOWN and self.current_floor > floor

        return False

    def add_stop(self, floor, request_direction=None):
        floor = int(floor)

        if floor in self.stop_queue:
            return False

        if self._is_at_floor(floor):
            self.current_floor = float(floor)
            self.state = ElevatorState.DOOR_OPEN
            self.door_timer = float(config.DOOR_OPEN_TIME)
            return True

        if request_direction is not None and self.is_passing_by_eligible(floor, request_direction):
            self.stop_queue.append(floor)
            if self.get_service_direction() == config.DIRECTION_UP:
                self.stop_queue.sort()
            else:
                self.stop_queue.sort(reverse=True)
        else:
            self.stop_queue.append(floor)

        if self.state == ElevatorState.IDLE and self.direction == config.DIRECTION_IDLE:
            nearest = self._nearest_stop()
            self._set_motion_toward(nearest)

        return True

    def _enforce_full_capacity_route(self):
        """When full, keep only onboard passenger destination stops."""
        if self.current_load < config.MAX_CAPACITY:
            return

        onboard_destinations = []
        for passenger in self.passengers:
            destination = passenger.request.destination_floor
            if destination not in onboard_destinations:
                onboard_destinations.append(destination)

        if not onboard_destinations:
            return

        new_queue = [stop for stop in self.stop_queue if stop in onboard_destinations]
        if not new_queue:
            new_queue = list(onboard_destinations)

        service_direction = self.get_service_direction()
        if service_direction == config.DIRECTION_UP:
            new_queue.sort()
        elif service_direction == config.DIRECTION_DOWN:
            new_queue.sort(reverse=True)
        else:
            new_queue.sort(key=lambda floor: abs(floor - self.current_floor))

        self.stop_queue = new_queue
    def _restore_destinations_from_passengers(self):
        """Ensure onboard passenger destinations are always present in stop queue."""
        if not self.passengers:
            return

        for passenger in self.passengers:
            destination = passenger.request.destination_floor
            if destination not in self.stop_queue:
                self.stop_queue.append(destination)

        service_direction = self.get_service_direction()
        if service_direction == config.DIRECTION_UP:
            self.stop_queue.sort()
        elif service_direction == config.DIRECTION_DOWN:
            self.stop_queue.sort(reverse=True)
        else:
            self.stop_queue.sort(key=lambda floor: abs(floor - self.current_floor))

    def _choose_next_direction_after_arrival(self):
        if not self.stop_queue:
            self.direction = config.DIRECTION_IDLE
            return

        above = [stop for stop in self.stop_queue if stop >= self.current_floor]
        below = [stop for stop in self.stop_queue if stop <= self.current_floor]

        if self.direction == config.DIRECTION_UP:
            if above:
                self.direction = config.DIRECTION_UP
            elif below:
                self.direction = config.DIRECTION_DOWN
        elif self.direction == config.DIRECTION_DOWN:
            if below:
                self.direction = config.DIRECTION_DOWN
            elif above:
                self.direction = config.DIRECTION_UP
        else:
            nearest = self._nearest_stop()
            if nearest is None:
                self.direction = config.DIRECTION_IDLE
            elif nearest >= self.current_floor:
                self.direction = config.DIRECTION_UP
            else:
                self.direction = config.DIRECTION_DOWN

    def _remove_served_stop(self, floor):
        self.stop_queue = [stop for stop in self.stop_queue if stop != floor]

    def handle_floor_arrival(self, floor, all_passengers_waiting, current_sim_time=0.0, request_queue_manager=None):
        remaining_passengers = []
        for passenger in self.passengers:
            if passenger.request.destination_floor == floor:
                self.current_load -= 1
                passenger.request.served = True
                print(f"E{self.id}: Passenger alighted at floor {floor}.")
            else:
                remaining_passengers.append(passenger)
        self.passengers = remaining_passengers
        self._enforce_full_capacity_route()

        boarded_any = False
        for waiting_passenger in all_passengers_waiting:
            request = waiting_passenger.request
            if waiting_passenger.boarded:
                continue
            if request.pickup_floor != floor:
                continue

            service_direction = self.get_service_direction()
            same_direction = request.direction == service_direction
            idle_service = service_direction == config.DIRECTION_IDLE
            assigned_here = request.assigned_to == self.id
            # If this elevator was explicitly assigned for this pickup floor,
            # boarding must happen even when movement direction just changed.
            if not same_direction and not idle_service and not assigned_here:
                continue

            if self.current_load < config.MAX_CAPACITY:
                waiting_passenger.boarded = True
                request.assigned_to = self.id
                request.pickup_time = current_sim_time
                self.passengers.append(waiting_passenger)
                self.current_load += 1
                boarded_any = True
                print(f"E{self.id}: Passenger boarded at floor {floor}, going to {request.destination_floor}.")
                self.add_stop(request.destination_floor, request_direction=request.direction)
                # Full elevator should not continue pickup-only stops.
                self._enforce_full_capacity_route()
            else:
                print(f"E{self.id}: FULL. Passenger at floor {floor} must wait.")
                print(f"E{self.id} is at full capacity ({self.current_load}/{config.MAX_CAPACITY}). Request re-queued.")
                if request_queue_manager is not None:
                    request.assigned_to = None
                self._enforce_full_capacity_route()

        if boarded_any:
            self.door_hold_timer = float(config.DOOR_HOLD_MAX_TIME)

    def _update_door_states(self, tick_size):
        if self.state == ElevatorState.DOOR_OPEN:
            self.door_timer -= tick_size
            if self.door_hold_timer > 0.0:
                self.state = ElevatorState.DOOR_HOLDING
                return
            if self.door_timer <= 0.0:
                self.state = ElevatorState.DOOR_CLOSING
                self.door_timer = float(config.DOOR_CLOSE_TIME)
            return

        if self.state == ElevatorState.DOOR_HOLDING:
            self.door_hold_timer -= tick_size
            seconds_left = max(0.0, self.door_hold_timer)
            print(f"E{self.id}: Door held - passenger boarding. Safety timer: {seconds_left:.1f}s")
            if self.door_hold_timer <= 0.0:
                print(f"E{self.id}: Door hold timeout. Closing door.")
                self.state = ElevatorState.DOOR_CLOSING
                self.door_timer = float(config.DOOR_CLOSE_TIME)
            return

        if self.state == ElevatorState.DOOR_CLOSING:
            self.door_timer -= tick_size
            if self.door_timer <= 0.0:
                self._restore_destinations_from_passengers()
                if not self.stop_queue:
                    self.state = ElevatorState.IDLE
                    self.direction = config.DIRECTION_IDLE
                    return

                self._choose_next_direction_after_arrival()
                if self.direction == config.DIRECTION_UP:
                    self.state = ElevatorState.MOVING_UP
                elif self.direction == config.DIRECTION_DOWN:
                    self.state = ElevatorState.MOVING_DOWN
                else:
                    self.state = ElevatorState.IDLE

    def _move_one_tick(self, tick_size):
        speed = 1.0 / float(config.FLOOR_TRAVEL_TIME)
        distance_this_tick = speed * tick_size

        if self.state == ElevatorState.MOVING_UP:
            self.current_floor += distance_this_tick
            self.total_floors_traveled += distance_this_tick
        elif self.state == ElevatorState.MOVING_DOWN:
            self.current_floor -= distance_this_tick
            self.total_floors_traveled += distance_this_tick

        if config.NUM_FLOORS is not None:
            if self.current_floor < 0.0:
                self.current_floor = 0.0
            if self.current_floor > float(config.NUM_FLOORS):
                self.current_floor = float(config.NUM_FLOORS)

    def _check_arrival(self, all_passengers_waiting, current_sim_time, request_queue_manager):
        arrived_floor = int(round(self.current_floor))
        if arrived_floor not in self.stop_queue:
            return

        self.current_floor = float(arrived_floor)
        self._remove_served_stop(arrived_floor)
        # LOOK turnaround must happen in same tick on arrival.
        self._choose_next_direction_after_arrival()
        self.state = ElevatorState.DOOR_OPEN
        self.door_timer = float(config.DOOR_OPEN_TIME)
        self.handle_floor_arrival(
            arrived_floor,
            all_passengers_waiting,
            current_sim_time=current_sim_time,
            request_queue_manager=request_queue_manager,
        )
    def _recover_boundary_stall(self):
        """Recover when state/direction is invalid at floor boundaries."""
        if self.state == ElevatorState.MOVING_DOWN and self.current_floor <= 0.0:
            above = [stop for stop in self.stop_queue if stop > self.current_floor]
            if above:
                self.direction = config.DIRECTION_UP
                self.state = ElevatorState.MOVING_UP
            else:
                self.direction = config.DIRECTION_IDLE
                self.state = ElevatorState.IDLE

        if config.NUM_FLOORS is not None and self.state == ElevatorState.MOVING_UP and self.current_floor >= float(config.NUM_FLOORS):
            below = [stop for stop in self.stop_queue if stop < self.current_floor]
            if below:
                self.direction = config.DIRECTION_DOWN
                self.state = ElevatorState.MOVING_DOWN
            else:
                self.direction = config.DIRECTION_IDLE
                self.state = ElevatorState.IDLE

    def update(self, tick_size, all_passengers_waiting=None, current_sim_time=0.0, request_queue_manager=None):
        if all_passengers_waiting is None:
            all_passengers_waiting = []

        if self.state in (ElevatorState.DOOR_OPEN, ElevatorState.DOOR_HOLDING, ElevatorState.DOOR_CLOSING):
            self._update_door_states(tick_size)
            return

        if self.state in (ElevatorState.MOVING_UP, ElevatorState.MOVING_DOWN) and not self.stop_queue:
            self._restore_destinations_from_passengers()
            if not self.stop_queue:
                self.state = ElevatorState.IDLE
                self.direction = config.DIRECTION_IDLE
                return

        if self.state == ElevatorState.IDLE:
            if not self.stop_queue:
                self._restore_destinations_from_passengers()
            if not self.stop_queue:
                return
            nearest = self._nearest_stop()
            self._set_motion_toward(nearest)
            if self.state != ElevatorState.DOOR_OPEN:
                return
            self.handle_floor_arrival(
                int(round(self.current_floor)),
                all_passengers_waiting,
                current_sim_time=current_sim_time,
                request_queue_manager=request_queue_manager,
            )
            return

        self._move_one_tick(tick_size)
        self._check_arrival(all_passengers_waiting, current_sim_time, request_queue_manager)
        if self.state in (ElevatorState.MOVING_UP, ElevatorState.MOVING_DOWN):
            self._recover_boundary_stall()











