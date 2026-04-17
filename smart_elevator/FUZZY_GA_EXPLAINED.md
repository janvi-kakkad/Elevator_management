# Smart Elevator Management System - Fuzzy Logic and Genetic Algorithm Deep Dive

## Why this project uses both Fuzzy + GA
This system solves two different decision layers:

1. **Which elevator should take a new request?**
This is uncertain and context-heavy (distance, direction compatibility, load). A strict if-else rule usually feels brittle, so we use **Fuzzy Logic**.

2. **In what stop order should that elevator serve queued stops?**
This is a route optimization problem over permutations. We use a **Genetic Algorithm (GA)** to search for better orderings.

So, Fuzzy handles **assignment quality under uncertainty**, and GA handles **route optimization after assignment**.

---

## Fuzzy Logic in this project

### Inputs used by fuzzy engine
For each elevator and incoming request, fuzzy scoring uses:

1. **Distance**
- `abs(elevator.current_floor - request.pickup_floor)`

2. **Direction compatibility**
- High when elevator is moving in same useful direction and request is ahead
- Medium for idle elevators
- Low/zero for opposite direction or already-passed situations

3. **Load ratio**
- `elevator.current_load / MAX_CAPACITY`

### Membership functions
The fuzzy engine uses triangular/trapezoidal style membership functions:

- Distance: `near`, `medium`, `far`
- Load: `light`, `moderate`, `heavy`
- Direction is treated as crisp compatibility values (`1.0`, `0.7`, `0.1`, `0.0`)

### Rule base (Mamdani style)
Each rule strength is computed with **min(antecedents)**.
Examples:

- near + same-direction/pass-by + light -> very high score
- near + idle -> high
- medium + opposite -> very low
- far -> very low

### Defuzzification
The engine computes a crisp score with weighted average:

- numerator = sum(rule_strength * output_score)
- denominator = sum(rule_strength)
- score = numerator / denominator (if denominator > 0)

Special behaviors:

- Full elevator (`current_load == MAX_CAPACITY`) gets hard score `0`
- Pass-by useful match can get bonus (capped)

### Why this helps in practice
Fuzzy avoids rigid switching boundaries. For example:

- Two elevators can both be acceptable, but one is "slightly better" due to combined context.
- Door state + future service direction can still get meaningful preference.
- It captures realistic heuristics without requiring perfect prediction.

---

## Genetic Algorithm in this project

### Problem GA solves
After an elevator receives/updates stops, the stop order may be inefficient.
GA tries to reduce total travel distance from current floor.

### Chromosome representation
A chromosome is a permutation of stops, e.g.:

- `[4, 8, 6]`

This means: visit 4, then 8, then 6.

### Fitness
Fitness is negative route distance:

- `fitness = -total_distance`

Since GA maximizes fitness, shorter distance means better (less negative).

### GA pipeline implemented
1. Generate random permutations as initial population
2. Evaluate fitness
3. Keep elites
4. Tournament selection for parents
5. OX1 crossover (order-preserving for permutations)
6. Swap mutation with configured probability
7. Repeat for configured generations
8. Return best chromosome

### Why GA is suitable here
Stop ordering is combinatorial. Exhaustive search is expensive as queue grows.
GA gives good near-optimal routes quickly and stays simple enough for undergraduate explanation.

---

## End-to-end flow (Fuzzy + GA together)
1. User creates a request (pickup, destination)
2. Dispatcher evaluates all elevators with fuzzy score
3. Best elevator selected
4. Pickup stop inserted
5. GA optionally optimizes stop queue
6. Elevator moves with LOOK-like direction handling
7. On floor arrival, board/alight updates queue and load
8. If elevator becomes full, pickup-only stops are dropped and only onboard destinations remain

This layered approach keeps behavior realistic:
- Assignment quality from fuzzy reasoning
- Route efficiency from evolutionary optimization

---

## Important edge behaviors currently handled
- Same-floor request can be handled immediately
- Opposite-direction same-floor request is deprioritized for ongoing lift
- Full elevators reject extra boarding and requests are re-queued
- Full elevator route is restricted to onboard passenger destinations
- Fuzzy still drives assignment preference in ambiguous cases

---

## Viva-ready explanation in one line
**Fuzzy decides the best elevator under uncertain real-time conditions; GA then optimizes that elevator's stop sequence to reduce travel distance.**
