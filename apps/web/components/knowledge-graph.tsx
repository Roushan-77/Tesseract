"use client";

import { useEffect, useMemo, useState, useRef, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { EmptyState } from "@/components/ui";
import {
  FolderKanban,
  User,
  Users,
  Phone,
  Car,
  MapPin,
  Building2,
  FileText,
  Calendar,
  Activity,
  CreditCard,
  Shield,
  Search,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Maximize2,
  X,
  ArrowUpRight,
  Eye,
  EyeOff,
  Sparkles,
  Clock,
  Code,
  Tag,
  Network,
  GitFork,
  Layers,
  CircleDot,
  Compass,
  Flag,
} from "lucide-react";

type GraphNode = { id: string; type: string; label: string; properties: Record<string, unknown> };
type GraphEdge = {
  id: string;
  source: string;
  target: string;
  type: string;
  confidence: number;
  evidenceIds: string[];
  sourceText: string[];
  sourceRow?: number | null;
  sourceFields?: string[];
};
type Graph = { nodes: GraphNode[]; edges: GraphEdge[] };
type Finding = { id?: string; title: string; explanation: string; metric: number; confidence: number; evidenceIds: string[] };

type LayoutMode = "RADIAL" | "HIERARCHICAL" | "FORCE" | "CIRCULAR" | "LAYERED";

const PRIMARY_TYPES = new Set(["PERSON", "ORGANIZATION", "PHONE", "VEHICLE", "LOCATION"]);

/**
 * Entity styling mapped accurately to professional intelligence board standards:
 * - Person: Slate Blue Circle (●)
 * - Organization: Muted Purple Rounded Square (■)
 * - Location: Teal Green Diamond (◆)
 * - Vehicle: Warm Ochre Rounded Capsule (⬭)
 * - Phone / Transaction: Copper Hexagon (⬡)
 * - Account: Steel Blue Rounded Square (■)
 * - Event / Incident: Terracotta Rust 5-point Star (★)
 * - Evidence: Slate Grey Square (■)
 * - Case: Concentric Ring Hub (⊚)
 */
const ENTITY_CONFIGS: Record<
  string,
  {
    shape: "circle" | "square" | "diamond" | "capsule" | "hexagon" | "star" | "hub";
    label: string;
    fill: string;
    stroke: string;
    text: string;
    icon: typeof User;
  }
> = {
  PERSON: {
    shape: "circle",
    label: "Person",
    fill: "#4f7296",
    stroke: "#385675",
    text: "#ffffff",
    icon: User,
  },
  ORGANIZATION: {
    shape: "square",
    label: "Organization",
    fill: "#7c628a",
    stroke: "#61496e",
    text: "#ffffff",
    icon: Building2,
  },
  LOCATION: {
    shape: "diamond",
    label: "Location",
    fill: "#4a7c73",
    stroke: "#355e57",
    text: "#ffffff",
    icon: MapPin,
  },
  VEHICLE: {
    shape: "capsule",
    label: "Vehicle",
    fill: "#9e7950",
    stroke: "#7c5c37",
    text: "#ffffff",
    icon: Car,
  },
  PHONE: {
    shape: "hexagon",
    label: "Phone",
    fill: "#9c6f50",
    stroke: "#7b543c",
    text: "#ffffff",
    icon: Phone,
  },
  TRANSACTION: {
    shape: "hexagon",
    label: "Transaction",
    fill: "#9c6f50",
    stroke: "#7b543c",
    text: "#ffffff",
    icon: CreditCard,
  },
  ACCOUNT: {
    shape: "square",
    label: "Account",
    fill: "#577085",
    stroke: "#3f5464",
    text: "#ffffff",
    icon: CreditCard,
  },
  EVENT: {
    shape: "star",
    label: "Incident / Event",
    fill: "#b04e46",
    stroke: "#8c3831",
    text: "#ffffff",
    icon: Activity,
  },
  EVIDENCE: {
    shape: "square",
    label: "Evidence Document",
    fill: "#687685",
    stroke: "#4f5c6a",
    text: "#ffffff",
    icon: FileText,
  },
  CASE: {
    shape: "hub",
    label: "Investigation Hub",
    fill: "#2563eb",
    stroke: "#1d4ed8",
    text: "#ffffff",
    icon: FolderKanban,
  },
  DATE: {
    shape: "circle",
    label: "Date / Timestamp",
    fill: "#64748b",
    stroke: "#475569",
    text: "#ffffff",
    icon: Calendar,
  },
};

const DEFAULT_CONFIG = {
  shape: "circle" as const,
  label: "Entity",
  fill: "#5a6e85",
  stroke: "#415367",
  text: "#ffffff",
  icon: Shield,
};

function isInvestigativeEdge(type: string): boolean {
  const upper = (type || "").toUpperCase();
  return (
    upper.includes("MET") ||
    upper.includes("CONTACT") ||
    upper.includes("CALL") ||
    upper.includes("VISIT") ||
    upper.includes("OWN") ||
    upper.includes("USE") ||
    upper.includes("OPERAT") ||
    upper.includes("WORK") ||
    upper.includes("CONNECT") ||
    upper.includes("TRANSFER") ||
    upper.includes("SUSPECT") ||
    upper.includes("SUPERVIS") ||
    upper.includes("PARTICIPAT") ||
    upper.includes("OCCUR") ||
    upper.includes("ASSOCIATE")
  );
}

function formatNodeLabel(node: GraphNode): string {
  if (node.type === "EVIDENCE") {
    const parts = node.label.split("-");
    if (parts.length >= 3) {
      return `${parts[0]}-${parts[1]}-${parts[2].slice(0, 4)}…`;
    }
  }
  if (node.label.length > 24) {
    return `${node.label.slice(0, 22)}…`;
  }
  return node.label;
}

// ==========================================
// 1. RADIAL NETWORK LAYOUT (DEFAULT)
// Places Central Hub at center, Tier 1 directly connected entities in inner ring,
// and Tier 2 secondary entities in an outer ring around their parents.
// ==========================================
function layoutRadial(
  nodes: GraphNode[],
  edges: GraphEdge[],
  width: number,
  height: number
): Map<string, { x: number; y: number; radius: number }> {
  if (nodes.length === 0) return new Map();
  const cx = width / 2;
  const cy = height / 2;

  // Degrees and Adjacency
  const degreeMap = new Map<string, number>();
  const adj = new Map<string, Set<string>>();
  nodes.forEach((n) => {
    degreeMap.set(n.id, 0);
    adj.set(n.id, new Set());
  });
  edges.forEach((e) => {
    degreeMap.set(e.source, (degreeMap.get(e.source) || 0) + 1);
    degreeMap.set(e.target, (degreeMap.get(e.target) || 0) + 1);
    adj.get(e.source)?.add(e.target);
    adj.get(e.target)?.add(e.source);
  });

  // Pick Root / Central Entity:
  // 1. Case node if present, 2. Event/Incident, 3. Highest degree node
  let root = nodes.find((n) => n.type === "CASE");
  if (!root) {
    root = nodes.find((n) => n.type === "EVENT" && (degreeMap.get(n.id) || 0) >= 2);
  }
  if (!root) {
    let maxDeg = -1;
    nodes.forEach((n) => {
      const d = degreeMap.get(n.id) || 0;
      if (d > maxDeg) {
        maxDeg = d;
        root = n;
      }
    });
  }
  const rootId = root?.id || nodes[0].id;

  // BFS Levels from root
  const levelMap = new Map<string, number>();
  const parentMap = new Map<string, string>();
  const queue = [rootId];
  levelMap.set(rootId, 0);

  while (queue.length > 0) {
    const curr = queue.shift()!;
    const curLevel = levelMap.get(curr)!;
    adj.get(curr)?.forEach((nbr) => {
      if (!levelMap.has(nbr)) {
        levelMap.set(nbr, curLevel + 1);
        parentMap.set(nbr, curr);
        queue.push(nbr);
      }
    });
  }

  // Any unreached nodes go to outermost tier
  nodes.forEach((n) => {
    if (!levelMap.has(n.id)) {
      levelMap.set(n.id, 2);
    }
  });

  const level0 = nodes.filter((n) => levelMap.get(n.id) === 0);
  const level1 = nodes.filter((n) => levelMap.get(n.id) === 1);
  const level2 = nodes.filter((n) => (levelMap.get(n.id) || 0) >= 2);

  const positions = new Map<string, { x: number; y: number; radius: number }>();

  // Place Level 0 (Center)
  level0.forEach((n) => {
    positions.set(n.id, { x: cx, y: cy, radius: 24 });
  });

  // Place Level 1 (Inner Ring: R = 210)
  const r1 = 215;
  const angleByNode = new Map<string, number>();
  level1.forEach((n, idx) => {
    const angle = (2 * Math.PI * idx) / Math.max(1, level1.length) - Math.PI / 2;
    angleByNode.set(n.id, angle);
    const x = cx + Math.cos(angle) * r1;
    const y = cy + Math.sin(angle) * r1;
    positions.set(n.id, { x: Math.round(x), y: Math.round(y), radius: 20 });
  });

  // Group Level 2 nodes by their parent in Level 1
  const childrenByParent = new Map<string, GraphNode[]>();
  const unparented: GraphNode[] = [];
  level2.forEach((n) => {
    const p = parentMap.get(n.id);
    if (p && angleByNode.has(p)) {
      if (!childrenByParent.has(p)) childrenByParent.set(p, []);
      childrenByParent.get(p)!.push(n);
    } else {
      unparented.push(n);
    }
  });

  // Place Level 2 around parent sector (Outer Ring: R = 390)
  const r2 = 395;
  childrenByParent.forEach((children, parentId) => {
    const pAngle = angleByNode.get(parentId) || 0;
    const count = children.length;
    const spread = Math.min(0.75, 0.28 * count);
    children.forEach((child, cIdx) => {
      const offset = count === 1 ? 0 : (cIdx - (count - 1) / 2) * (spread / count);
      const angle = pAngle + offset;
      const x = cx + Math.cos(angle) * r2;
      const y = cy + Math.sin(angle) * r2;
      positions.set(child.id, { x: Math.round(x), y: Math.round(y), radius: 18 });
    });
  });

  // Place unparented outer nodes
  unparented.forEach((child, uIdx) => {
    const angle = (2 * Math.PI * uIdx) / Math.max(1, unparented.length);
    const r3 = 450;
    const x = cx + Math.cos(angle) * r3;
    const y = cy + Math.sin(angle) * r3;
    positions.set(child.id, { x: Math.round(x), y: Math.round(y), radius: 17 });
  });

  // Relaxation step for collision avoidance
  const posArray = Array.from(positions.entries()).map(([id, pos]) => ({ id, ...pos, vx: 0, vy: 0 }));
  for (let iter = 0; iter < 45; iter++) {
    for (let i = 0; i < posArray.length; i++) {
      for (let j = i + 1; j < posArray.length; j++) {
        const u = posArray[i];
        const v = posArray[j];
        const dx = u.x - v.x;
        const dy = u.y - v.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const minDist = 100; // minimum clearance
        if (dist < minDist) {
          const push = ((minDist - dist) / dist) * 0.35;
          if (u.id !== rootId) {
            u.x += dx * push;
            u.y += dy * push;
          }
          if (v.id !== rootId) {
            v.x -= dx * push;
            v.y -= dy * push;
          }
        }
      }
    }
  }

  posArray.forEach((p) => {
    positions.set(p.id, { x: Math.round(p.x), y: Math.round(p.y), radius: p.radius });
  });

  return positions;
}

// ==========================================
// 2. HIERARCHICAL LAYOUT
// Top-to-bottom organized tree by investigative role
// ==========================================
function layoutHierarchical(
  nodes: GraphNode[],
  width: number,
  height: number
): Map<string, { x: number; y: number; radius: number }> {
  const positions = new Map<string, { x: number; y: number; radius: number }>();
  const layers: GraphNode[][] = [[], [], [], [], []];

  nodes.forEach((n) => {
    if (n.type === "CASE" || n.type === "EVIDENCE") layers[0].push(n);
    else if (n.type === "EVENT" || n.type === "ORGANIZATION") layers[1].push(n);
    else if (n.type === "PERSON") layers[2].push(n);
    else if (n.type === "PHONE" || n.type === "ACCOUNT" || n.type === "TRANSACTION") layers[3].push(n);
    else layers[4].push(n); // Vehicles, Locations, Dates
  });

  const activeLayers = layers.filter((l) => l.length > 0);
  const rowHeight = (height - 180) / Math.max(1, activeLayers.length - 1 || 1);

  let activeRow = 0;
  layers.forEach((layerNodes) => {
    if (layerNodes.length === 0) return;
    const y = 90 + activeRow * rowHeight;
    const count = layerNodes.length;
    const spacing = Math.min(180, (width - 240) / Math.max(1, count));
    const startX = width / 2 - ((count - 1) * spacing) / 2;

    layerNodes.forEach((node, idx) => {
      const x = startX + idx * spacing;
      positions.set(node.id, { x: Math.round(x), y: Math.round(y), radius: 19 });
    });
    activeRow++;
  });

  return positions;
}

// ==========================================
// 3. FORCE-DIRECTED PHYSICS LAYOUT
// Spacious organic cluster physics
// ==========================================
function layoutForce(
  nodes: GraphNode[],
  edges: GraphEdge[],
  width: number,
  height: number
): Map<string, { x: number; y: number; radius: number }> {
  if (nodes.length === 0) return new Map();
  const cx = width / 2;
  const cy = height / 2;

  const simNodes = nodes.map((node, i) => {
    const angle = i * 2.39996;
    const dist = 80 + Math.sqrt(i) * 55;
    return {
      id: node.id,
      x: cx + Math.cos(angle) * dist,
      y: cy + Math.sin(angle) * dist,
      vx: 0,
      vy: 0,
      radius: node.type === "CASE" ? 24 : 19,
    };
  });

  const nodeMap = new Map(simNodes.map((n) => [n.id, n]));
  const k = Math.sqrt((width * height) / (simNodes.length + 1)) * 1.35;
  let temp = width / 8.0;

  for (let iter = 0; iter < 240; iter++) {
    // Repulsion
    for (let i = 0; i < simNodes.length; i++) {
      const u = simNodes[i];
      for (let j = i + 1; j < simNodes.length; j++) {
        const v = simNodes[j];
        const dx = u.x - v.x;
        const dy = u.y - v.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const minDist = 110;
        let f = dist < minDist ? (minDist * minDist * 2.2) / (dist * 0.4) : (k * k) / dist;
        const fx = (dx / dist) * f * 0.45;
        const fy = (dy / dist) * f * 0.45;
        u.vx += fx;
        u.vy += fy;
        v.vx -= fx;
        v.vy -= fy;
      }
    }

    // Springs
    for (const e of edges) {
      const u = nodeMap.get(e.source);
      const v = nodeMap.get(e.target);
      if (!u || !v) continue;
      const dx = v.x - u.x;
      const dy = v.y - u.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const delta = dist - 155;
      const attr = ((delta * delta) / (k * 1.2)) * (delta > 0 ? 1 : -0.35);
      u.vx += (dx / dist) * attr;
      u.vy += (dy / dist) * attr;
      v.vx -= (dx / dist) * attr;
      v.vy -= (dy / dist) * attr;
    }

    // Center Gravity & Integration
    for (const u of simNodes) {
      u.vx += (cx - u.x) * 0.012;
      u.vy += (cy - u.y) * 0.012;
      const speed = Math.sqrt(u.vx * u.vx + u.vy * u.vy) || 1;
      const d = Math.min(speed, temp);
      u.x += (u.vx / speed) * d;
      u.y += (u.vy / speed) * d;
      u.x = Math.max(65, Math.min(width - 65, u.x));
      u.y = Math.max(65, Math.min(height - 65, u.y));
      u.vx = 0;
      u.vy = 0;
    }
    temp *= 0.95;
  }

  const result = new Map<string, { x: number; y: number; radius: number }>();
  simNodes.forEach((n) => result.set(n.id, { x: Math.round(n.x), y: Math.round(n.y), radius: n.radius }));
  return result;
}

// ==========================================
// 4. CIRCULAR CONCENTRIC LAYOUT
// ==========================================
function layoutCircular(
  nodes: GraphNode[],
  width: number,
  height: number
): Map<string, { x: number; y: number; radius: number }> {
  const positions = new Map<string, { x: number; y: number; radius: number }>();
  const cx = width / 2;
  const cy = height / 2;

  if (nodes.length <= 14) {
    const r = Math.min(width, height) * 0.38;
    nodes.forEach((n, idx) => {
      const angle = (2 * Math.PI * idx) / nodes.length - Math.PI / 2;
      positions.set(n.id, {
        x: Math.round(cx + Math.cos(angle) * r),
        y: Math.round(cy + Math.sin(angle) * r),
        radius: 19,
      });
    });
  } else {
    const half = Math.ceil(nodes.length / 2);
    const inner = nodes.slice(0, half);
    const outer = nodes.slice(half);

    const r1 = 180;
    const r2 = 360;

    inner.forEach((n, idx) => {
      const angle = (2 * Math.PI * idx) / inner.length - Math.PI / 2;
      positions.set(n.id, {
        x: Math.round(cx + Math.cos(angle) * r1),
        y: Math.round(cy + Math.sin(angle) * r1),
        radius: 20,
      });
    });
    outer.forEach((n, idx) => {
      const angle = (2 * Math.PI * idx) / outer.length - Math.PI / 2;
      positions.set(n.id, {
        x: Math.round(cx + Math.cos(angle) * r2),
        y: Math.round(cy + Math.sin(angle) * r2),
        radius: 18,
      });
    });
  }

  return positions;
}

// ==========================================
// 5. LAYERED / FLOW LAYOUT (Horizontal)
// ==========================================
function layoutLayered(
  nodes: GraphNode[],
  width: number,
  height: number
): Map<string, { x: number; y: number; radius: number }> {
  const positions = new Map<string, { x: number; y: number; radius: number }>();
  const cols: GraphNode[][] = [[], [], [], [], []];

  nodes.forEach((n) => {
    if (n.type === "CASE" || n.type === "EVIDENCE") cols[0].push(n);
    else if (n.type === "ORGANIZATION" || n.type === "EVENT") cols[1].push(n);
    else if (n.type === "PERSON") cols[2].push(n);
    else if (n.type === "PHONE" || n.type === "ACCOUNT" || n.type === "TRANSACTION") cols[3].push(n);
    else cols[4].push(n); // Location, Vehicle, Date
  });

  const activeCols = cols.filter((c) => c.length > 0);
  const colWidth = (width - 240) / Math.max(1, activeCols.length - 1 || 1);

  let activeColIdx = 0;
  cols.forEach((colNodes) => {
    if (colNodes.length === 0) return;
    const x = 120 + activeColIdx * colWidth;
    const count = colNodes.length;
    const spacing = Math.min(130, (height - 160) / Math.max(1, count));
    const startY = height / 2 - ((count - 1) * spacing) / 2;

    colNodes.forEach((node, idx) => {
      const y = startY + idx * spacing;
      positions.set(node.id, { x: Math.round(x), y: Math.round(y), radius: 19 });
    });
    activeColIdx++;
  });

  return positions;
}

export function KnowledgeGraph({
  token,
  caseNumber,
  onFlag,
  flaggedIds = new Set(),
}: {
  token: string;
  caseNumber: string;
  onFlag?: (target: { resourceType: string; resourceId: string; resourceLabel: string }) => void;
  flaggedIds?: Set<string>;
}) {
  const [graph, setGraph] = useState<Graph | null>(null);
  const [intel, setIntel] = useState<{ findings: Finding[] } | null>(null);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<GraphEdge | null>(null);
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [confidence, setConfidence] = useState(0);

  // Layout View Mode (Default: Radial Network)
  const [layoutMode, setLayoutMode] = useState<LayoutMode>("RADIAL");

  // Filter Mode: Primary Entities vs Full Technical Architecture
  const [showSupporting, setShowSupporting] = useState(false);
  // Edge Labels: Smart (Hover/Focus only) vs Always
  const [showAllLabels, setShowAllLabels] = useState(false);

  // Pan & Zoom state
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);

  // User manual node repositioning
  const [customPositions, setCustomPositions] = useState<
    Map<string, { x: number; y: number; radius: number }>
  >(new Map());
  const [draggedNode, setDraggedNode] = useState<{
    id: string;
    startX: number;
    startY: number;
    origX: number;
    origY: number;
    origRadius?: number;
  } | null>(null);

  const svgWidth = 1500;
  const svgHeight = 900;

  useEffect(() => {
    api<Graph>(`/cases/${caseNumber}/graph`, token)
      .then(setGraph)
      .catch(() => setGraph({ nodes: [], edges: [] }));

    api<{ findings: Finding[] }>(`/cases/${caseNumber}/intelligence`, token)
      .then(setIntel)
      .catch(() => setIntel(null));
  }, [token, caseNumber]);

  // Smooth mouse-wheel and trackpad pinch zoom centered on cursor
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const cursorX = e.clientX - rect.left;
      const cursorY = e.clientY - rect.top;

      const delta = -e.deltaY;
      const factor = delta > 0 ? 1.07 : 0.93;

      setZoom((prevZoom) => {
        const nextZoom = Math.max(0.3, Math.min(3.5, Number((prevZoom * factor).toFixed(3))));
        setPan((prevPan) => {
          const nextPanX = cursorX - ((cursorX - prevPan.x) / prevZoom) * nextZoom;
          const nextPanY = cursorY - ((cursorY - prevPan.y) / prevZoom) * nextZoom;
          return { x: Math.round(nextPanX), y: Math.round(nextPanY) };
        });
        return nextZoom;
      });
    };

    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  const allRawTypes = useMemo(() => Array.from(new Set((graph?.nodes ?? []).map((n) => n.type))), [graph]);

  const availablePrimaryTypes = useMemo(() => {
    return allRawTypes.filter((t) => PRIMARY_TYPES.has(t));
  }, [allRawTypes]);

  // Filter visible nodes
  const visibleNodes = useMemo(() => {
    if (!graph?.nodes) return [];

    return graph.nodes.filter((node) => {
      const isPrimary = PRIMARY_TYPES.has(node.type) || node.type === "CASE";

      if (!showSupporting && !isPrimary) {
        return false;
      }

      const matchType = typeFilter === "ALL" || node.type === typeFilter;
      const matchQuery =
        !query ||
        node.label.toLowerCase().includes(query.toLowerCase()) ||
        node.type.toLowerCase().includes(query.toLowerCase());

      return matchType && matchQuery;
    });
  }, [graph, showSupporting, typeFilter, query]);

  const visibleIds = useMemo(() => new Set(visibleNodes.map((node) => node.id)), [visibleNodes]);

  // Filter edges connecting visible nodes
  const edges = useMemo(() => {
    if (!graph?.edges) return [];

    const baseEdges = graph.edges.filter(
      (edge) =>
        edge.confidence >= confidence &&
        visibleIds.has(edge.source) &&
        visibleIds.has(edge.target)
    );

    if (!showSupporting) {
      return baseEdges.filter((e) => isInvestigativeEdge(e.type));
    }

    return baseEdges;
  }, [graph, confidence, visibleIds, showSupporting]);

  // Parallel edge tracking for arcs
  const edgePairIndex = useMemo(() => {
    const counts = new Map<string, number>();
    const indices = new Map<string, { index: number; total: number }>();

    edges.forEach((e) => {
      const key = [e.source, e.target].sort().join("___");
      counts.set(key, (counts.get(key) || 0) + 1);
    });

    const currentTrack = new Map<string, number>();
    edges.forEach((e) => {
      const key = [e.source, e.target].sort().join("___");
      const idx = currentTrack.get(key) || 0;
      currentTrack.set(key, idx + 1);
      indices.set(e.id, { index: idx, total: counts.get(key) || 1 });
    });

    return indices;
  }, [edges]);

  // Compute Layout based on Active Mode
  const computedPositions = useMemo(() => {
    switch (layoutMode) {
      case "RADIAL":
        return layoutRadial(visibleNodes, edges, svgWidth, svgHeight);
      case "HIERARCHICAL":
        return layoutHierarchical(visibleNodes, svgWidth, svgHeight);
      case "FORCE":
        return layoutForce(visibleNodes, edges, svgWidth, svgHeight);
      case "CIRCULAR":
        return layoutCircular(visibleNodes, svgWidth, svgHeight);
      case "LAYERED":
        return layoutLayered(visibleNodes, svgWidth, svgHeight);
      default:
        return layoutRadial(visibleNodes, edges, svgWidth, svgHeight);
    }
  }, [visibleNodes, edges, layoutMode]);

  // Merge computed positions with manual drag overrides
  const positions = useMemo(() => {
    const merged = new Map<string, { x: number; y: number; radius: number }>();
    computedPositions.forEach((pos, id) => {
      merged.set(id, customPositions.get(id) || pos);
    });
    return merged;
  }, [computedPositions, customPositions]);

  // Neighbor Adjacency Map
  const connectedMap = useMemo(() => {
    const map = new Map<string, Set<string>>();
    edges.forEach((e) => {
      if (!map.has(e.source)) map.set(e.source, new Set());
      if (!map.has(e.target)) map.set(e.target, new Set());
      map.get(e.source)!.add(e.target);
      map.get(e.target)!.add(e.source);
    });
    return map;
  }, [edges]);

  const activeFocusId = selected?.id || hoveredNode?.id || null;

  // Fit Viewport
  const fitGraph = useCallback(() => {
    if (visibleNodes.length === 0 || !containerRef.current) return;

    let minX = Infinity,
      maxX = -Infinity,
      minY = Infinity,
      maxY = -Infinity;

    visibleNodes.forEach((node) => {
      const pos = positions.get(node.id);
      if (pos) {
        minX = Math.min(minX, pos.x - pos.radius - 60);
        maxX = Math.max(maxX, pos.x + pos.radius + 60);
        minY = Math.min(minY, pos.y - pos.radius - 40);
        maxY = Math.max(maxY, pos.y + pos.radius + 50);
      }
    });

    if (!isFinite(minX) || !isFinite(maxX)) return;

    const rect = containerRef.current.getBoundingClientRect();
    const graphW = Math.max(100, maxX - minX);
    const graphH = Math.max(100, maxY - minY);
    const padding = 50;

    const scaleX = (rect.width - padding * 2) / graphW;
    const scaleY = (rect.height - padding * 2) / graphH;
    const newScale = Math.max(0.35, Math.min(1.35, Math.min(scaleX, scaleY)));

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    const newPanX = rect.width / 2 - centerX * newScale;
    const newPanY = rect.height / 2 - centerY * newScale;

    setZoom(Number(newScale.toFixed(2)));
    setPan({ x: Math.round(newPanX), y: Math.round(newPanY) });
  }, [visibleNodes, positions]);

  // Initial Auto-fit & on layout change
  useEffect(() => {
    if (visibleNodes.length > 0) {
      const timer = setTimeout(fitGraph, 60);
      return () => clearTimeout(timer);
    }
  }, [visibleNodes.length, showSupporting, layoutMode]);

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setCustomPositions(new Map());
    setTimeout(fitGraph, 30);
  };

  // Node Drag handlers
  const handleNodeMouseDown = (e: React.MouseEvent, node: GraphNode) => {
    e.stopPropagation();
    const currentPos = positions.get(node.id);
    if (!currentPos) return;
    setDraggedNode({
      id: node.id,
      startX: e.clientX,
      startY: e.clientY,
      origX: currentPos.x,
      origY: currentPos.y,
    });
  };

  const handleNodeDoubleClick = (e: React.MouseEvent, node: GraphNode) => {
    e.stopPropagation();
    setSelected(node);

    const pos = positions.get(node.id);
    if (!pos || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const targetZoom = 1.35;
    const targetPanX = rect.width / 2 - pos.x * targetZoom;
    const targetPanY = rect.height / 2 - pos.y * targetZoom;

    setZoom(targetZoom);
    setPan({ x: Math.round(targetPanX), y: Math.round(targetPanY) });
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).tagName === "svg" || (e.target as HTMLElement).id === "graph-bg") {
      setIsPanning(true);
      dragStart.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (draggedNode) {
      const deltaX = (e.clientX - draggedNode.startX) / zoom;
      const deltaY = (e.clientY - draggedNode.startY) / zoom;
      setCustomPositions((prev) => {
        const next = new Map(prev);
        const existing = positions.get(draggedNode.id);
        if (existing) {
          next.set(draggedNode.id, {
            ...existing,
            x: Math.round(draggedNode.origX + deltaX),
            y: Math.round(draggedNode.origY + deltaY),
          });
        }
        return next;
      });
    } else if (isPanning) {
      setPan({ x: e.clientX - dragStart.current.x, y: e.clientY - dragStart.current.y });
    }
  };

  const handleMouseUp = () => {
    setIsPanning(false);
    setDraggedNode(null);
  };

  // Degree calculation across all graph edges
  const nodeDegreeMap = useMemo(() => {
    const map = new Map<string, number>();
    (graph?.edges ?? []).forEach((e) => {
      map.set(e.source, (map.get(e.source) || 0) + 1);
      map.set(e.target, (map.get(e.target) || 0) + 1);
    });
    return map;
  }, [graph]);

  // Center & focus node on graph
  const focusNode = useCallback((node: GraphNode) => {
    setSelected(node);
    const pos = positions.get(node.id);
    if (pos && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const targetZoom = 1.35;
      const targetPanX = rect.width / 2 - pos.x * targetZoom;
      const targetPanY = rect.height / 2 - pos.y * targetZoom;
      setZoom(targetZoom);
      setPan({ x: Math.round(targetPanX), y: Math.round(targetPanY) });
    }
  }, [positions]);

  // Node lookup map
  const nodeById = useMemo(() => {
    const map = new Map<string, GraphNode>();
    (graph?.nodes ?? []).forEach((n) => map.set(n.id, n));
    return map;
  }, [graph]);

  // Key network entities for default inspector view
  const keyEntities = useMemo(() => {
    if (!graph?.nodes) return { people: [], orgs: [], phones: [], others: [] };

    const validNodes = graph.nodes.filter((n) => n.type !== "CASE");
    const enriched = validNodes
      .map((n) => {
        const degree = nodeDegreeMap.get(n.id) || 0;
        const finding = intel?.findings.find(
          (f) =>
            f.title.toLowerCase().includes(n.label.toLowerCase()) ||
            f.explanation.toLowerCase().includes(n.label.toLowerCase())
        );
        return { node: n, degree, finding };
      })
      .filter((i) => i.degree > 0)
      .sort((a, b) => b.degree - a.degree);

    const people = enriched.filter((i) => i.node.type === "PERSON");
    const orgs = enriched.filter((i) => i.node.type === "ORGANIZATION");
    const phones = enriched.filter((i) => i.node.type === "PHONE" || i.node.type === "ACCOUNT");
    const others = enriched.filter(
      (i) => !["PERSON", "ORGANIZATION", "PHONE", "ACCOUNT"].includes(i.node.type)
    );

    return { people, orgs, phones, others };
  }, [graph, nodeDegreeMap, intel]);

  // Direct relationships of selected node
  const selectedEdges = useMemo(() => {
    if (!selected) return [];
    return (graph?.edges ?? []).filter((e) => e.source === selected.id || e.target === selected.id);
  }, [selected, graph]);

  // Categorized direct connections for selected node
  const categorizedConnections = useMemo(() => {
    if (!selected) {
      return { people: [], orgs: [], phones: [], vehicles: [], locations: [], events: [], others: [] };
    }

    const res = {
      people: [] as Array<{ edge: GraphEdge; otherNode: GraphNode; isOutbound: boolean }>,
      orgs: [] as Array<{ edge: GraphEdge; otherNode: GraphNode; isOutbound: boolean }>,
      phones: [] as Array<{ edge: GraphEdge; otherNode: GraphNode; isOutbound: boolean }>,
      vehicles: [] as Array<{ edge: GraphEdge; otherNode: GraphNode; isOutbound: boolean }>,
      locations: [] as Array<{ edge: GraphEdge; otherNode: GraphNode; isOutbound: boolean }>,
      events: [] as Array<{ edge: GraphEdge; otherNode: GraphNode; isOutbound: boolean }>,
      others: [] as Array<{ edge: GraphEdge; otherNode: GraphNode; isOutbound: boolean }>,
    };

    selectedEdges.forEach((edge) => {
      const otherId = edge.source === selected.id ? edge.target : edge.source;
      const otherNode = nodeById.get(otherId);
      if (!otherNode) return;
      const isOutbound = edge.source === selected.id;
      const item = { edge, otherNode, isOutbound };

      const type = otherNode.type.toUpperCase();
      if (type === "PERSON") res.people.push(item);
      else if (type === "ORGANIZATION") res.orgs.push(item);
      else if (type === "PHONE" || type === "ACCOUNT") res.phones.push(item);
      else if (type === "VEHICLE") res.vehicles.push(item);
      else if (type === "LOCATION") res.locations.push(item);
      else if (type === "EVENT" || type === "INCIDENT") res.events.push(item);
      else res.others.push(item);
    });

    return res;
  }, [selected, selectedEdges, nodeById]);

  // Selected node structural analysis
  const selectedDegree = selected ? (nodeDegreeMap.get(selected.id) || 0) : 0;
  const selectedFinding = useMemo(() => {
    if (!selected || !intel?.findings) return null;
    return intel.findings.find(
      (f) =>
        f.title.toLowerCase().includes(selected.label.toLowerCase()) ||
        f.explanation.toLowerCase().includes(selected.label.toLowerCase())
    );
  }, [selected, intel]);

  const selectedRole = useMemo(() => {
    if (!selected) return "";
    if (selectedFinding) return selectedFinding.title;
    if (selectedDegree >= 6) return "Central Network Hub";
    if (selectedDegree >= 4) return "Key Network Connector";
    if (selectedDegree >= 2) return "Connected Actor / Entity";
    return "Peripheral Link";
  }, [selected, selectedDegree, selectedFinding]);

  const selectedEvidenceIds = useMemo(() => {
    if (!selectedEdges.length) return [];
    const set = new Set<string>();
    selectedEdges.forEach((e) => {
      (e.evidenceIds || []).forEach((eid) => {
        if (eid) set.add(eid);
      });
    });
    return Array.from(set);
  }, [selectedEdges]);

  /**
   * Render distinct geometric node shapes
   */
  const renderShapeElement = (type: string, isFocus: boolean, isNeighbor: boolean) => {
    const config = ENTITY_CONFIGS[type] || DEFAULT_CONFIG;
    const strokeColor = isFocus ? "#0f172a" : isNeighbor ? "#0284c7" : config.stroke;
    const strokeW = isFocus ? 2.8 : isNeighbor ? 2.4 : 1.5;

    switch (config.shape) {
      case "hub":
        return (
          <g>
            <circle r="23" fill={config.fill} stroke={strokeColor} strokeWidth={strokeW} />
            <circle r="16" fill="none" stroke="#ffffff" strokeWidth="1.5" strokeOpacity="0.8" />
          </g>
        );
      case "circle":
        return (
          <circle
            r="19"
            fill={config.fill}
            stroke={strokeColor}
            strokeWidth={strokeW}
            className="transition-all duration-150"
          />
        );
      case "square":
        return (
          <rect
            x="-16"
            y="-16"
            width="32"
            height="32"
            rx="4"
            fill={config.fill}
            stroke={strokeColor}
            strokeWidth={strokeW}
            className="transition-all duration-150"
          />
        );
      case "diamond":
        return (
          <polygon
            points="0,-20 20,0 0,20 -20,0"
            fill={config.fill}
            stroke={strokeColor}
            strokeWidth={strokeW}
            className="transition-all duration-150"
          />
        );
      case "capsule":
        return (
          <rect
            x="-21"
            y="-13"
            width="42"
            height="26"
            rx="7"
            fill={config.fill}
            stroke={strokeColor}
            strokeWidth={strokeW}
            className="transition-all duration-150"
          />
        );
      case "hexagon":
        return (
          <polygon
            points="0,-18 16,-9 16,9 0,18 -16,9 -16,-9"
            fill={config.fill}
            stroke={strokeColor}
            strokeWidth={strokeW}
            className="transition-all duration-150"
          />
        );
      case "star":
        return (
          <polygon
            points="0,-22 5.8,-8 21,-6.8 9.5,3.6 13,18.8 0,11 -13,18.8 -9.5,3.6 -21,-6.8 -5.8,-8"
            fill={config.fill}
            stroke={strokeColor}
            strokeWidth={strokeW}
            className="transition-all duration-150"
          />
        );
      default:
        return (
          <circle
            r="18"
            fill={config.fill}
            stroke={strokeColor}
            strokeWidth={strokeW}
          />
        );
    }
  };

  return (
    <section className="mt-6 panel overflow-hidden border border-line bg-surface shadow-xs rounded-xl">
      {/* 1. Main Navigation, Layout Selector & Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-white p-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search actors, phones, vehicles, places..."
              className="border border-line pl-9 pr-3 py-1.5 text-sm rounded-lg bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent w-60 transition-all"
            />
          </div>

          {/* 🎯 Layout Selector Dropdown */}
          <div className="flex items-center gap-1.5 bg-slate-50 border border-line rounded-lg px-2.5 py-1">
            <Network className="w-4 h-4 text-accent" />
            <span className="text-xs font-semibold text-slate-600">Layout:</span>
            <select
              value={layoutMode}
              onChange={(e) => {
                setLayoutMode(e.target.value as LayoutMode);
                setCustomPositions(new Map());
              }}
              className="bg-transparent text-xs font-bold text-slate-900 focus:outline-none cursor-pointer pr-1"
            >
              <option value="RADIAL">Radial Network (Default)</option>
              <option value="HIERARCHICAL">Hierarchical Tree</option>
              <option value="FORCE">Force-Directed</option>
              <option value="CIRCULAR">Circular Ring</option>
              <option value="LAYERED">Layered / Flow</option>
            </select>
          </div>

          {/* Mode Toggle: Primary Investigative Focus vs Full Technical Graph */}
          <button
            onClick={() => {
              setShowSupporting(!showSupporting);
              setSelected(null);
            }}
            className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
              showSupporting
                ? "bg-sky-50 text-sky-900 border-sky-300 ring-1 ring-sky-300"
                : "bg-slate-100 text-slate-700 border-slate-300 hover:bg-slate-200"
            }`}
            title={
              showSupporting
                ? "Switch to primary investigative entities view"
                : "Include raw evidence documents, timestamps, and technical nodes"
            }
          >
            {showSupporting ? <Eye className="h-3.5 w-3.5 text-sky-600" /> : <EyeOff className="h-3.5 w-3.5 text-slate-500" />}
            <span>{showSupporting ? "Architecture: Full" : "Network: Primary"}</span>
          </button>

          {/* Entity Type Filter */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="border border-line px-3 py-1.5 text-sm rounded-lg bg-slate-50 focus:bg-white text-slate-700 font-medium"
          >
            <option value="ALL">
              {showSupporting
                ? `All Entity Types (${graph?.nodes.length || 0})`
                : `All Primary Types (${(graph?.nodes ?? []).filter((n) => PRIMARY_TYPES.has(n.type)).length})`}
            </option>
            {(showSupporting ? allRawTypes : availablePrimaryTypes).map((item) => (
              <option key={item} value={item}>
                {item} ({(graph?.nodes ?? []).filter((n) => n.type === item).length})
              </option>
            ))}
          </select>

          {/* Confidence Slider */}
          <label className="text-xs font-semibold uppercase text-slate-600 flex items-center gap-2 bg-slate-50 border border-line px-2.5 py-1.5 rounded-lg">
            <span>Conf. {Math.round(confidence * 100)}%</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={confidence}
              onChange={(e) => setConfidence(Number(e.target.value))}
              className="w-14 accent-accent cursor-pointer"
            />
          </label>

          {/* Edge Label Visibility Toggle */}
          <button
            onClick={() => setShowAllLabels(!showAllLabels)}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              showAllLabels
                ? "bg-violet-50 text-violet-800 border-violet-300"
                : "bg-slate-50 text-slate-600 border-line hover:bg-slate-100"
            }`}
            title="Toggle relationship labels always visible vs visible on hover/focus"
          >
            <Tag className="w-3.5 h-3.5" />
            <span>{showAllLabels ? "Labels: Always" : "Labels: Smart"}</span>
          </button>
        </div>

        {/* View Zoom & Fit Toolbar */}
        <div className="flex items-center gap-2">
          <div className="flex items-center border border-line rounded-lg bg-slate-50 p-0.5 shadow-2xs">
            <button
              onClick={() => setZoom((z) => Math.min(3.5, Number((z * 1.15).toFixed(2))))}
              title="Zoom In"
              className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-white rounded transition-colors"
            >
              <ZoomIn className="h-4 w-4" />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(0.3, Number((z / 1.15).toFixed(2))))}
              title="Zoom Out"
              className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-white rounded transition-colors"
            >
              <ZoomOut className="h-4 w-4" />
            </button>
            <button
              onClick={fitGraph}
              title="Fit Graph to View"
              className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-white rounded transition-colors"
            >
              <Maximize2 className="h-4 w-4" />
            </button>
            <button
              onClick={resetView}
              title="Reset Layout & View"
              className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-white rounded transition-colors"
            >
              <RotateCcw className="h-4 w-4" />
            </button>
          </div>

          <span className="text-xs font-mono text-slate-500 ml-2">
            {visibleNodes.length} nodes · {edges.length} edges
          </span>
        </div>
      </div>

      {/* 2. Shape-Based Visual Legend */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2 border-b border-line bg-slate-50/90 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-slate-500 uppercase tracking-wider text-[10px] mr-1">
            Network Entities:
          </span>
          <button
            onClick={() => setTypeFilter("ALL")}
            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border text-[11px] font-semibold transition-all ${
              typeFilter === "ALL"
                ? "bg-navy text-white border-navy shadow-xs"
                : "bg-white border-line text-slate-700 hover:border-slate-400"
            }`}
          >
            <span>All</span>
            <span className="opacity-70 text-[10px]">({visibleNodes.length})</span>
          </button>
          {(showSupporting ? allRawTypes : availablePrimaryTypes).map((t) => {
            const config = ENTITY_CONFIGS[t] || DEFAULT_CONFIG;
            const count = (graph?.nodes ?? []).filter((n) => n.type === t).length;
            const isCurrent = typeFilter === t;
            return (
              <button
                key={t}
                onClick={() => setTypeFilter(typeFilter === t ? "ALL" : t)}
                className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border text-[11px] font-medium transition-all ${
                  isCurrent
                    ? "ring-2 ring-accent border-transparent bg-white shadow-xs font-semibold text-slate-900"
                    : "bg-white border-line text-slate-700 hover:border-slate-400"
                }`}
              >
                <span
                  className="w-2.5 h-2.5 inline-block rounded-xs"
                  style={{ backgroundColor: config.fill }}
                />
                <span>{config.label}</span>
                <span className="text-slate-400 text-[10px]">({count})</span>
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-3 text-[11px] text-slate-500 font-mono">
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-0.5 bg-slate-600 inline-block rounded-full" /> Direct Connection
          </span>
          <span className="flex items-center gap-1 text-accent font-semibold">
            {layoutMode === "RADIAL"
              ? "Radial Network Mode"
              : layoutMode === "HIERARCHICAL"
              ? "Hierarchical Mode"
              : layoutMode === "FORCE"
              ? "Force Physics Mode"
              : layoutMode === "CIRCULAR"
              ? "Circular Mode"
              : "Layered Flow Mode"}
          </span>
        </div>
      </div>

      {/* 3. Main Graph Canvas + Entity Inspector Drawer */}
      {!visibleNodes.length ? (
        <div className="p-12">
          <EmptyState
            title="No network entities to display"
            body="No entities match your active filters. Click 'Architecture: Full' or reset filters to display the investigation network."
          />
        </div>
      ) : (
        <div className="grid lg:grid-cols-[1fr_360px] min-h-[640px]">
          {/* SVG Canvas with Clean Reference Light Theme */}
          <div
            ref={containerRef}
            className="relative overflow-hidden bg-[#eef3f8] select-none cursor-grab active:cursor-grabbing border-r border-line"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            {/* Top Canvas Header */}
            <div className="absolute top-3 left-1/2 -translate-x-1/2 text-xs text-slate-400 font-medium tracking-wide pointer-events-none flex items-center gap-1.5">
              <Compass className="w-3.5 h-3.5" />
              <span>Investigation Knowledge Graph</span>
            </div>

            {/* Floating Zoom & Preset Controls */}
            <div className="absolute top-3 right-3 flex items-center gap-1 bg-white/95 backdrop-blur border border-slate-300 rounded-lg p-1 shadow-sm z-10">
              <button
                onClick={() => setZoom((z) => Math.min(3.5, Number((z * 1.15).toFixed(2))))}
                title="Zoom In (+)"
                className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded transition-colors"
              >
                <ZoomIn className="h-4 w-4" />
              </button>
              <button
                onClick={() => setZoom((z) => Math.max(0.3, Number((z / 1.15).toFixed(2))))}
                title="Zoom Out (−)"
                className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded transition-colors"
              >
                <ZoomOut className="h-4 w-4" />
              </button>
              <div className="w-px h-4 bg-slate-200 mx-0.5" />
              <button
                onClick={fitGraph}
                title="Fit Network to Screen"
                className="px-2 py-1 text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-100 rounded flex items-center gap-1 transition-colors"
              >
                <Maximize2 className="h-3.5 w-3.5" />
                <span>Fit</span>
              </button>
              <button
                onClick={resetView}
                title="Reset View"
                className="px-2 py-1 text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-100 rounded flex items-center gap-1 transition-colors"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Reset</span>
              </button>
            </div>

            <svg
              viewBox={`0 0 ${svgWidth} ${svgHeight}`}
              className="w-full h-full min-h-[640px]"
              role="img"
              aria-label="Investigation Knowledge Graph"
            >
              {/* Defs for Arrowhead Markers */}
              <defs>
                <marker
                  id="arrow-subtle"
                  viewBox="0 0 10 10"
                  refX="23"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#475569" />
                </marker>
                <marker
                  id="arrow-focus"
                  viewBox="0 0 10 10"
                  refX="23"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#0f172a" />
                </marker>
              </defs>

              {/* Background Canvas click reset */}
              <rect
                id="graph-bg"
                width={svgWidth}
                height={svgHeight}
                fill="transparent"
                onClick={() => setSelected(null)}
              />

              {/* Main Scalable Pan/Zoom Group */}
              <g transform={`translate(${pan.x} ${pan.y}) scale(${zoom})`}>
                {/* 1. EDGES LAYER */}
                <g className="edges-layer">
                  {edges.map((edge) => {
                    const sourcePos = positions.get(edge.source);
                    const targetPos = positions.get(edge.target);
                    if (!sourcePos || !targetPos) return null;

                    const isConnectedToFocus =
                      activeFocusId === edge.source || activeFocusId === edge.target;
                    const isEdgeHovered = hoveredEdge?.id === edge.id;
                    const isDimmed = activeFocusId && !isConnectedToFocus;

                    // Compute curved routing to prevent overlapping lines
                    const dx = targetPos.x - sourcePos.x;
                    const dy = targetPos.y - sourcePos.y;
                    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                    const midX = (sourcePos.x + targetPos.x) / 2;
                    const midY = (sourcePos.y + targetPos.y) / 2;

                    const pairInfo = edgePairIndex.get(edge.id) || { index: 0, total: 1 };
                    let curveMagnitude = 0;
                    if (pairInfo.total > 1) {
                      curveMagnitude = (pairInfo.index - (pairInfo.total - 1) / 2) * 28;
                    }

                    const cx = midX - (dy / dist) * curveMagnitude;
                    const cy = midY + (dx / dist) * curveMagnitude;

                    const pathData =
                      curveMagnitude === 0
                        ? `M ${sourcePos.x} ${sourcePos.y} L ${targetPos.x} ${targetPos.y}`
                        : `M ${sourcePos.x} ${sourcePos.y} Q ${cx} ${cy} ${targetPos.x} ${targetPos.y}`;

                    const strokeColor = isConnectedToFocus || isEdgeHovered ? "#0f172a" : "#475569";
                    const strokeWidth = isConnectedToFocus || isEdgeHovered ? 2.2 : 1.3;
                    const strokeOpacity = isDimmed ? 0.08 : isConnectedToFocus || isEdgeHovered ? 1.0 : 0.72;

                    const shouldShowLabel = showAllLabels || isConnectedToFocus || isEdgeHovered;

                    return (
                      <g key={edge.id} className="transition-opacity duration-150">
                        {/* Thin clean directional line */}
                        <path
                          d={pathData}
                          fill="none"
                          stroke={strokeColor}
                          strokeWidth={strokeWidth}
                          strokeOpacity={strokeOpacity}
                          markerEnd={`url(#${isConnectedToFocus || isEdgeHovered ? "arrow-focus" : "arrow-subtle"})`}
                          className="cursor-pointer"
                          onMouseEnter={() => setHoveredEdge(edge)}
                          onMouseLeave={() => setHoveredEdge(null)}
                        />

                        {/* Interactive Relationship Label Pill */}
                        {shouldShowLabel && !isDimmed && (
                          <g transform={`translate(${cx}, ${cy})`} className="pointer-events-none">
                            <rect
                              x={-((edge.type.length * 5.2 + 12) / 2)}
                              y="-9"
                              width={edge.type.length * 5.2 + 12}
                              height="18"
                              rx="4"
                              fill="#ffffff"
                              stroke={strokeColor}
                              strokeWidth={isConnectedToFocus || isEdgeHovered ? "1.4" : "0.9"}
                              fillOpacity="0.96"
                              className="shadow-xs"
                            />
                            <text
                              x="0"
                              y="3.2"
                              fill="#0f172a"
                              fontSize="9"
                              fontWeight="600"
                              textAnchor="middle"
                              letterSpacing="0.02em"
                            >
                              {edge.type.replaceAll("_", " ")}
                            </text>
                          </g>
                        )}
                      </g>
                    );
                  })}
                </g>

                {/* 2. NODES LAYER */}
                <g className="nodes-layer">
                  {visibleNodes.map((node) => {
                    const pos = positions.get(node.id);
                    if (!pos) return null;

                    const isSelected = selected?.id === node.id;
                    const isHovered = hoveredNode?.id === node.id;
                    const isNeighbor = activeFocusId
                      ? connectedMap.get(activeFocusId)?.has(node.id)
                      : false;
                    const isFocus = isSelected || isHovered;
                    const isDimmed = activeFocusId && !isFocus && !isNeighbor;

                    const radius = pos.radius;

                    return (
                      <g
                        key={node.id}
                        transform={`translate(${pos.x}, ${pos.y})`}
                        onMouseDown={(e) => handleNodeMouseDown(e, node)}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelected(selected?.id === node.id ? null : node);
                        }}
                        onDoubleClick={(e) => handleNodeDoubleClick(e, node)}
                        onMouseEnter={() => setHoveredNode(node)}
                        onMouseLeave={() => setHoveredNode(null)}
                        className="cursor-pointer"
                        style={{
                          opacity: isDimmed ? 0.14 : 1,
                          transition: "opacity 150ms ease-out",
                        }}
                      >
                        {/* Focus Halo Ring */}
                        {isFocus && (
                          <circle
                            r={radius + 8}
                            fill="none"
                            stroke="#0284c7"
                            strokeWidth="2.2"
                            strokeOpacity="0.8"
                            className="animate-pulse"
                          />
                        )}

                        {/* Neighbor Accent Halo */}
                        {isNeighbor && !isFocus && (
                          <circle
                            r={radius + 5}
                            fill="none"
                            stroke="#38bdf8"
                            strokeWidth="1.8"
                            strokeOpacity="0.65"
                            strokeDasharray="3 3"
                          />
                        )}

                        {/* Distinct Geometric Node Shape */}
                        {renderShapeElement(node.type, isFocus, Boolean(isNeighbor))}

                        {/* Centered Entity Icon */}
                        {(() => {
                          const config = ENTITY_CONFIGS[node.type] || DEFAULT_CONFIG;
                          const IconComp = config.icon;
                          const iconSize = node.type === "EVENT" ? 13 : radius >= 20 ? 14 : 12;
                          return (
                            <foreignObject
                              x={-iconSize / 2}
                              y={-iconSize / 2}
                              width={iconSize}
                              height={iconSize}
                              className="pointer-events-none select-none"
                            >
                              <div className="w-full h-full flex items-center justify-center text-white/95">
                                <IconComp size={iconSize} strokeWidth={2.2} />
                              </div>
                            </foreignObject>
                          );
                        })()}

                        {/* Clean High-Contrast Node Label Below Node */}
                        <text
                          x="0"
                          y={radius + 15}
                          fill={isFocus ? "#0284c7" : "#334155"}
                          fontSize={isFocus ? "11.5" : "11"}
                          fontWeight={isFocus ? "700" : "500"}
                          textAnchor="middle"
                          letterSpacing="0.01em"
                          stroke="#eef3f8"
                          strokeWidth="3.5"
                          strokeLinejoin="round"
                          paintOrder="stroke fill"
                          className="pointer-events-none select-none"
                        >
                          {formatNodeLabel(node)}
                        </text>
                      </g>
                    );
                  })}
                </g>
              </g>
            </svg>

            {/* Bottom Context Helper */}
            <div className="absolute bottom-3 left-3 bg-white/90 backdrop-blur border border-slate-300 rounded-lg px-3 py-1.5 text-[11px] text-slate-600 pointer-events-none flex items-center gap-2 shadow-xs">
              <Sparkles className="w-3.5 h-3.5 text-sky-600" />
              <span>Scroll to zoom · Drag canvas to pan · Drag node to reposition · Click to inspect</span>
            </div>
          </div>

          {/* Right-Side Entity Inspector Drawer */}
          <aside className="border-l border-line bg-white p-4 sm:p-5 overflow-y-auto max-h-[640px]">
            {selected ? (
              <div className="space-y-4">
                {/* 1. Header with Type, Icon, Label & Close */}
                <div className="flex items-start justify-between gap-2 border-b border-line pb-3">
                  <div className="flex items-center gap-2.5 min-w-0">
                    {(() => {
                      const config = ENTITY_CONFIGS[selected.type] || DEFAULT_CONFIG;
                      const Icon = config.icon;
                      return (
                        <div
                          className="w-9 h-9 rounded-lg flex items-center justify-center border shadow-2xs shrink-0"
                          style={{ backgroundColor: config.fill, borderColor: config.stroke }}
                        >
                          <Icon className="w-4 h-4 text-white" />
                        </div>
                      );
                    })()}
                    <div className="min-w-0 flex-1">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 font-mono">
                        {selected.type}
                      </span>
                      <h2 className="text-sm sm:text-base font-bold text-slate-900 leading-snug truncate" title={selected.label}>
                        {selected.label}
                      </h2>
                    </div>
                  </div>
                  <button
                    onClick={() => setSelected(null)}
                    title="Back to Key Network Entities"
                    className="text-slate-400 hover:text-slate-700 p-1.5 rounded-lg hover:bg-slate-100 transition-colors shrink-0"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* 2. Network Role & Structural Centrality Box */}
                <div className="rounded-lg bg-slate-50 border border-slate-200/90 p-3 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-slate-600">Network Centrality:</span>
                    <span className="inline-flex items-center gap-1 font-bold text-[11px] bg-sky-100 text-sky-900 border border-sky-300 px-2 py-0.5 rounded-full">
                      <Sparkles className="w-3 h-3 text-sky-600" />
                      <span>{selectedRole}</span>
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-600 pt-1.5 border-t border-slate-200/60">
                    <span>Direct Connections:</span>
                    <span className="text-slate-900 font-bold font-mono">{selectedEdges.length}</span>
                  </div>
                  {selectedFinding && (
                    <div className="mt-2 text-xs text-purple-900 bg-purple-50 border border-purple-200 rounded p-2.5 leading-relaxed">
                      <p className="font-bold text-[10px] uppercase tracking-wider text-purple-800 mb-0.5 flex items-center gap-1">
                        <span>⚡ Structural Finding</span>
                      </p>
                      <p>{selectedFinding.explanation}</p>
                    </div>
                  )}
                </div>

                {/* 3. Investigator Review Action */}
                {onFlag && (
                  <div className="flex items-center justify-between gap-2 py-0.5">
                    <span className="text-xs text-slate-500 font-medium">Investigator Marker:</span>
                    {flaggedIds.has(selected.id) || flaggedIds.has(selected.label) ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-900 bg-amber-100 border border-amber-300 px-2 py-0.5 rounded">
                        <Flag className="w-3 h-3 text-amber-700" />
                        <span>Flagged for Review</span>
                      </span>
                    ) : (
                      <button
                        onClick={() =>
                          onFlag({
                            resourceType: selected.type,
                            resourceId: selected.id,
                            resourceLabel: `${selected.label} (${selected.type})`,
                          })
                        }
                        className="inline-flex items-center gap-1 text-xs font-semibold text-amber-800 bg-amber-50 hover:bg-amber-100 border border-amber-300 px-2.5 py-1 rounded transition-colors shadow-2xs"
                      >
                        <Flag className="w-3 h-3 text-amber-600" />
                        <span>Flag for Review</span>
                      </button>
                    )}
                  </div>
                )}

                {/* 4. Categorized Direct Connections */}
                <div className="space-y-3 pt-1 border-t border-line/60">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                      Connected Entities
                    </h3>
                    <span className="text-[11px] font-mono text-slate-400">
                      {selectedEdges.length} direct link{selectedEdges.length === 1 ? "" : "s"}
                    </span>
                  </div>

                  {/* Connected People */}
                  {categorizedConnections.people.length > 0 && (
                    <div className="space-y-1">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                        <Users className="w-3.5 h-3.5 text-sky-600" />
                        <span>People ({categorizedConnections.people.length})</span>
                      </div>
                      <div className="space-y-1">
                        {categorizedConnections.people.map(({ edge, otherNode, isOutbound }) => (
                          <button
                            key={edge.id}
                            onClick={() => focusNode(otherNode)}
                            className="w-full text-left p-2 rounded border border-line bg-slate-50/80 hover:bg-sky-50/70 hover:border-sky-300 transition-colors text-xs flex items-center justify-between group"
                          >
                            <div className="min-w-0 pr-2">
                              <div className="font-semibold text-slate-900 truncate flex items-center gap-1.5">
                                <span className="text-slate-400 text-[10px]">{isOutbound ? "→" : "←"}</span>
                                <span className="truncate">{otherNode.label}</span>
                              </div>
                              <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                                {edge.type.replaceAll("_", " ")}
                              </div>
                            </div>
                            <ArrowUpRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-accent shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Connected Organizations */}
                  {categorizedConnections.orgs.length > 0 && (
                    <div className="space-y-1 pt-1">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                        <Building2 className="w-3.5 h-3.5 text-purple-600" />
                        <span>Organizations ({categorizedConnections.orgs.length})</span>
                      </div>
                      <div className="space-y-1">
                        {categorizedConnections.orgs.map(({ edge, otherNode, isOutbound }) => (
                          <button
                            key={edge.id}
                            onClick={() => focusNode(otherNode)}
                            className="w-full text-left p-2 rounded border border-line bg-slate-50/80 hover:bg-purple-50/70 hover:border-purple-300 transition-colors text-xs flex items-center justify-between group"
                          >
                            <div className="min-w-0 pr-2">
                              <div className="font-semibold text-slate-900 truncate flex items-center gap-1.5">
                                <span className="text-slate-400 text-[10px]">{isOutbound ? "→" : "←"}</span>
                                <span className="truncate">{otherNode.label}</span>
                              </div>
                              <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                                {edge.type.replaceAll("_", " ")}
                              </div>
                            </div>
                            <ArrowUpRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-accent shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Connected Phones & Accounts */}
                  {categorizedConnections.phones.length > 0 && (
                    <div className="space-y-1 pt-1">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                        <Phone className="w-3.5 h-3.5 text-amber-600" />
                        <span>Phones & Accounts ({categorizedConnections.phones.length})</span>
                      </div>
                      <div className="space-y-1">
                        {categorizedConnections.phones.map(({ edge, otherNode, isOutbound }) => (
                          <button
                            key={edge.id}
                            onClick={() => focusNode(otherNode)}
                            className="w-full text-left p-2 rounded border border-line bg-slate-50/80 hover:bg-amber-50/70 hover:border-amber-300 transition-colors text-xs flex items-center justify-between group"
                          >
                            <div className="min-w-0 pr-2">
                              <div className="font-semibold text-slate-900 font-mono truncate flex items-center gap-1.5">
                                <span className="text-slate-400 text-[10px]">{isOutbound ? "→" : "←"}</span>
                                <span className="truncate">{otherNode.label}</span>
                              </div>
                              <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                                {edge.type.replaceAll("_", " ")}
                              </div>
                            </div>
                            <ArrowUpRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-accent shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Connected Vehicles */}
                  {categorizedConnections.vehicles.length > 0 && (
                    <div className="space-y-1 pt-1">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                        <Car className="w-3.5 h-3.5 text-amber-700" />
                        <span>Vehicles ({categorizedConnections.vehicles.length})</span>
                      </div>
                      <div className="space-y-1">
                        {categorizedConnections.vehicles.map(({ edge, otherNode, isOutbound }) => (
                          <button
                            key={edge.id}
                            onClick={() => focusNode(otherNode)}
                            className="w-full text-left p-2 rounded border border-line bg-slate-50/80 hover:bg-amber-50/70 hover:border-amber-300 transition-colors text-xs flex items-center justify-between group"
                          >
                            <div className="min-w-0 pr-2">
                              <div className="font-semibold text-slate-900 font-mono truncate flex items-center gap-1.5">
                                <span className="text-slate-400 text-[10px]">{isOutbound ? "→" : "←"}</span>
                                <span className="truncate">{otherNode.label}</span>
                              </div>
                              <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                                {edge.type.replaceAll("_", " ")}
                              </div>
                            </div>
                            <ArrowUpRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-accent shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Connected Locations */}
                  {categorizedConnections.locations.length > 0 && (
                    <div className="space-y-1 pt-1">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                        <MapPin className="w-3.5 h-3.5 text-rose-600" />
                        <span>Locations ({categorizedConnections.locations.length})</span>
                      </div>
                      <div className="space-y-1">
                        {categorizedConnections.locations.map(({ edge, otherNode, isOutbound }) => (
                          <button
                            key={edge.id}
                            onClick={() => focusNode(otherNode)}
                            className="w-full text-left p-2 rounded border border-line bg-slate-50/80 hover:bg-rose-50/70 hover:border-rose-300 transition-colors text-xs flex items-center justify-between group"
                          >
                            <div className="min-w-0 pr-2">
                              <div className="font-semibold text-slate-900 truncate flex items-center gap-1.5">
                                <span className="text-slate-400 text-[10px]">{isOutbound ? "→" : "←"}</span>
                                <span className="truncate">{otherNode.label}</span>
                              </div>
                              <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                                {edge.type.replaceAll("_", " ")}
                              </div>
                            </div>
                            <ArrowUpRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-accent shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Connected Events & Other Nodes */}
                  {(categorizedConnections.events.length > 0 || categorizedConnections.others.length > 0) && (
                    <div className="space-y-1 pt-1">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                        <Clock className="w-3.5 h-3.5 text-slate-600" />
                        <span>Events & Linked Nodes ({categorizedConnections.events.length + categorizedConnections.others.length})</span>
                      </div>
                      <div className="space-y-1">
                        {[...categorizedConnections.events, ...categorizedConnections.others].map(({ edge, otherNode, isOutbound }) => (
                          <button
                            key={edge.id}
                            onClick={() => focusNode(otherNode)}
                            className="w-full text-left p-2 rounded border border-line bg-slate-50/80 hover:bg-slate-100 transition-colors text-xs flex items-center justify-between group"
                          >
                            <div className="min-w-0 pr-2">
                              <div className="font-semibold text-slate-900 truncate flex items-center gap-1.5">
                                <span className="text-slate-400 text-[10px]">{isOutbound ? "→" : "←"}</span>
                                <span className="truncate">{otherNode.label}</span>
                              </div>
                              <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                                {edge.type.replaceAll("_", " ")}
                              </div>
                            </div>
                            <ArrowUpRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-accent shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {!selectedEdges.length && (
                    <p className="text-xs text-slate-400 italic py-1">No direct relationships recorded in current view.</p>
                  )}
                </div>

                {/* 5. Supporting Evidence Documents */}
                {selectedEvidenceIds.length > 0 && (
                  <div className="pt-2 border-t border-line/60">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                      Supporting Evidence ({selectedEvidenceIds.length})
                    </h3>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedEvidenceIds.map((eid) => (
                        <Link
                          key={eid}
                          href={`/evidence/${eid}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-100 border border-line font-mono text-xs text-slate-700 hover:text-accent hover:border-accent hover:bg-sky-50 transition-colors"
                        >
                          <FileText className="w-3 h-3 text-slate-400" />
                          <span>{eid}</span>
                        </Link>
                      ))}
                    </div>
                  </div>
                )}

                {/* 6. Stored Properties */}
                <div className="pt-2 border-t border-line/60">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                    Entity Properties
                  </h3>
                  <dl className="space-y-1.5 text-xs border border-line rounded-lg p-2.5 bg-slate-50/80">
                    <div className="flex justify-between py-0.5 border-b border-line/60">
                      <dt className="text-slate-500 font-mono text-[11px]">ID</dt>
                      <dd className="font-mono text-slate-800 text-right truncate max-w-[170px]" title={selected.id}>
                        {selected.id}
                      </dd>
                    </div>
                    {Object.entries(selected.properties).map(([k, v]) => (
                      <div
                        key={k}
                        className="flex justify-between py-0.5 border-b border-line/60 last:border-0"
                      >
                        <dt className="text-slate-500 capitalize truncate max-w-[100px]">{k.replaceAll("_", " ")}</dt>
                        <dd className="font-medium text-slate-800 text-right truncate max-w-[170px]" title={String(v ?? "-")}>
                          {String(v ?? "-")}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </div>
              </div>
            ) : (
              /* DEFAULT STATE: KEY NETWORK ENTITIES OVERVIEW */
              <div className="space-y-4">
                {/* Header */}
                <div className="border-b border-line pb-3">
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-accent" />
                    <h2 className="text-sm font-bold uppercase tracking-wider text-slate-900">
                      Key Network Entities
                    </h2>
                  </div>
                  <p className="text-xs text-slate-500 mt-1 leading-snug">
                    Structurally central entities identified from network connectivity & graph topology.
                  </p>
                </div>

                {/* Graph Summary Pills */}
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="p-2 rounded bg-slate-50 border border-line">
                    <p className="text-[10px] uppercase font-bold text-slate-500">Nodes</p>
                    <p className="text-sm font-bold text-slate-900 mt-0.5">{graph?.nodes.length ?? 0}</p>
                  </div>
                  <div className="p-2 rounded bg-slate-50 border border-line">
                    <p className="text-[10px] uppercase font-bold text-slate-500">Links</p>
                    <p className="text-sm font-bold text-slate-900 mt-0.5">{graph?.edges.length ?? 0}</p>
                  </div>
                  <div className="p-2 rounded bg-sky-50 border border-sky-200">
                    <p className="text-[10px] uppercase font-bold text-sky-800">Key Hubs</p>
                    <p className="text-sm font-bold text-sky-900 mt-0.5">
                      {keyEntities.people.length + keyEntities.orgs.length + keyEntities.phones.length}
                    </p>
                  </div>
                </div>

                {/* Highly Connected Persons */}
                {keyEntities.people.length > 0 && (
                  <div className="space-y-2 pt-1">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                        <Users className="w-3.5 h-3.5 text-sky-600" />
                        <span>Connected Persons</span>
                      </h3>
                      <span className="text-[10px] font-mono text-slate-400">
                        {keyEntities.people.length}
                      </span>
                    </div>
                    <div className="space-y-1.5">
                      {keyEntities.people.slice(0, 4).map(({ node, degree, finding }) => (
                        <button
                          key={node.id}
                          onClick={() => focusNode(node)}
                          className="w-full text-left p-2.5 rounded-lg border border-line bg-slate-50/80 hover:bg-sky-50/70 hover:border-sky-300 transition-colors flex items-center justify-between group"
                        >
                          <div className="min-w-0 pr-2">
                            <p className="font-semibold text-xs text-slate-900 truncate group-hover:text-accent">
                              {node.label}
                            </p>
                            <div className="flex items-center gap-1.5 mt-1">
                              <span className="inline-flex items-center text-[10px] font-mono font-medium text-slate-600 bg-white border border-line px-1.5 py-0.2 rounded">
                                {degree} connection{degree === 1 ? "" : "s"}
                              </span>
                              {finding && (
                                <span className="inline-flex items-center text-[10px] font-bold text-purple-700 bg-purple-50 border border-purple-200 px-1.5 py-0.2 rounded">
                                  <span>⚡ Central Hub</span>
                                </span>
                              )}
                            </div>
                          </div>
                          <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-accent opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Key Organizations */}
                {keyEntities.orgs.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-line/60">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                        <Building2 className="w-3.5 h-3.5 text-purple-600" />
                        <span>Organizations</span>
                      </h3>
                      <span className="text-[10px] font-mono text-slate-400">
                        {keyEntities.orgs.length}
                      </span>
                    </div>
                    <div className="space-y-1.5">
                      {keyEntities.orgs.slice(0, 3).map(({ node, degree }) => (
                        <button
                          key={node.id}
                          onClick={() => focusNode(node)}
                          className="w-full text-left p-2.5 rounded-lg border border-line bg-slate-50/80 hover:bg-purple-50/70 hover:border-purple-300 transition-colors flex items-center justify-between group"
                        >
                          <div className="min-w-0 pr-2">
                            <p className="font-semibold text-xs text-slate-900 truncate group-hover:text-purple-700">
                              {node.label}
                            </p>
                            <p className="text-[10px] font-mono text-slate-500 mt-1">
                              {degree} direct linkage{degree === 1 ? "" : "s"}
                            </p>
                          </div>
                          <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-accent opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Communication Hubs (Phones & Accounts) */}
                {keyEntities.phones.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-line/60">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                        <Phone className="w-3.5 h-3.5 text-amber-600" />
                        <span>Communication Hubs</span>
                      </h3>
                      <span className="text-[10px] font-mono text-slate-400">
                        {keyEntities.phones.length}
                      </span>
                    </div>
                    <div className="space-y-1.5">
                      {keyEntities.phones.slice(0, 3).map(({ node, degree }) => (
                        <button
                          key={node.id}
                          onClick={() => focusNode(node)}
                          className="w-full text-left p-2.5 rounded-lg border border-line bg-slate-50/80 hover:bg-amber-50/70 hover:border-amber-300 transition-colors flex items-center justify-between group"
                        >
                          <div className="min-w-0 pr-2">
                            <p className="font-semibold text-xs text-slate-900 font-mono truncate group-hover:text-amber-800">
                              {node.label}
                            </p>
                            <p className="text-[10px] font-mono text-slate-500 mt-1">
                              {degree} link{degree === 1 ? "" : "s"}
                            </p>
                          </div>
                          <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-accent opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Key Vehicles & Locations */}
                {keyEntities.others.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-line/60">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5 text-rose-600" />
                        <span>Vehicles & Locations</span>
                      </h3>
                      <span className="text-[10px] font-mono text-slate-400">
                        {keyEntities.others.length}
                      </span>
                    </div>
                    <div className="space-y-1.5">
                      {keyEntities.others.slice(0, 3).map(({ node, degree }) => (
                        <button
                          key={node.id}
                          onClick={() => focusNode(node)}
                          className="w-full text-left p-2.5 rounded-lg border border-line bg-slate-50/80 hover:bg-rose-50/70 hover:border-rose-300 transition-colors flex items-center justify-between group"
                        >
                          <div className="min-w-0 pr-2">
                            <p className="font-semibold text-xs text-slate-900 truncate group-hover:text-rose-700">
                              {node.label}
                            </p>
                            <p className="text-[10px] font-mono text-slate-500 mt-1">
                              {node.type} &bull; {degree} link{degree === 1 ? "" : "s"}
                            </p>
                          </div>
                          <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-accent opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Footer hint */}
                <div className="pt-3 border-t border-line/60 text-center">
                  <p className="text-[11px] text-slate-400 italic">
                    Click any node on the graph or list above to inspect connections, evidence, and properties.
                  </p>
                </div>
              </div>
            )}
          </aside>
        </div>
      )}
    </section>
  );
}

function formatTimelineDateTime(dateStr?: string | null, timeStr?: string | null): string {
  if (!dateStr && !timeStr) return "Date unknown";

  let raw = (dateStr || "").trim();
  const timeVal = (timeStr || "").trim();

  if (timeVal && !raw.includes("T") && !raw.includes(" ")) {
    raw = `${raw}T${timeVal}`;
  } else if (!raw && timeVal) {
    raw = timeVal;
  }

  const d = new Date(raw);
  if (!isNaN(d.getTime())) {
    const day = d.getDate();
    const month = d.toLocaleString("en-US", { month: "short" });
    const year = d.getFullYear();
    const hours = d.getHours();
    const minutes = d.getMinutes();
    const ampm = hours >= 12 ? "PM" : "AM";
    const formattedHours = hours % 12 || 12;
    const formattedMins = minutes < 10 ? `0${minutes}` : minutes;

    if (timeVal || raw.includes("T") || raw.includes(":") || raw.includes(" ")) {
      return `${day} ${month} ${year} · ${formattedHours}:${formattedMins} ${ampm}`;
    }
    return `${day} ${month} ${year}`;
  }

  const cleanDate = (dateStr || "").split("T")[0];
  const parts = cleanDate.split(/[-/]/);
  if (parts.length === 3) {
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    let y = parts[0], m = parseInt(parts[1], 10) - 1, dayStr = parts[2];
    if (parts[0].length === 2 && parts[2].length === 4) {
      dayStr = parts[0];
      m = parseInt(parts[1], 10) - 1;
      y = parts[2];
    }
    const mName = months[m] || parts[1];
    let timeText = "";
    if (timeVal) {
      const tParts = timeVal.split(":");
      if (tParts.length >= 2) {
        let hrs = parseInt(tParts[0], 10);
        const mins = tParts[1].substring(0, 2);
        const ampm = hrs >= 12 ? "PM" : "AM";
        hrs = hrs % 12 || 12;
        timeText = ` · ${hrs}:${mins} ${ampm}`;
      } else {
        timeText = ` · ${timeVal}`;
      }
    }
    return `${dayStr} ${mName} ${y}${timeText}`;
  }

  return [dateStr, timeStr].filter(Boolean).join(" · ");
}

function formatDuration(val: unknown): string | null {
  if (val === undefined || val === null || val === "") return null;
  const num = Number(val);
  if (!isNaN(num) && num > 0) {
    const mins = Math.floor(num / 60);
    const secs = Math.floor(num % 60);
    if (mins > 0) {
      return `${mins}m ${secs < 10 ? "0" : ""}${secs}s`;
    }
    return `${secs}s`;
  }
  return String(val);
}

function formatAmount(val: unknown): string | null {
  if (val === undefined || val === null || val === "") return null;
  const str = String(val).trim();
  if (str.startsWith("₹")) return str;
  const num = Number(str.replaceAll(",", "").replaceAll("₹", "").replaceAll("Rs.", "").trim());
  if (!isNaN(num)) {
    return "₹" + num.toLocaleString("en-IN");
  }
  return `₹${val}`;
}

function TimelineEventCard({
  ev,
  idx,
  onFlag,
  isFlagged,
}: {
  ev: Record<string, unknown>;
  idx: number;
  onFlag?: (ev: Record<string, unknown>) => void;
  isFlagged?: boolean;
}) {
  const [showRaw, setShowRaw] = useState(false);

  const typeStr = String(ev.type || "EVENT").toUpperCase();

  let payload: Record<string, unknown> | null = null;
  let rawText: string | null = null;

  if (typeof ev.sourceRow === "object" && ev.sourceRow !== null) {
    payload = ev.sourceRow as Record<string, unknown>;
  }

  if (typeof ev.sourceText === "string" && ev.sourceText.trim()) {
    const trimmed = ev.sourceText.trim();
    if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
      try {
        const parsed = JSON.parse(trimmed);
        if (typeof parsed === "object" && parsed !== null) {
          payload = { ...(payload || {}), ...parsed };
        }
      } catch {
        rawText = trimmed;
      }
    } else {
      rawText = trimmed;
    }
  }

  const participantsArr: string[] = Array.isArray(ev.participants)
    ? ev.participants.map((p: any) => (typeof p === "object" && p !== null ? (p.text || p.normalizedValue || String(p)) : String(p)))
    : (typeof payload?.participants === "string" ? [payload.participants as string] : Array.isArray(payload?.participants) ? (payload.participants as any[]).map(String) : []);

  const caller = String(payload?.caller || payload?.calling_number || payload?.from || "");
  const receiver = String(payload?.receiver || payload?.called_number || payload?.to || payload?.recipient || "");
  const duration = payload?.duration || payload?.call_duration;
  const cellTower = String(payload?.cell_tower || payload?.tower || payload?.cell_site || "");

  const senderAcc = String(payload?.sender_account || payload?.account_a || payload?.sender || payload?.from_account || "");
  const receiverAcc = String(payload?.receiver_account || payload?.account_b || payload?.receiver || payload?.to_account || "");
  const amount = payload?.amount || payload?.value || payload?.sum;
  const txId = String(payload?.transaction_id || payload?.tx_id || payload?.ref_no || payload?.reference_id || "");

  const locationName = String(payload?.location || payload?.location_name || payload?.place || payload?.venue || ev.location || "");
  const vehicleName = String(payload?.vehicle || payload?.vehicle_no || payload?.vehicle_number || payload?.subject || payload?.target || "");

  const isCall = typeStr.includes("CALL") || typeStr === "CONTACTED";
  const isMeeting = typeStr.includes("MEET") || typeStr.includes("ENCOUNTER");
  const isFinancial = typeStr.includes("FINANC") || typeStr.includes("TRANS") || typeStr.includes("PAY") || typeStr.includes("BANK") || typeStr === "TRANSFER";
  const isLocation = typeStr.includes("LOCAT") || typeStr.includes("SIGHT") || typeStr.includes("MOVE") || typeStr.includes("TRAVEL");

  const formattedDuration = formatDuration(duration);
  const formattedAmount = formatAmount(amount);

  const dateTimeDisplay = formatTimelineDateTime(
    (payload?.timestamp as string) || (ev.date as string),
    (payload?.time as string) || (ev.time as string)
  );

  return (
    <article className={`panel p-5 relative shadow-sm hover:shadow transition-shadow border-l-4 ${isFlagged ? "border-l-amber-500 bg-amber-50/15" : "border-l-navy"}`}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
        <div className="flex items-center gap-2">
          {isCall ? (
            <span className="inline-flex items-center gap-1.5 border border-sky-200 bg-sky-50 px-2.5 py-1 text-xs font-bold uppercase tracking-wider text-sky-900 rounded">
              <Phone className="h-3.5 w-3.5 text-sky-600" />
              CALL
            </span>
          ) : isMeeting ? (
            <span className="inline-flex items-center gap-1.5 border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-xs font-bold uppercase tracking-wider text-indigo-900 rounded">
              <Users className="h-3.5 w-3.5 text-indigo-600" />
              MEETING
            </span>
          ) : isFinancial ? (
            <span className="inline-flex items-center gap-1.5 border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-bold uppercase tracking-wider text-emerald-900 rounded">
              <CreditCard className="h-3.5 w-3.5 text-emerald-600" />
              FINANCIAL TRANSACTION
            </span>
          ) : isLocation ? (
            <span className="inline-flex items-center gap-1.5 border border-rose-200 bg-rose-50 px-2.5 py-1 text-xs font-bold uppercase tracking-wider text-rose-900 rounded">
              <MapPin className="h-3.5 w-3.5 text-rose-600" />
              LOCATION EVENT
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 border border-slate-200 bg-slate-100 px-2.5 py-1 text-xs font-bold uppercase tracking-wider text-slate-800 rounded">
              <Clock className="h-3.5 w-3.5 text-slate-600" />
              {typeStr.replaceAll("_", " ")}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {onFlag && (
            <button
              onClick={() => onFlag(ev)}
              className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded transition-colors ${
                isFlagged
                  ? "bg-amber-100 text-amber-900 border border-amber-300 font-bold"
                  : "text-slate-500 hover:text-amber-800 hover:bg-amber-50 border border-line"
              }`}
              title={isFlagged ? "Event is flagged for review" : "Flag event for review"}
            >
              <Flag className="h-3 w-3 text-amber-600" />
              <span>{isFlagged ? "Flagged" : "Flag"}</span>
            </button>
          )}
          <div className="text-xs font-medium text-slate-600 font-mono bg-slate-50 border border-line px-2.5 py-1 rounded">
            {dateTimeDisplay}
          </div>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        {isCall ? (
          <div>
            <div className="text-base font-semibold text-slate-900 font-mono tracking-tight flex items-center gap-2">
              <span className="text-slate-900">{caller || (participantsArr[0] ?? "Unknown Caller")}</span>
              <span className="text-sky-600 font-bold text-lg">→</span>
              <span className="text-slate-900">{receiver || (participantsArr[1] ?? "Unknown Receiver")}</span>
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-2 text-xs text-slate-600">
              {formattedDuration ? (
                <div className="bg-slate-50 border border-line px-2.5 py-1.5 rounded">
                  <span className="font-semibold text-slate-700">Duration:</span> {formattedDuration}
                </div>
              ) : null}
              {cellTower ? (
                <div className="bg-slate-50 border border-line px-2.5 py-1.5 rounded">
                  <span className="font-semibold text-slate-700">Cell Tower:</span> {cellTower}
                </div>
              ) : null}
              {locationName && !cellTower ? (
                <div className="bg-slate-50 border border-line px-2.5 py-1.5 rounded">
                  <span className="font-semibold text-slate-700">Location:</span> {locationName}
                </div>
              ) : null}
            </div>
          </div>
        ) : isMeeting ? (
          <div>
            <div className="text-base font-semibold text-slate-900">
              {participantsArr.length >= 2 ? (
                <span>{participantsArr[0]} met {participantsArr.slice(1).join(", ")}</span>
              ) : participantsArr.length === 1 ? (
                <span>Meeting involving {participantsArr[0]}</span>
              ) : rawText ? (
                <span>{rawText}</span>
              ) : (
                <span>Meeting Event</span>
              )}
            </div>
            {locationName ? (
              <div className="mt-2 text-xs text-slate-600 bg-slate-50 border border-line px-2.5 py-1.5 rounded inline-block">
                <span className="font-semibold text-slate-700">Location:</span> {locationName}
              </div>
            ) : null}
          </div>
        ) : isFinancial ? (
          <div>
            <div className="text-base font-semibold text-slate-900 font-mono tracking-tight flex items-center gap-2">
              <span className="text-slate-900">{senderAcc || (participantsArr[0] ?? "Account A")}</span>
              <span className="text-emerald-600 font-bold text-lg">→</span>
              <span className="text-slate-900">{receiverAcc || (participantsArr[1] ?? "Account B")}</span>
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-2 text-xs text-slate-600">
              {formattedAmount ? (
                <div className="bg-emerald-50/50 border border-emerald-200 px-2.5 py-1.5 rounded">
                  <span className="font-semibold text-emerald-900">Amount:</span> <strong className="text-emerald-900">{formattedAmount}</strong>
                </div>
              ) : null}
              {txId ? (
                <div className="bg-slate-50 border border-line px-2.5 py-1.5 rounded">
                  <span className="font-semibold text-slate-700">Transaction ID:</span> <span className="font-mono">{txId}</span>
                </div>
              ) : null}
              {locationName ? (
                <div className="bg-slate-50 border border-line px-2.5 py-1.5 rounded">
                  <span className="font-semibold text-slate-700">Location:</span> {locationName}
                </div>
              ) : null}
            </div>
          </div>
        ) : isLocation ? (
          <div>
            <div className="text-sm font-semibold text-slate-900">
              {vehicleName ? (
                <span>Vehicle <strong className="font-mono text-slate-900">{vehicleName}</strong> observed at:</span>
              ) : participantsArr.length > 0 ? (
                <span>{participantsArr.join(", ")} observed at:</span>
              ) : (
                <span>Location event observed:</span>
              )}
            </div>
            {locationName ? (
              <div className="mt-2 text-sm font-medium text-rose-900 bg-rose-50 border border-rose-200 px-3 py-1.5 rounded inline-block">
                📍 {locationName}
              </div>
            ) : null}
          </div>
        ) : (
          <div>
            {rawText ? (
              <p className="text-sm font-medium text-slate-900 leading-relaxed">{rawText}</p>
            ) : participantsArr.length > 0 ? (
              <p className="text-sm font-medium text-slate-900">Participants: {participantsArr.join(", ")}</p>
            ) : (
              <p className="text-sm font-medium text-slate-900">{typeStr.replaceAll("_", " ")}</p>
            )}
            {locationName ? (
              <div className="mt-2 text-xs text-slate-600 bg-slate-50 border border-line px-2.5 py-1.5 rounded inline-block">
                <span className="font-semibold text-slate-700">Location:</span> {locationName}
              </div>
            ) : null}
          </div>
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-line flex flex-wrap items-center justify-between text-xs text-slate-500 gap-2">
        <div>
          {ev.evidenceId ? (
            <Link
              href={`/evidence/${String(ev.evidenceId)}`}
              className="inline-flex items-center gap-1 font-mono text-slate-600 hover:text-accent hover:underline transition-colors"
            >
              <FileText className="h-3.5 w-3.5 text-slate-400" />
              <span>Source Evidence: <strong className="text-slate-800">{String(ev.evidenceId)}</strong></span>
            </Link>
          ) : (
            <span className="text-slate-400 italic">Source Evidence: -</span>
          )}
        </div>
        {ev.confidence !== undefined && ev.confidence !== null && (
          <div className="font-mono text-slate-600">
            Confidence: <strong className="text-slate-800">{Math.round(Number(ev.confidence) * (Number(ev.confidence) <= 1 ? 100 : 1))}%</strong>
          </div>
        )}
      </div>

      <div className="mt-2">
        <button
          onClick={() => setShowRaw(!showRaw)}
          className="text-[11px] text-slate-400 hover:text-slate-600 font-mono flex items-center gap-1 transition-colors"
        >
          <Code className="h-3 w-3" />
          <span>{showRaw ? "Hide raw event data" : "View raw event data"}</span>
        </button>
        {showRaw && (
          <pre className="mt-2 p-3 bg-slate-900 text-emerald-400 font-mono text-xs rounded border border-slate-800 overflow-x-auto max-h-60">
            {JSON.stringify(payload || ev, null, 2)}
          </pre>
        )}
      </div>
    </article>
  );
}

export function TimelineView({
  token,
  caseNumber,
  onFlag,
  flaggedIds = new Set(),
}: {
  token: string;
  caseNumber: string;
  onFlag?: (ev: Record<string, unknown>) => void;
  flaggedIds?: Set<string>;
}) {
  const [events, setEvents] = useState<Array<Record<string, unknown>>>([]);
  const [filter, setFilter] = useState("ALL");

  useEffect(() => {
    api<{ events: Array<Record<string, unknown>> }>(`/cases/${caseNumber}/timeline`, token)
      .then(result => setEvents(result.events))
      .catch(() => setEvents([]));
  }, [token, caseNumber]);

  const types = Array.from(new Set(events.map(e => String((e as any).type || "OTHER"))));

  const filteredEvents = events.filter(e => {
    if (filter === "ALL") return true;
    const typeStr = String((e as any).type || "").toUpperCase();
    return typeStr === filter.toUpperCase();
  });

  const eventsByDate = filteredEvents.reduce((acc: Record<string, Array<Record<string, unknown>>>, ev: Record<string, unknown>) => {
    const d = String(ev.date || "Undated");
    if (!acc[d]) acc[d] = [];
    acc[d].push(ev);
    return acc;
  }, {} as Record<string, Array<Record<string, unknown>>>);

  const dates = Object.keys(eventsByDate);

  return (
    <section className="mt-6 space-y-6">
      <div className="panel p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold uppercase text-slate-500 mr-2">Filter Events:</span>
          <button
            onClick={() => setFilter("ALL")}
            className={`px-3 py-1.5 text-xs font-semibold rounded border transition-colors ${
              filter === "ALL" ? "bg-accent text-white border-accent" : "bg-white text-slate-700 border-line hover:bg-slate-50"
            }`}
          >
            All ({events.length})
          </button>
          {types.map(t => (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className={`px-3 py-1.5 text-xs font-semibold rounded border transition-colors ${
                filter === t ? "bg-accent text-white border-accent" : "bg-white text-slate-700 border-line hover:bg-slate-50"
              }`}
            >
              {t.replaceAll("_", " ")} ({events.filter(e => String((e as any).type || "") === t).length})
            </button>
          ))}
        </div>
        <span className="text-xs text-slate-500">{filteredEvents.length} events displayed</span>
      </div>

      {!filteredEvents.length ? (
        <EmptyState title="No timeline events" body="No authorized event records match the selected filter." />
      ) : (
        <div className="relative pl-6 space-y-8 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-line">
          {dates.map(date => (
            <div key={date} className="relative">
              <div className="flex items-center gap-3 mb-4">
                <div className="relative z-10 -ml-6 flex h-6 w-6 items-center justify-center rounded-full bg-navy text-white text-xs font-bold border-2 border-white shadow">
                  •
                </div>
                <h3 className="font-semibold text-sm tracking-wide text-slate-900 bg-slate-100 border border-line px-3 py-1 rounded inline-block">
                  📅 {formatTimelineDateTime(date)}
                </h3>
              </div>

              <div className="space-y-4 ml-2">
                {eventsByDate[date].map((event: any, idx: number) => {
                  const eventId = String(event.id || event.event_key || `EVENT-${idx}`);
                  const isFlagged = flaggedIds.has(eventId);
                  return (
                    <TimelineEventCard
                      key={String(event.id || idx)}
                      ev={event}
                      idx={idx}
                      onFlag={onFlag}
                      isFlagged={isFlagged}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export function IntelligenceView({
  token,
  caseNumber,
  onFlag,
  flaggedIds = new Set(),
}: {
  token: string;
  caseNumber: string;
  onFlag?: (finding: Finding) => void;
  flaggedIds?: Set<string>;
}) {
  const [findings, setFindings] = useState<Finding[]>([]);
  useEffect(() => {
    api<{ findings: Finding[] }>(`/cases/${caseNumber}/intelligence`, token)
      .then(result => setFindings(result.findings))
      .catch(() => setFindings([]));
  }, [token, caseNumber]);

  return (
    <section className="mt-6 space-y-4">
      {findings.length ? (
        findings.map((finding, index) => {
          const findingId = finding.id || `FINDING-${finding.title.replace(/\s+/g, '_')}`;
          const isFlagged = flaggedIds.has(findingId) || flaggedIds.has(finding.title);
          return (
            <article
              className={`panel p-5 transition-all border ${
                isFlagged ? "border-amber-300 bg-amber-50/20" : "border-line"
              }`}
              key={finding.id || `${finding.title}-${finding.metric}-${index}`}
            >
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm font-semibold text-slate-900">{finding.title}</p>
                {onFlag && (
                  <button
                    onClick={() => onFlag(finding)}
                    className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded transition-colors ${
                      isFlagged
                        ? "bg-amber-100 text-amber-900 border border-amber-300 font-bold"
                        : "text-slate-500 hover:text-amber-800 hover:bg-amber-50 border border-line"
                    }`}
                    title={isFlagged ? "Finding is flagged for review" : "Flag finding for review"}
                  >
                    <Flag className="h-3 w-3 text-amber-600" />
                    <span>{isFlagged ? "Flagged" : "Flag"}</span>
                  </button>
                )}
              </div>
              <p className="mt-2 text-sm text-slate-700 leading-relaxed">{finding.explanation}</p>
              <div className="mt-3 pt-2 border-t border-line flex flex-wrap items-center justify-between text-xs text-slate-500 gap-2">
                <span>Strength: <strong className="text-slate-700">{Math.round(finding.confidence * 100)}%</strong></span>
                <span>Source Evidence: <strong className="text-slate-700">{finding.evidenceIds.join(", ") || "-"}</strong></span>
              </div>
            </article>
          );
        })
      ) : (
        <EmptyState
          title="No structural signals yet"
          body="No sufficient relationship or event data is available to generate this signal yet."
        />
      )}
    </section>
  );
}
