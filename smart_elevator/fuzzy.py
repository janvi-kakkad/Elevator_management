"""Fuzzy inference engine for elevator assignment decisions."""

import config
from elevator import ElevatorState

DIST_NEAR_FULL_MAX = 2.0
DIST_NEAR_ZERO_MIN = 5.0
DIST_MEDIUM_MIN = 2.0
DIST_MEDIUM_PEAK = 5.0
DIST_MEDIUM_MAX = 9.0
DIST_FAR_ZERO_MAX = 7.0
DIST_FAR_FULL_MIN = 10.0

LOAD_LIGHT_FULL_MAX = 0.3
LOAD_LIGHT_ZERO_MIN = 0.6
LOAD_MODERATE_MIN = 0.2
LOAD_MODERATE_PEAK = 0.5
LOAD_MODERATE_MAX = 0.8
LOAD_HEAVY_ZERO_MAX = 0.6
LOAD_HEAVY_FULL_MIN = 1.0

DIRECTION_IDLE_SCORE = 0.7
DIRECTION_SAME_PASSED_SCORE = 0.1
DIRECTION_OPPOSITE_SCORE = 0.0
DIRECTION_PASS_BY_SCORE = 1.0
PASS_BY_BONUS = 10.0
AT_FLOOR_TOLERANCE = 0.1


class FuzzyEngine:
    """Compute fuzzy suitability scores for assigning requests to elevators."""

    def near(self, distance_value):
        if distance_value <= DIST_NEAR_FULL_MAX:
            return 1.0
        if distance_value >= DIST_NEAR_ZERO_MIN:
            return 0.0
        return (DIST_NEAR_ZERO_MIN - distance_value) / (DIST_NEAR_ZERO_MIN - DIST_NEAR_FULL_MAX)

    def medium(self, distance_value):
        if distance_value <= DIST_MEDIUM_MIN or distance_value >= DIST_MEDIUM_MAX:
            return 0.0
        if DIST_MEDIUM_MIN < distance_value <= DIST_MEDIUM_PEAK:
            return (distance_value - DIST_MEDIUM_MIN) / (DIST_MEDIUM_PEAK - DIST_MEDIUM_MIN)
        return (DIST_MEDIUM_MAX - distance_value) / (DIST_MEDIUM_MAX - DIST_MEDIUM_PEAK)

    def far(self, distance_value):
        if distance_value <= DIST_FAR_ZERO_MAX:
            return 0.0
        if distance_value >= DIST_FAR_FULL_MIN:
            return 1.0
        return (distance_value - DIST_FAR_ZERO_MAX) / (DIST_FAR_FULL_MIN - DIST_FAR_ZERO_MAX)

    def light(self, load_ratio):
        if load_ratio <= LOAD_LIGHT_FULL_MAX:
            return 1.0
        if load_ratio >= LOAD_LIGHT_ZERO_MIN:
            return 0.0
        return (LOAD_LIGHT_ZERO_MIN - load_ratio) / (LOAD_LIGHT_ZERO_MIN - LOAD_LIGHT_FULL_MAX)

    def moderate(self, load_ratio):
        if load_ratio <= LOAD_MODERATE_MIN or load_ratio >= LOAD_MODERATE_MAX:
            return 0.0
        if LOAD_MODERATE_MIN < load_ratio <= LOAD_MODERATE_PEAK:
            return (load_ratio - LOAD_MODERATE_MIN) / (LOAD_MODERATE_PEAK - LOAD_MODERATE_MIN)
        return (LOAD_MODERATE_MAX - load_ratio) / (LOAD_MODERATE_MAX - LOAD_MODERATE_PEAK)

    def heavy(self, load_ratio):
        if load_ratio <= LOAD_HEAVY_ZERO_MAX:
            return 0.0
        if load_ratio >= LOAD_HEAVY_FULL_MIN:
            return 1.0
        return (load_ratio - LOAD_HEAVY_ZERO_MAX) / (LOAD_HEAVY_FULL_MIN - LOAD_HEAVY_ZERO_MAX)

    def direction_score(self, elevator, request_obj):
        service_direction = elevator.get_service_direction()

        if abs(elevator.current_floor - request_obj.pickup_floor) < AT_FLOOR_TOLERANCE:
            if service_direction in (config.DIRECTION_IDLE, request_obj.direction):
                return DIRECTION_PASS_BY_SCORE
            return DIRECTION_OPPOSITE_SCORE

        if elevator.state == ElevatorState.IDLE:
            return DIRECTION_IDLE_SCORE

        if service_direction == config.DIRECTION_IDLE:
            return DIRECTION_IDLE_SCORE

        if service_direction == request_obj.direction:
            if elevator.is_passing_by_eligible(request_obj.pickup_floor, request_obj.direction):
                return DIRECTION_PASS_BY_SCORE
            return DIRECTION_SAME_PASSED_SCORE

        return DIRECTION_OPPOSITE_SCORE

    def _distance_label(self, near_val, medium_val, far_val):
        if near_val >= medium_val and near_val >= far_val:
            return "Near"
        if medium_val >= near_val and medium_val >= far_val:
            return "Medium"
        return "Far"

    def _load_label(self, light_val, moderate_val, heavy_val):
        if light_val >= moderate_val and light_val >= heavy_val:
            return "Light"
        if moderate_val >= light_val and moderate_val >= heavy_val:
            return "Moderate"
        return "Heavy"

    def _direction_label(self, direction_val):
        if direction_val == DIRECTION_PASS_BY_SCORE:
            return "Same+PassBy"
        if direction_val == DIRECTION_IDLE_SCORE:
            return "Idle(0.7)"
        if direction_val == DIRECTION_OPPOSITE_SCORE:
            return "Opposite"
        return "Same+Passed"

    def score_elevator(self, elevator, request_obj):
        distance_value = abs(elevator.current_floor - request_obj.pickup_floor)
        load_ratio = elevator.current_load / float(config.MAX_CAPACITY)

        near_val = self.near(distance_value)
        medium_val = self.medium(distance_value)
        far_val = self.far(distance_value)

        light_val = self.light(load_ratio)
        moderate_val = self.moderate(load_ratio)
        heavy_val = self.heavy(load_ratio)

        direction_val = self.direction_score(elevator, request_obj)

        dir_same = 1.0 if direction_val == DIRECTION_PASS_BY_SCORE else 0.0
        dir_idle = 1.0 if direction_val == DIRECTION_IDLE_SCORE else 0.0
        dir_opposite_like = 1.0 if direction_val <= DIRECTION_SAME_PASSED_SCORE else 0.0

        rules = [
            (min(near_val, dir_same, light_val), float(config.SCORE_VERY_HIGH)),
            (min(near_val, dir_same, moderate_val), float(config.SCORE_HIGH)),
            (min(near_val, dir_same, heavy_val), float(config.SCORE_MEDIUM)),
            (min(near_val, dir_idle), float(config.SCORE_HIGH)),
            (min(near_val, dir_opposite_like), float(config.SCORE_LOW)),
            (min(medium_val, dir_same, light_val), float(config.SCORE_HIGH)),
            (min(medium_val, dir_same, heavy_val), float(config.SCORE_MEDIUM)),
            (min(medium_val, dir_idle), float(config.SCORE_MEDIUM)),
            (min(medium_val, dir_opposite_like), float(config.SCORE_VERY_LOW)),
            (far_val, float(config.SCORE_VERY_LOW)),
        ]

        numerator = 0.0
        denominator = 0.0
        for strength, output_value in rules:
            numerator += strength * output_value
            denominator += strength

        score = 0.0
        if denominator > 0.0:
            score = numerator / denominator

        if elevator.current_load == config.MAX_CAPACITY:
            score = 0.0

        pass_by_eligible = elevator.is_passing_by_eligible(request_obj.pickup_floor, request_obj.direction)
        if direction_val == DIRECTION_PASS_BY_SCORE and pass_by_eligible:
            score = min(float(config.SCORE_VERY_HIGH), score + PASS_BY_BONUS)

        distance_label = self._distance_label(near_val, medium_val, far_val)
        direction_label = self._direction_label(direction_val)
        load_label = self._load_label(light_val, moderate_val, heavy_val)
        descriptor = f"[{distance_label} | {direction_label} | {load_label}]"

        return float(score), descriptor, float(direction_val)
