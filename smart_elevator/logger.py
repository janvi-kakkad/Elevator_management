"""In-memory event logger and summary reporting for the elevator simulation."""

import config

SEPARATOR_LENGTH = 61


class SimulationLogger:
    """Store simulation events and build text summaries for GUI display."""

    def __init__(self):
        """
        Initialize logger storage.

        Args:
            None

        Returns:
            None
        """
        self.events = []
        self.elevators = []

    def set_elevators(self, elevators):
        """
        Attach elevator references for summary metrics.

        Args:
            elevators: List of elevator objects.

        Returns:
            None
        """
        self.elevators = list(elevators)

    def log_event(self, **kwargs):
        """
        Append one event using the required schema keys.

        Args:
            **kwargs: Event values by field name.

        Returns:
            dict: Stored event dictionary.
        """
        entry = {
            "req_id": kwargs.get("req_id", 0),
            "sim_time": kwargs.get("sim_time", 0.0),
            "event": kwargs.get("event", "INFO"),
            "pickup_floor": kwargs.get("pickup_floor", 0),
            "dest_floor": kwargs.get("dest_floor", 0),
            "elevator_id": kwargs.get("elevator_id", -1),
            "fuzzy_score": kwargs.get("fuzzy_score", 0.0),
            "wait_time": kwargs.get("wait_time", 0.0),
            "ga_improvement": kwargs.get("ga_improvement", 0.0),
            "note": kwargs.get("note", ""),
        }
        self.events.append(entry)
        return entry

    def get_recent_events(self, count=20):
        """
        Return the most recent event entries.

        Args:
            count: Maximum number of entries as int.

        Returns:
            list: Recent event dictionaries.
        """
        return self.events[-count:]

    def get_all_events(self):
        """
        Return all stored events.

        Args:
            None

        Returns:
            list: All event dictionaries.
        """
        return list(self.events)

    def _request_stats(self):
        """
        Compute wait-time and request aggregates from event data.

        Args:
            None

        Returns:
            dict: Aggregate request metrics.
        """
        request_ids = set()
        wait_entries = []
        total_ga_improvement = 0.0

        for entry in self.events:
            if entry["req_id"] > 0:
                request_ids.add(entry["req_id"])
            if entry["wait_time"] > 0.0:
                wait_entries.append((entry["req_id"], entry["wait_time"]))
            total_ga_improvement += entry["ga_improvement"]

        if wait_entries:
            avg_wait = sum(item[1] for item in wait_entries) / len(wait_entries)
            best_req, best_wait = min(wait_entries, key=lambda item: item[1])
            worst_req, worst_wait = max(wait_entries, key=lambda item: item[1])
        else:
            avg_wait = 0.0
            best_req = 0
            best_wait = 0.0
            worst_req = 0
            worst_wait = 0.0

        return {
            "total_requests": len(request_ids),
            "avg_wait": avg_wait,
            "best_wait": best_wait,
            "best_req": best_req,
            "worst_wait": worst_wait,
            "worst_req": worst_req,
            "total_ga_improvement": total_ga_improvement,
        }

    def _per_elevator_stats(self):
        """
        Build per-elevator served count, wait, and load factor metrics.

        Args:
            None

        Returns:
            dict: Stats keyed by elevator id.
        """
        stats = {}

        for elevator in self.elevators:
            stats[elevator.id] = {
                "floors_traveled": elevator.total_floors_traveled,
                "served": 0,
                "wait_sum": 0.0,
                "wait_count": 0,
                "load_factor": 0.0,
            }

        for entry in self.events:
            elevator_id = entry["elevator_id"]
            if elevator_id not in stats:
                continue
            if entry["event"] == "ALIGHTED":
                stats[elevator_id]["served"] += 1
            if entry["wait_time"] > 0.0:
                stats[elevator_id]["wait_sum"] += entry["wait_time"]
                stats[elevator_id]["wait_count"] += 1

        for elevator in self.elevators:
            if config.MAX_CAPACITY > 0:
                stats[elevator.id]["load_factor"] = (
                    elevator.current_load / float(config.MAX_CAPACITY)
                ) * 100.0

        return stats

    def print_summary(self):
        """
        Build and return formatted system summary text.

        Args:
            None

        Returns:
            str: Multi-line summary report.
        """
        req_stats = self._request_stats()
        per_elevator = self._per_elevator_stats()

        total_floors = 0.0
        for elevator in self.elevators:
            total_floors += elevator.total_floors_traveled

        separator = "-" * SEPARATOR_LENGTH
        lines = [
            separator,
            "SYSTEM SUMMARY",
            separator,
            f"Total requests handled : {req_stats['total_requests']}",
            f"Total floors traveled  : {total_floors:.1f} (across all elevators)",
            f"Average wait time      : {req_stats['avg_wait']:.1f}s",
            f"Best wait time         : {req_stats['best_wait']:.1f}s (Request #{req_stats['best_req']})",
            f"Worst wait time        : {req_stats['worst_wait']:.1f}s (Request #{req_stats['worst_req']})",
            f"Total GA improvements  : {req_stats['total_ga_improvement']:.1f} floors saved",
            "",
            "Per-elevator summary:",
        ]

        for elevator in self.elevators:
            stats = per_elevator[elevator.id]
            avg_wait = 0.0
            if stats["wait_count"] > 0:
                avg_wait = stats["wait_sum"] / stats["wait_count"]
            lines.append(
                f"E{elevator.id}: {stats['floors_traveled']:.1f} floors | {stats['served']} served"
            )
            lines.append(
                f"       | avg wait {avg_wait:.1f}s | load factor {stats['load_factor']:.1f}%"
            )

        return "\n".join(lines)
