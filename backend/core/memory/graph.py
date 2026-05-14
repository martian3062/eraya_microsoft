"""
ErayaGraph — shared context graph for the agent swarm.

Architecture:
  NetworkX       — in-process graph (fast reads, all agents)
  Redis          — pub/sub for graph update events
  Neo4j          — optional production persistence

Nodes:    entities (cells, patients, services, agents)
Edges:    relationships (depends_on, monitors, affects, reports_to)
Props:    time-versioned state (each update tagged with timestamp)

All agents read/write through this single typed schema.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Any

import networkx as nx

logger = logging.getLogger("eraya.memory.graph")


@dataclass
class GraphNode:
    node_id: str
    node_type: str          # "cell", "patient", "service", "agent", "domain"
    domain: str
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def update(self, **props: Any) -> None:
        self.properties.update(props)
        self.updated_at = time.time()


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    edge_type: str          # "depends_on", "monitors", "affects", "reports_to"
    weight: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class ErayaGraph:
    """
    Thread-safe in-process context graph with optional Redis sync.
    Each agent instance holds a reference to the same singleton per domain.
    """

    _instances: dict[str, ErayaGraph] = {}
    _lock = threading.Lock()

    @classmethod
    def for_domain(cls, domain: str) -> ErayaGraph:
        with cls._lock:
            if domain not in cls._instances:
                cls._instances[domain] = cls(domain)
            return cls._instances[domain]

    def __init__(self, domain: str):
        self.domain = domain
        self._G = nx.DiGraph()
        self._lock = threading.RLock()
        self._redis = None
        self._history: list[dict[str, Any]] = []  # audit trail of all mutations
        self._try_connect_redis()

    # ─── Node operations ──────────────────────────────────────────────────────

    def add_node(self, node: GraphNode) -> None:
        with self._lock:
            self._G.add_node(node.node_id, **asdict(node))
            self._record("add_node", node.node_id, asdict(node))
        self._sync_redis("node.add", asdict(node))

    def update_node(self, node_id: str, **props: Any) -> bool:
        with self._lock:
            if node_id not in self._G:
                return False
            data = self._G.nodes[node_id]
            if "properties" not in data:
                data["properties"] = {}
            data["properties"].update(props)
            data["updated_at"] = time.time()
            self._record("update_node", node_id, props)
        self._sync_redis("node.update", {"node_id": node_id, "props": props})
        return True

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        with self._lock:
            if node_id not in self._G:
                return None
            return dict(self._G.nodes[node_id])

    def remove_node(self, node_id: str) -> None:
        with self._lock:
            if node_id in self._G:
                self._G.remove_node(node_id)
                self._record("remove_node", node_id, {})

    # ─── Edge operations ──────────────────────────────────────────────────────

    def add_edge(self, edge: GraphEdge) -> None:
        with self._lock:
            self._G.add_edge(
                edge.source_id, edge.target_id,
                edge_type=edge.edge_type,
                weight=edge.weight,
                **edge.properties,
            )
            self._record("add_edge", f"{edge.source_id}→{edge.target_id}", asdict(edge))

    def get_neighbors(self, node_id: str, edge_type: str | None = None) -> list[str]:
        with self._lock:
            if node_id not in self._G:
                return []
            neighbors = list(self._G.successors(node_id))
            if edge_type:
                neighbors = [
                    n for n in neighbors
                    if self._G[node_id][n].get("edge_type") == edge_type
                ]
            return neighbors

    # ─── Queries ──────────────────────────────────────────────────────────────

    def find_nodes_by_type(self, node_type: str) -> list[dict[str, Any]]:
        with self._lock:
            return [
                dict(data)
                for _, data in self._G.nodes(data=True)
                if data.get("node_type") == node_type
            ]

    def find_nodes_by_property(self, key: str, value: Any) -> list[dict[str, Any]]:
        with self._lock:
            return [
                dict(data)
                for _, data in self._G.nodes(data=True)
                if data.get("properties", {}).get(key) == value
            ]

    def subgraph_around(self, node_id: str, depth: int = 2) -> nx.DiGraph:
        with self._lock:
            if node_id not in self._G:
                return nx.DiGraph()
            nodes = nx.ego_graph(self._G, node_id, radius=depth)
            return nodes

    def causal_path(self, source_id: str, target_id: str) -> list[str]:
        """Returns the causal path (if any) from source to target node."""
        with self._lock:
            try:
                return nx.shortest_path(self._G, source_id, target_id)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                return []

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "domain": self.domain,
                "nodes": [
                    {"id": nid, **dict(data)}
                    for nid, data in self._G.nodes(data=True)
                ],
                "edges": [
                    {"source": u, "target": v, **dict(data)}
                    for u, v, data in self._G.edges(data=True)
                ],
            }

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "nodes": self._G.number_of_nodes(),
                "edges": self._G.number_of_edges(),
                "mutations": len(self._history),
            }

    # ─── Redis sync ───────────────────────────────────────────────────────────

    def _try_connect_redis(self) -> None:
        try:
            import redis as redis_lib
            from django.conf import settings
            url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
            self._redis = redis_lib.from_url(url, decode_responses=True)
            self._redis.ping()
        except Exception:
            self._redis = None

    def _sync_redis(self, event: str, payload: dict[str, Any]) -> None:
        if self._redis is None:
            return
        try:
            channel = f"eraya:graph:{self.domain}"
            self._redis.publish(channel, json.dumps({"event": event, "payload": payload}))
        except Exception:
            pass

    def _record(self, op: str, target: str, payload: dict[str, Any]) -> None:
        self._history.append({
            "op": op,
            "target": target,
            "payload": payload,
            "ts": time.time(),
        })
        if len(self._history) > 50_000:
            self._history = self._history[-25_000:]
