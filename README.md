# Smart Elevator Management System

A Python-based simulation of an intelligent multi-elevator system that uses **Fuzzy Logic** to assign the best elevator to a request, and a **Genetic Algorithm** to plan the most efficient route for that elevator.

---

## What Does This Project Do?

Imagine a building with multiple elevators. When someone presses the call button on a floor, the system has to decide:
1. **Which elevator should respond?** (handled by Fuzzy Logic)
2. **In what order should that elevator visit all its pending stops?** (handled by Genetic Algorithm)

This project simulates that entire decision-making process in Python — without any strict hardcoded rules. Instead, it uses AI-inspired techniques to make smart, real-world-like decisions.

---

## How It Works

### Part 1 — Fuzzy Logic: Choosing the Right Elevator

When a person requests an elevator, the system looks at **every available elevator** and scores them based on three factors:

| Factor | What It Means |
|--------|--------------|
| **Distance** | How many floors away is the elevator from the person? |
| **Direction** | Is the elevator already heading towards the person, or going the opposite way? |
| **Load** | How many people are already inside the elevator? |

These factors don't just give a simple yes/no answer — they are evaluated on a **scale** (like "somewhat close", "very far", "moderately loaded"). This is what makes it *fuzzy* — it handles situations that aren't black and white.

**Examples of the rules used:**
- If an elevator is **close** + going in the **same direction** + is **lightly loaded** → give it a **very high score**
- If an elevator is **far away** → give it a **very low score**
- If an elevator is **completely full** → immediately give it a **score of 0** (it cannot take anyone)

The elevator with the highest final score is selected.

---

### Part 2 — Genetic Algorithm: Planning the Best Route

Once an elevator is assigned, it may already have several pending stops. For example, it needs to go to floors 3, 7, and 5. The question is: **in what order?**

The Genetic Algorithm (GA) figures this out by:

1. **Creating many random orderings** of the stops (called a "population")
2. **Measuring how good each ordering is** — shorter total travel = better
3. **Keeping the best orderings**, combining them, and making small changes
4. **Repeating this process** over many rounds (called "generations")
5. **Returning the best stop order found**

This is inspired by how nature evolves better solutions over time — hence the name *Genetic* Algorithm.

---

## End-to-End Flow

Here's what happens from start to finish when someone calls an elevator:

```
Person presses call button
        ↓
System scores all elevators using Fuzzy Logic
        ↓
Best elevator is selected
        ↓
Person's pickup floor is added to that elevator's stop list
        ↓
Genetic Algorithm rearranges stops for shortest route
        ↓
Elevator moves floor by floor (using LOOK-style direction logic)
        ↓
People board and exit at their floors
        ↓
If elevator gets full → only serves people already inside
```

---

##  Special Situations Handled

- **Same floor request** — handled immediately without delay
- **Elevator going the opposite direction** — that elevator is given lower priority
- **Elevator completely full** — rejects new boarders; pending requests go back in the queue
- **Full elevator route** — restricted to only the destinations of people already inside
- **Ambiguous cases** — fuzzy logic still gives a preference score rather than failing

---

## Getting Started

### Requirements

- Python 3.x
- No external libraries required (uses only Python standard library)

### Run the Project

```bash
# Clone the repository
git clone https://github.com/janvi-kakkad/Elevator_management.git

# Navigate to the project folder
cd Elevator_management/smart_elevator

# Run the main simulation
python main.py
```

---

## Project Structure

```
Elevator_management/
│
├── smart_elevator/          # Main project folder
│   ├── main.py              # Entry point — runs the simulation
│   ├── elevator.py          # Elevator class — movement, load, stops
│   ├── dispatcher.py        # Assigns elevators using Fuzzy Logic
│   ├── fuzzy_engine.py      # Fuzzy membership functions and rules
│   └── genetic_algo.py      # Genetic Algorithm for stop optimization
│
├── .gitignore
└── README.md
```

---

##  Technical Details

### Fuzzy Logic Engine

- **Membership functions used:** Triangular and Trapezoidal (for distance and load)
- **Rule evaluation:** Mamdani style — each rule's strength = minimum of its conditions
- **Defuzzification:** Weighted average — `score = Σ(rule_strength × score) / Σ(rule_strength)`

### Genetic Algorithm

- **Chromosome:** A permutation of stop floors (e.g., `[4, 8, 6]` means visit 4 → 8 → 6)
- **Fitness function:** Negative total travel distance (shorter = better)
- **Selection:** Tournament selection
- **Crossover:** OX1 (Order Crossover) — preserves stop order validity
- **Mutation:** Random swap of two stops in the sequence
- **Elitism:** Best solutions are kept across generations

---

##  Why Use Both Fuzzy Logic AND Genetic Algorithm?

These two techniques solve **two different problems**:

| Problem | Why this technique? |
|---------|-------------------|
| Which elevator to pick? | Fuzzy Logic — because it's uncertain and context-heavy. Hard if-else rules break easily. |
| What order to visit stops? | Genetic Algorithm — because it's a combinatorial optimization problem. Trying all orderings is too slow. |

Together, they make the system both **smart in assignment** and **efficient in routing**.

---

##  One-Line Summary

> **Fuzzy Logic picks the best elevator under uncertain real-world conditions. The Genetic Algorithm then optimizes that elevator's stop order to minimize total travel distance.**

---
