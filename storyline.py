"""
Mission Briefings, Narrative Lore, and Audio-Log Transmissions.
"""

LORE_INTRO = {
    "title": "MISSION: PROTOCOL OMEGA",
    "stardate": "CYBER-ERA 2187.04",
    "location": "AERIS-IV DEEP EXTRACTION COLONY",
    "briefing": (
        "Colony Sector 7 has fallen silent. A hyper-evolving xenomorphic bio-construct "
        "— code-named 'The Stalker' — has breached quarantine and hijacked the station grid.\n\n"
        "Your crew was ambushed. You are the sole survivor inside the central research core.\n\n"
        "OBJECTIVE:\n"
        "1. Recover 3 High-Energy Hyper-Matter Cores to restore emergency station generator.\n"
        "2. Evacuate to the Airlock Bay before the organism recalculates your coordinates.\n"
        "3. Watch the radar: the beast's neural sensory pathfinding adapts to system difficulty!"
    )
}

DIFFICULTY_INTEL = {
    "Simple": {
        "title": "TIER 1: RECONNAISSANCE FORM",
        "description": "Alien uses BFS (Breadth-First Search). It explores open corridors uniformly, causing delayed target pursuit.",
        "threat": "LOW"
    },
    "Medium": {
        "title": "TIER 2: STALKER MUTATION",
        "description": "Alien uses Depth-Bounded DFS. It stalks winding tunnels deeply before doubling back, creating erratic ambushes.",
        "threat": "MODERATE"
    },
    "Hard": {
        "title": "TIER 3: APEX PREDATOR",
        "description": "Alien uses Optimal A* Search with Euclidean Heuristics. Zero wasted movements. It constantly tracks your exact coordinates.",
        "threat": "LETHAL"
    }
}
GAME_TITLE_LINE_1 = "ALIEN COLONY"
GAME_TITLE_LINE_2 = "ESCAPE"
GAME_TAGLINE = "OUTSMART THE ALGORITHM.  SURVIVE THE STALKER."
BOOT_LOG = ["# WAKING EMERGENCY POWER GRID ...", "# QUARANTINE FIELD ........ FAILED", "# LIFE SIGNS DETECTED: 1", "# XENOMORPH SIGNATURE ..... ACTIVE", "# LOADING NEURAL PATHFINDING MODULES ...", "# BFS ......... ONLINE", "# DBDFS ....... ONLINE", "# A* .......... ONLINE", "# AERIS-IV DEEP EXTRACTION COLONY: SECTOR 7", "# GOOD LUCK, OPERATOR."]
