"""Central dispatcher that assigns requests to elevators."""

import config
from elevator import ElevatorState
from request import Passenger

AT_FLOOR_TOLERANCE = 0.1


class Dispatcher:
    """Coordinate request assignment and stop queue updates."""

    def __init__(self, elevators, request_queue_manager, logger=None, fuzzy_engine=None, ga_optimizer=None):
        self.elevators = elevators
        self.request_queue_manager = request_queue_manager
        self.logger = logger
        self.fuzzy_engine = fuzzy_engine
        self.ga_optimizer = ga_optimizer
        self.waiting_passengers = []

    def _log_event(self, **kwargs):
        if self.logger is not None and hasattr(self.logger, "log_event"):
            self.logger.log_event(**kwargs)

    def _get_elevator_by_id(self, elevator_id):
        for elevator in self.elevators:
            if elevator.id == elevator_id:
                return elevator
        return None

    def _all_elevators_full(self):
        for elevator in self.elevators:
            if elevator.current_load < config.MAX_CAPACITY:
                return False
        return True

    def _fallback_direction_score(self, elevator, request_obj):
        service_direction = elevator.get_service_direction()

        if abs(elevator.current_floor - request_obj.pickup_floor) < AT_FLOOR_TOLERANCE:
            if service_direction in (config.DIRECTION_IDLE, request_obj.direction):
                return 1.0
            return 0.0

        if service_direction == config.DIRECTION_IDLE:
            return 0.7

        if service_direction != request_obj.direction:
            return 0.0

        if elevator.is_passing_by_eligible(request_obj.pickup_floor, request_obj.direction):
            return 1.0

        return 0.1

    def _fallback_fuzzy_score(self, elevator, request_obj):
        distance = abs(elevator.current_floor - request_obj.pickup_floor)
        direction_score = self._fallback_direction_score(elevator, request_obj)
        load_ratio = elevator.current_load / float(config.MAX_CAPACITY)

        if distance <= 2:
            distance_band = "Near"
        elif distance <= config.FUZZY_FAR_MIN:
            distance_band = "Medium"
        else:
            distance_band = "Far"

        if direction_score == 1.0:
            direction_band = "Same+PassBy"
        elif direction_score == 0.7:
            direction_band = "Idle"
        elif direction_score == 0.0:
            direction_band = "Opposite"
        else:
            direction_band = "Same"

        if load_ratio <= 0.3:
            load_band = "Light"
        elif load_ratio < 0.8:
            load_band = "Moderate"
        else:
            load_band = "Heavy"

        score = config.SCORE_MEDIUM
        score -= distance * 5
        score += direction_score * 20
        score -= load_ratio * 10

        if elevator.current_load == config.MAX_CAPACITY:
            score = 0.0

        score = max(0.0, min(float(config.SCORE_VERY_HIGH), score))
        descriptor = f"[{distance_band} | {direction_band} | {load_band}]"
        return score, descriptor, direction_score

    def _score_elevator(self, elevator, request_obj):
        if self.fuzzy_engine is not None and hasattr(self.fuzzy_engine, "score_elevator"):
            scored = self.fuzzy_engine.score_elevator(elevator, request_obj)
            if isinstance(scored, tuple) and len(scored) == 3:
                return scored

        return self._fallback_fuzzy_score(elevator, request_obj)

    def _pick_best_elevator(self, scored_rows):
        if not scored_rows:
            return None

        return max(
            scored_rows,
            key=lambda row: (
                row[1],
                1 if row[0].state == ElevatorState.IDLE else 0,
                -row[0].id,
            ),
        )

    def add_stop(self, elevator, floor, request_direction=None):
        return elevator.add_stop(floor, request_direction=request_direction)

    def _run_ga_if_available(self, elevator):
        if self.ga_optimizer is None:
            return 0.0

        if hasattr(self.ga_optimizer, "optimize"):
            result = self.ga_optimizer.optimize(elevator.id, elevator.current_floor, elevator.stop_queue)
            if isinstance(result, tuple) and len(result) == 2:
                route, improvement = result
                elevator.stop_queue = list(route)
                return float(improvement)
            if isinstance(result, list):
                elevator.stop_queue = list(result)
        return 0.0

    def _maybe_immediate_board(self, elevator, sim_time):
        if abs(elevator.current_floor - round(elevator.current_floor)) >= AT_FLOOR_TOLERANCE:
            return 0.0

        if elevator.state != ElevatorState.DOOR_OPEN:
            return 0.0

        elevator.handle_floor_arrival(
            int(round(elevator.current_floor)),
            self.waiting_passengers,
            current_sim_time=sim_time,
            request_queue_manager=self.request_queue_manager,
        )

        return self._run_ga_if_available(elevator)

    def _cleanup_obsolete_pickups(self):
        """Remove stale pickup stops from elevators after actual boarding elsewhere."""
        for passenger in self.waiting_passengers:
            request_obj = passenger.request
            if not passenger.boarded:
                continue

            assigned_elevator_id = request_obj.assigned_to
            for elevator in self.elevators:
                if elevator.id == assigned_elevator_id:
                    continue
                if request_obj.pickup_floor not in elevator.stop_queue:
                    continue

                # Keep pickup stop only if another unboarded request for same pickup is assigned here.
                keep_stop = False
                for other in self.waiting_passengers:
                    if other.boarded:
                        continue
                    if other.request.assigned_to != elevator.id:
                        continue
                    if other.request.pickup_floor == request_obj.pickup_floor:
                        keep_stop = True
                        break

                if not keep_stop:
                    elevator.stop_queue = [s for s in elevator.stop_queue if s != request_obj.pickup_floor]
    def _assignment_is_stale(self, request_obj):
        elevator = self._get_elevator_by_id(request_obj.assigned_to)
        if elevator is None:
            return True

        if elevator.current_load >= config.MAX_CAPACITY:
            return True

        at_pickup = abs(elevator.current_floor - request_obj.pickup_floor) < AT_FLOOR_TOLERANCE
        if at_pickup:
            return False

        if request_obj.pickup_floor in elevator.stop_queue:
            return False

        # If assigned elevator has no path to this pickup anymore, release it.
        if elevator.state == ElevatorState.IDLE and not elevator.stop_queue:
            return True

        return False

    def _assign_existing_request(self, request_obj, sim_time):
        scored_rows = []
        for elevator in self.elevators:
            score, descriptor, direction_score = self._score_elevator(elevator, request_obj)
            scored_rows.append((elevator, score, descriptor, direction_score))

        best = self._pick_best_elevator(scored_rows)
        if best is None:
            return None

        winner, winner_score, _, _ = best
        request_obj.assigned_to = winner.id
        request_obj.fuzzy_score = winner_score

        self.add_stop(winner, request_obj.pickup_floor, request_direction=request_obj.direction)
        self._run_ga_if_available(winner)

        if abs(winner.current_floor - request_obj.pickup_floor) < AT_FLOOR_TOLERANCE:
            self._maybe_immediate_board(winner, sim_time)

        return winner

    def assign(self, pickup_floor, destination_floor, sim_time=0.0):
        request_obj = self.request_queue_manager.add_request(pickup_floor, destination_floor)
        if request_obj is None:
            return None

        self.waiting_passengers.append(Passenger(request_obj))

        if self._all_elevators_full():
            print(f"All elevators full. Request #{request_obj.id} queued.")
            self._log_event(
                req_id=request_obj.id,
                sim_time=sim_time,
                event="WAITING",
                pickup_floor=request_obj.pickup_floor,
                dest_floor=request_obj.destination_floor,
                elevator_id=-1,
                fuzzy_score=0.0,
                wait_time=0.0,
                ga_improvement=0.0,
                note="all elevators full",
            )
            return request_obj

        winner = self._assign_existing_request(request_obj, sim_time)
        if winner is None:
            return request_obj

        print(
            f"Assigned Request #{request_obj.id}: "
            f"{request_obj.pickup_floor} -> {request_obj.destination_floor} to E{winner.id} "
            f"(score {request_obj.fuzzy_score:.1f})"
        )

        self._log_event(
            req_id=request_obj.id,
            sim_time=sim_time,
            event="ASSIGNED",
            pickup_floor=request_obj.pickup_floor,
            dest_floor=request_obj.destination_floor,
            elevator_id=winner.id,
            fuzzy_score=request_obj.fuzzy_score,
            wait_time=0.0,
            ga_improvement=0.0,
            note="",
        )

        return request_obj

    def reassign_waiting_requests(self, sim_time=0.0):
        self._cleanup_obsolete_pickups()
        for passenger in self.waiting_passengers:
            if passenger.boarded:
                continue

            request_obj = passenger.request
            if request_obj.served:
                continue

            if request_obj.assigned_to is not None:
                assigned_elevator = self._get_elevator_by_id(request_obj.assigned_to)
                if assigned_elevator is not None:
                    if (
                        abs(assigned_elevator.current_floor - request_obj.pickup_floor) < AT_FLOOR_TOLERANCE
                        and assigned_elevator.state == ElevatorState.DOOR_OPEN
                    ):
                        self._maybe_immediate_board(assigned_elevator, sim_time)
                        continue

                if self._assignment_is_stale(request_obj):
                    request_obj.assigned_to = None

            if request_obj.assigned_to is not None:
                continue

            if self._all_elevators_full():
                continue

            self._assign_existing_request(request_obj, sim_time)


