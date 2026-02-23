"""
Mock welder archetypes for enterprise demo.
Each archetype has an arc_type that drives frame generation (angle/amps/thermal profiles).
"""

import random
from typing import List

# arc ∈ fast_learner|consistent_expert|plateaued|declining|new_hire|volatile|stitch_expert|continuous_novice
WELDER_ARCHETYPES = [
    {"welder_id": "mike-chen", "name": "Mike Chen", "arc": "fast_learner", "sessions": 5, "base": 58, "delta": 4},
    {"welder_id": "sara-okafor", "name": "Sara Okafor", "arc": "consistent_expert", "sessions": 5, "base": 88, "delta": 1},
    {"welder_id": "james-park", "name": "James Park", "arc": "plateaued", "sessions": 5, "base": 71, "delta": 0},
    {"welder_id": "lucia-reyes", "name": "Lucia Reyes", "arc": "declining", "sessions": 5, "base": 76, "delta": -4},
    {"welder_id": "tom-bradley", "name": "Tom Bradley", "arc": "new_hire", "sessions": 3, "base": 42, "delta": 6},
    {"welder_id": "ana-silva", "name": "Ana Silva", "arc": "volatile", "sessions": 5, "base": 65, "delta": 0},
    {"welder_id": "derek-kwon", "name": "Derek Kwon", "arc": "fast_learner", "sessions": 5, "base": 61, "delta": 5},
    {"welder_id": "priya-nair", "name": "Priya Nair", "arc": "consistent_expert", "sessions": 5, "base": 91, "delta": 0},
    {"welder_id": "marcus-bell", "name": "Marcus Bell", "arc": "declining", "sessions": 5, "base": 80, "delta": -5},
    {"welder_id": "expert-benchmark", "name": "Expert Benchmark", "arc": "consistent_expert", "sessions": 5, "base": 93, "delta": 0.5},
    {"welder_id": "expert_aluminium_001", "name": "Senior Welder A", "arc": "stitch_expert", "sessions": 4, "base": 85, "delta": 4},
    {"welder_id": "novice_aluminium_001", "name": "Trainee Welder B", "arc": "continuous_novice", "sessions": 6, "base": 48, "delta": -3},
]


def generate_score_arc(base: float, delta: float, sessions: int, arc_type: str) -> List[float]:
    """
    Generate expected score arc for validation/tuning only. Actual scores come from score_session.
    volatile: random swing; else: base + delta * session_idx + noise.
    """
    scores: List[float] = []
    for i in range(sessions):
        if arc_type == "volatile":
            score = base + random.choice([-12, -6, 0, 8, 14])
        else:
            noise = random.uniform(-2, 2)
            score = base + (delta * i) + noise
        scores.append(round(min(max(score, 0), 100), 1))
    return scores


__all__ = ["WELDER_ARCHETYPES", "generate_score_arc"]
