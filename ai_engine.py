"""
AI Pathfinding Engines based on Academic Syllabus (Unit 1 & Unit 2).
Implements BFS (Simple), DBDFS (Medium), and Optimal A* (Hard).
All functions accept the same 6 positional arguments so they are interchangeable.
"""
import math
import heapq
from collections import deque


def get_valid_neighbors(node, grid, rows, cols):
    r, c = node
    neighbors = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 0:
            neighbors.append((nr, nc))
    return neighbors


def euclidean_distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def reconstruct_path(came_from, start, target):
    """Returns the list of steps from start (excluded) to target (included)."""
    if target not in came_from:
        return []
    curr = target
    path = []
    while curr is not None and curr != start:
        path.append(curr)
        curr = came_from[curr]
    path.reverse()
    return path


# --- 1: SIMPLE DIFFICULTY - BREADTH FIRST SEARCH (BFS) ---
def search_bfs(start, goal, grid, rows, cols, prev_pos=None):
    if start == goal:
        return []
    queue = deque([start])
    came_from = {start: None}

    while queue:
        current = queue.popleft()
        if current == goal:
            break
        for nxt in get_valid_neighbors(current, grid, rows, cols):
            if nxt not in came_from:
                came_from[nxt] = current
                queue.append(nxt)

    return reconstruct_path(came_from, start, goal)


# --- 2: MEDIUM DIFFICULTY - DEPTH BOUNDED DFS WITH MOMENTUM ---
def _dbdfs_raw(start, goal, grid, rows, cols, prev_pos=None, max_depth=75):
    if start == goal:
        return []
    stack = [(start, 0)]
    came_from = {start: None}
    visited = {start: 0}

    while stack:
        current, depth = stack.pop()
        if current == goal:
            break

        if depth < max_depth:
            nbrs = get_valid_neighbors(current, grid, rows, cols)

            def sort_weight(n):
                dist = euclidean_distance(n, goal)
                # Momentum: avoid stepping straight back where we just came from
                if current == start and prev_pos is not None and n == prev_pos and len(nbrs) > 1:
                    return dist + 100.0
                return dist

            # DFS pops last-pushed first, so push the *closest* neighbour last
            nbrs.sort(key=sort_weight, reverse=True)

            for nxt in nbrs:
                if nxt not in visited or visited[nxt] > depth + 1:
                    visited[nxt] = depth + 1
                    came_from[nxt] = current
                    stack.append((nxt, depth + 1))

    if goal in came_from:
        return reconstruct_path(came_from, start, goal)

    # Goal not reachable inside the depth bound: head to the closest explored cell
    nodes = [n for n in came_from if n != start]
    if nodes:
        best = min(nodes, key=lambda n: euclidean_distance(n, goal))
        return reconstruct_path(came_from, start, best)
    return []


_trail = deque(maxlen=60)


def _distances_from(goal, grid, rows, cols):
    dist = {goal: 0}
    queue = deque([goal])
    while queue:
        cur = queue.popleft()
        for nxt in get_valid_neighbors(cur, grid, rows, cols):
            if nxt not in dist:
                dist[nxt] = dist[cur] + 1
                queue.append(nxt)
    return dist


def search_dbdfs(start, goal, grid, rows, cols, prev_pos=None, max_depth=75):
    # Depth-bounded DFS with momentum (erratic, winding pursuit).
    # Anti-loop rule: if the DFS wants to step back onto a recently visited tile (a loop),
    # the hunter takes one step along the shortest route instead, so it always closes in.
    if prev_pos is None:
        _trail.clear()
    path = _dbdfs_raw(start, goal, grid, rows, cols, prev_pos, max_depth)
    if path and (path[0] == prev_pos or path[0] in _trail):
        dist = _distances_from(goal, grid, rows, cols)
        if start in dist:
            closer = [n for n in get_valid_neighbors(start, grid, rows, cols)
                      if dist.get(n, 10 ** 9) < dist[start]]
            if closer:
                cur = min(closer, key=lambda n: dist[n])
                path = [cur]
                while cur != goal:
                    nxts = [n for n in get_valid_neighbors(cur, grid, rows, cols)
                            if dist.get(n, 10 ** 9) < dist[cur]]
                    if not nxts:
                        break
                    cur = nxts[0]
                    path.append(cur)
    _trail.append(start)
    return path


# --- 3: HARD DIFFICULTY - OPTIMAL A* SEARCH ---
def search_astar(start, goal, grid, rows, cols, prev_pos=None):
    if start == goal:
        return []
    open_set = [(euclidean_distance(start, goal), 0, start)]
    came_from = {start: None}
    g_score = {start: 0}
    closed = set()

    while open_set:
        _, g, current = heapq.heappop(open_set)
        if current in closed:
            continue
        if current == goal:
            break
        closed.add(current)

        for nxt in get_valid_neighbors(current, grid, rows, cols):
            tentative_g = g + 1
            if nxt not in g_score or tentative_g < g_score[nxt]:
                g_score[nxt] = tentative_g
                came_from[nxt] = current
                f_score = tentative_g + euclidean_distance(nxt, goal)
                heapq.heappush(open_set, (f_score, tentative_g, nxt))

    return reconstruct_path(came_from, start, goal)