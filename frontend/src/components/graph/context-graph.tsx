"use client";
import { useEffect, useState, useCallback } from "react";
import {
  ReactFlow, Background, Controls, MiniMap,
  Node, Edge, useNodesState, useEdgesState, addEdge,
  Connection, BackgroundVariant,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useWebSocket } from "@/hooks/use-websocket";
import { useThemeStore } from "@/store/theme";

const NODE_COLORS: Record<string, string> = {
  ue:      "#6366f1",
  cell:    "#3b82f6",
  patient: "#10b981",
  service: "#f59e0b",
  agent:   "#8b5cf6",
  nurse:   "#14b8a6",
  api:     "#f97316",
  payment: "#06b6d4",
  user:    "#8b5cf6",
  rec:     "#ec4899",
  batch:   "#64748b",
  pt:      "#10b981",
};

function buildDemoNodes(domain: string): { nodes: Node[]; edges: Edge[] } {
  if (domain === "5g") {
    return {
      nodes: [
        { id: "cell-001", type: "default", position: { x: 300, y: 100 }, data: { label: "cell-001\nn78 band" } },
        { id: "cell-002", type: "default", position: { x: 500, y: 100 }, data: { label: "cell-002\nn41 band" } },
        { id: "cell-003", type: "default", position: { x: 400, y: 250 }, data: { label: "cell-003\nn28 band" } },
        { id: "ue-001",   type: "default", position: { x: 200, y: 200 }, data: { label: "UE-001\nvehicular" } },
        { id: "ue-002",   type: "default", position: { x: 350, y: 350 }, data: { label: "UE-002\nindoor" } },
        { id: "ue-003",   type: "default", position: { x: 550, y: 250 }, data: { label: "UE-003\noutdoor" } },
      ],
      edges: [
        { id: "e1", source: "ue-001",  target: "cell-001", label: "attached" },
        { id: "e2", source: "ue-002",  target: "cell-003", label: "attached" },
        { id: "e3", source: "ue-003",  target: "cell-002", label: "attached" },
        { id: "e4", source: "cell-001",target: "cell-002", label: "neighbor", type: "step" },
        { id: "e5", source: "cell-002",target: "cell-003", label: "neighbor", type: "step" },
      ],
    };
  }

  if (domain === "cloud") {
    return {
      nodes: [
        { id: "api-gw",  type: "default", position: { x: 300, y:  50 }, data: { label: "api-gateway\n3 replicas" } },
        { id: "payment", type: "default", position: { x: 150, y: 180 }, data: { label: "payment-svc\n2 replicas" } },
        { id: "user",    type: "default", position: { x: 300, y: 180 }, data: { label: "user-svc\n3 replicas" } },
        { id: "rec",     type: "default", position: { x: 450, y: 180 }, data: { label: "recommendation\n5 replicas" } },
        { id: "batch",   type: "default", position: { x: 300, y: 320 }, data: { label: "analytics-batch\n8 replicas" } },
      ],
      edges: [
        { id: "e1", source: "api-gw", target: "payment", label: "depends_on" },
        { id: "e2", source: "api-gw", target: "user",    label: "depends_on" },
        { id: "e3", source: "api-gw", target: "rec",     label: "depends_on" },
        { id: "e4", source: "user",   target: "batch",   label: "feeds" },
      ],
    };
  }

  // ICU
  return {
    nodes: [
      { id: "pt-001",  type: "default", position: { x: 200, y: 150 }, data: { label: "Patient 001\nage 62" } },
      { id: "pt-002",  type: "default", position: { x: 400, y: 150 }, data: { label: "Patient 002\nage 74" } },
      { id: "pt-003",  type: "default", position: { x: 300, y: 300 }, data: { label: "Patient 003\nage 58" } },
      { id: "nurse-a", type: "default", position: { x: 100, y: 300 }, data: { label: "Nurse A\nstation 1" } },
      { id: "nurse-b", type: "default", position: { x: 500, y: 300 }, data: { label: "Nurse B\nstation 2" } },
    ],
    edges: [
      { id: "e1", source: "nurse-a", target: "pt-001", label: "monitors" },
      { id: "e2", source: "nurse-a", target: "pt-003", label: "monitors" },
      { id: "e3", source: "nurse-b", target: "pt-002", label: "monitors" },
      { id: "e4", source: "nurse-b", target: "pt-003", label: "monitors" },
    ],
  };
}

function nodeStyle(id: string, dark: boolean) {
  const color = NODE_COLORS[id.split("-")[0]] ?? "#374151";
  return {
    background: dark ? color + "33" : color + "22",
    color: dark ? "#f1f5f9" : "#1e293b",
    border: `1px solid ${color}66`,
    borderRadius: "8px",
    fontSize: 11,
    padding: "6px 10px",
    minWidth: 100,
  };
}

export function ContextGraph({ domain }: { domain: string }) {
  const dark = useThemeStore((s) => s.dark);

  const { nodes: demoNodes, edges: demoEdges } = buildDemoNodes(domain);

  const styledNodes = demoNodes.map((n) => ({
    ...n,
    style: nodeStyle(n.id, dark),
  }));

  const [nodes, setNodes, onNodesChange] = useNodesState(styledNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(demoEdges);

  useEffect(() => {
    const { nodes: newNodes, edges: newEdges } = buildDemoNodes(domain);
    setNodes(newNodes.map((n) => ({ ...n, style: nodeStyle(n.id, dark) })));
    setEdges(newEdges);
  }, [domain, dark, setNodes, setEdges]);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  useWebSocket(domain, {
    onMessage: (msg) => {
      if (msg.type === "graph.update" && msg.data) {
        // live graph mutations from the backend
      }
    },
  });

  const bgColor  = dark ? "#0a1628" : "#f8fafc";
  const dotColor = dark ? "#1e3a5f" : "#cbd5e1";
  const ctrlBg   = dark ? "#0f1f35" : "#ffffff";
  const ctrlBdr  = dark ? "#1e3a5f" : "#e2e8f0";

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      fitView
      style={{ background: bgColor }}
      proOptions={{ hideAttribution: true }}
    >
      <Background variant={BackgroundVariant.Dots} gap={20} size={1} color={dotColor} />
      <Controls style={{ background: ctrlBg, border: `1px solid ${ctrlBdr}` }} />
      <MiniMap
        style={{ background: ctrlBg, border: `1px solid ${ctrlBdr}` }}
        nodeColor={(n) => NODE_COLORS[(n.id ?? "").split("-")[0]] ?? "#374151"}
      />
    </ReactFlow>
  );
}
