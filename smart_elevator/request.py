"""Request and queue primitives for the Smart Elevator Management System."""

import time

import config


class Request:
    """
    Represent one passenger request from pickup floor to destination floor.

    Args:
        request_id: Auto-incremented request identifier as int.
        pickup_floor: Source floor as int.
        destination_floor: Destination floor as int.

    Returns:
        None
    """

    def __init__(self, request_id, pickup_floor, destination_floor):
        """
        Initialize a request and derive direction from floors.

        Args:
            request_id: Auto-incremented request identifier as int.
            pickup_floor: Source floor as int.
            destination_floor: Destination floor as int.

        Returns:
            None
        """
        if destination_floor == pickup_floor:
            # EC-03: Same-floor destination is invalid and must be rejected.
            raise ValueError("Destination must differ from pickup floor.")

        self.id = request_id
        self.pickup_floor = pickup_floor
        self.destination_floor = destination_floor

        # EC-04: Direction is always auto-derived from floor values.
        if destination_floor > pickup_floor:
            self.direction = config.DIRECTION_UP
        else:
            self.direction = config.DIRECTION_DOWN

        self.timestamp = time.time()
        self.assigned_to = None
        self.wait_start = self.timestamp
        self.pickup_time = None
        self.fuzzy_score = 0.0
        self.served = False


class Passenger:
    """
    Represent a passenger mapped to an originating request.

    Args:
        request: Request instance for this passenger.

    Returns:
        None
    """

    def __init__(self, request):
        """
        Initialize a passenger object.

        Args:
            request: Request instance for this passenger.

        Returns:
            None
        """
        self.request = request
        self.boarded = False


class RequestQueueManager:
    """
    Manage all requests and expose queue operations.

    Args:
        None

    Returns:
        None
    """

    def __init__(self):
        """
        Initialize the request queue manager.

        Args:
            None

        Returns:
            None
        """
        self._requests = []
        self._next_request_id = 1

    def _is_floor_in_range(self, floor):
        """
        Check whether a floor is inside current configured bounds.

        Args:
            floor: Candidate floor as int.

        Returns:
            bool: True if floor is valid for this building.
        """
        if config.NUM_FLOORS is None:
            return False
        return 0 <= floor <= config.NUM_FLOORS

    def add_request(self, pickup, destination):
        """
        Validate and append a new request.

        Args:
            pickup: Pickup floor as int.
            destination: Destination floor as int.

        Returns:
            Request | None: Created Request when valid, otherwise None.
        """
        if config.NUM_FLOORS is None:
            print("Building floor count is not configured yet.")
            return None

        if not isinstance(pickup, int) or not isinstance(destination, int):
            print("Pickup and destination must be integers.")
            return None

        if not self._is_floor_in_range(pickup) or not self._is_floor_in_range(destination):
            print("Pickup and destination must be within [0, NUM_FLOORS].")
            return None

        try:
            candidate_direction = config.DIRECTION_UP if destination > pickup else config.DIRECTION_DOWN

            # EC-01: Reject impossible upward movement from top floor.
            if pickup == config.NUM_FLOORS and candidate_direction == config.DIRECTION_UP:
                print("Cannot go UP from top floor.")
                return None

            # EC-02: Reject impossible downward movement from floor zero.
            if pickup == 0 and candidate_direction == config.DIRECTION_DOWN:
                print("Cannot go DOWN from floor 0.")
                return None

            request = Request(self._next_request_id, pickup, destination)
        except ValueError as error:
            print(str(error))
            return None

        self._next_request_id += 1
        self._requests.append(request)
        return request

    def mark_served(self, request_id):
        """
        Mark a request as served by identifier.

        Args:
            request_id: Request identifier as int.

        Returns:
            bool: True if a matching request is found and updated.
        """
        for request in self._requests:
            if request.id == request_id:
                request.served = True
                return True
        return False

    def get_pending(self):
        """
        Return all requests that are not served yet.

        Args:
            None

        Returns:
            list: Pending Request objects.
        """
        pending = []
        for request in self._requests:
            if not request.served:
                pending.append(request)
        return pending

    def get_all(self):
        """
        Return a shallow copy of all known requests.

        Args:
            None

        Returns:
            list: All Request objects.
        """
        return list(self._requests)
