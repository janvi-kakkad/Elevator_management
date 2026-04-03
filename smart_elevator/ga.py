"""Genetic Algorithm optimizer for elevator stop ordering."""

import random

import config

PERCENT_BASE = 100.0


class GeneticOptimizer:
    """Optimize stop order permutations to reduce travel distance."""

    def fitness(self, chromosome, start_floor):
        """
        Compute fitness as negative total travel distance.

        Args:
            chromosome: Proposed stop order as list[int].
            start_floor: Elevator current floor as float.

        Returns:
            float: Negative total distance where higher is better.
        """
        total_distance = 0.0
        current_floor = float(start_floor)

        for floor in chromosome:
            total_distance += abs(float(floor) - current_floor)
            current_floor = float(floor)

        return -total_distance

    def _route_distance(self, route, start_floor):
        """
        Compute non-negative route distance from a start floor.

        Args:
            route: Stop order as list[int].
            start_floor: Elevator current floor as float.

        Returns:
            float: Total distance traveled in floors.
        """
        return -self.fitness(route, start_floor)

    def _initial_population(self, stop_queue):
        """
        Build random permutation population for GA evolution.

        Args:
            stop_queue: Current stop list as list[int].

        Returns:
            list: Population of chromosomes.
        """
        population = []
        base_chromosome = list(stop_queue)

        for _ in range(config.GA_POPULATION_SIZE):
            chromosome = list(base_chromosome)
            random.shuffle(chromosome)
            population.append(chromosome)

        return population

    def _tournament_selection(self, population, start_floor):
        """
        Select one chromosome using tournament selection.

        Args:
            population: Population of chromosomes.
            start_floor: Elevator current floor as float.

        Returns:
            list[int]: Winning chromosome copy.
        """
        pool_size = min(config.GA_TOURNAMENT_SIZE, len(population))
        contestants = random.sample(population, pool_size)
        winner = max(contestants, key=lambda chrom: self.fitness(chrom, start_floor))
        return list(winner)

    def _ox1_crossover(self, parent_a, parent_b):
        """
        Perform Order-1 crossover (OX1) on two parent permutations.

        Args:
            parent_a: Parent chromosome as list[int].
            parent_b: Parent chromosome as list[int].

        Returns:
            list[int]: Child chromosome.
        """
        chromosome_length = len(parent_a)
        if chromosome_length <= 1:
            return list(parent_a)

        cut_start, cut_end = sorted(random.sample(range(chromosome_length), 2))
        child = [None] * chromosome_length

        # Preserve middle segment from parent A.
        child[cut_start:cut_end] = parent_a[cut_start:cut_end]

        fill_index = 0
        for value in parent_b:
            if value in child:
                continue
            while child[fill_index] is not None:
                fill_index += 1
            child[fill_index] = value

        return child

    def _swap_mutation(self, chromosome):
        """
        Apply swap mutation with configured mutation probability.

        Args:
            chromosome: Chromosome to mutate as list[int].

        Returns:
            list[int]: Mutated chromosome.
        """
        if len(chromosome) <= 1:
            return chromosome

        if random.random() < config.GA_MUTATION_RATE:
            idx_a, idx_b = random.sample(range(len(chromosome)), 2)
            chromosome[idx_a], chromosome[idx_b] = chromosome[idx_b], chromosome[idx_a]

        return chromosome

    def _best_chromosome(self, population, start_floor):
        """
        Return the fittest chromosome from a population.

        Args:
            population: Population of chromosomes.
            start_floor: Elevator current floor as float.

        Returns:
            list[int]: Best chromosome copy.
        """
        best = max(population, key=lambda chrom: self.fitness(chrom, start_floor))
        return list(best)

    def optimize(self, elevator_id, start_floor, stop_queue):
        """
        Optimize stop order using GA and print trace output.

        Args:
            elevator_id: Elevator identifier as int.
            start_floor: Elevator current floor as float.
            stop_queue: Current stop list as list[int].

        Returns:
            tuple: (best_route: list[int], improvement_percent: float)
        """
        route_input = list(stop_queue)
        stop_count = len(route_input)

        print(f"GA Optimizing E{elevator_id} route ({stop_count} stops)...")
        print(f"  Start floor: {float(start_floor):.1f}")

        if stop_count <= 1:
            print("GA skipped (<=1 stop).")
            return route_input, 0.0

        population = self._initial_population(route_input)

        best_gen0 = self._best_chromosome(population, start_floor)
        best_gen0_fitness = self.fitness(best_gen0, start_floor)
        print(f"  Gen 0  Best: {best_gen0_fitness:.1f}")

        mid_generation = config.GA_GENERATIONS // 2

        for generation in range(1, config.GA_GENERATIONS + 1):
            # Evaluate population and keep elites unchanged.
            ranked_population = sorted(
                population,
                key=lambda chrom: self.fitness(chrom, start_floor),
                reverse=True,
            )
            next_population = [list(chrom) for chrom in ranked_population[:config.GA_ELITISM_COUNT]]

            while len(next_population) < config.GA_POPULATION_SIZE:
                parent_a = self._tournament_selection(ranked_population, start_floor)
                parent_b = self._tournament_selection(ranked_population, start_floor)
                child = self._ox1_crossover(parent_a, parent_b)
                child = self._swap_mutation(child)
                next_population.append(child)

            population = next_population

            if generation == mid_generation or generation == config.GA_GENERATIONS:
                best_now = self._best_chromosome(population, start_floor)
                best_now_fitness = self.fitness(best_now, start_floor)
                print(f"  Gen {generation} Best: {best_now_fitness:.1f}")

        best_route = self._best_chromosome(population, start_floor)
        best_distance = self._route_distance(best_route, start_floor)

        fcfs_route = list(route_input)
        fcfs_distance = self._route_distance(fcfs_route, start_floor)

        saved_floors = fcfs_distance - best_distance
        improvement_percent = 0.0
        if fcfs_distance > 0.0:
            improvement_percent = (saved_floors / fcfs_distance) * PERCENT_BASE

        print(f"  Final route: {best_route} -> Total distance: {best_distance:.1f} floors")
        print(f"  FCFS baseline: {fcfs_route} -> Total distance: {fcfs_distance:.1f} floors")
        print(f"  GA improvement: {saved_floors:.1f} floors ({improvement_percent:.1f}%)")

        if saved_floors == 0.0:
            print("  (Route already optimal)")

        return best_route, improvement_percent
