"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ArrowLeft,
  GitMerge,
  Info,
  ZoomIn,
  ZoomOut,
  Maximize2,
} from "lucide-react";
import {
  Curriculum,
  PrerequisiteGraph,
  PrerequisiteGraphNode,
  PrerequisiteGraphEdge,
  SubjectType,
} from "@/types/catalog";

const TYPE_COLORS: Record<SubjectType, string> = {
  CORE: "#38bdf8",
  ELECTIVE: "#a78bfa",
  LAB: "#34d399",
  PROJECT: "#fbbf24",
  SEMINAR: "#f472b6",
};

const SEMESTER_COLORS = [
  "#6366f1", "#8b5cf6", "#a855f7", "#ec4899",
  "#f97316", "#eab308", "#22c55e", "#14b8a6",
];

const NODE_R = 30;
const NODE_W = 120;
const NODE_H = 56;
const SEM_PADDING = 60;
const HORIZONTAL_GAP = 160;
const VERTICAL_GAP = 90;

interface NodePosition {
  x: number;
  y: number;
  node: PrerequisiteGraphNode;
}

function buildLayout(
  nodes: PrerequisiteGraphNode[]
): NodePosition[] {
  // Group by semester
  const bySem: Record<number, PrerequisiteGraphNode[]> = {};
  for (const n of nodes) {
    const s = n.semesterNumber;
    if (!bySem[s]) bySem[s] = [];
    bySem[s].push(n);
  }

  const semesters = Object.keys(bySem)
    .map(Number)
    .sort((a, b) => a - b);

  const positions: NodePosition[] = [];
  let x = SEM_PADDING;

  for (const sem of semesters) {
    const semNodes = bySem[sem];
    const colHeight = semNodes.length * VERTICAL_GAP;
    let y = SEM_PADDING;

    for (const node of semNodes) {
      positions.push({ x, y, node });
      y += VERTICAL_GAP;
    }
    x += HORIZONTAL_GAP;
  }

  return positions;
}

function getSemesterBands(
  positions: NodePosition[]
): Array<{ x: number; width: number; sem: number }> {
  const bySem: Record<number, NodePosition[]> = {};
  for (const p of positions) {
    const s = p.node.semesterNumber;
    if (!bySem[s]) bySem[s] = [];
    bySem[s].push(p);
  }

  const semesters = Object.keys(bySem)
    .map(Number)
    .sort((a, b) => a - b);

  return semesters.map((sem, idx) => ({
    sem,
    x: SEM_PADDING + idx * HORIZONTAL_GAP - NODE_W / 2 - 10,
    width: HORIZONTAL_GAP,
  }));
}

export default function PrerequisiteGraphPage() {
  const { user } = useAuth();
  const orgId = user?.tenant?.organizationId || "";

  const [selectedCurriculumId, setSelectedCurriculumId] = useState<string>("");
  const [zoom, setZoom] = useState(1);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const { data: curricula = [], isLoading: loadingCurr } = useQuery<Curriculum[]>({
    queryKey: ["curricula_all", orgId],
    queryFn: async () => {
      const res = await api.get<any>(
        `/organizations/${orgId}/catalog/curricula?limit=100&status=ACTIVE`
      );
      return Array.isArray(res) ? res : res?.data ?? res ?? [];
    },
    enabled: !!orgId,
  });

  const { data: graph, isLoading: loadingGraph } = useQuery<PrerequisiteGraph>({
    queryKey: ["prereq_graph", orgId, selectedCurriculumId],
    queryFn: () =>
      api.get<PrerequisiteGraph>(
        `/organizations/${orgId}/catalog/curricula/${selectedCurriculumId}/prerequisite-graph`
      ),
    enabled: !!orgId && !!selectedCurriculumId,
  });

  // Auto-select first curriculum
  useEffect(() => {
    if (curricula.length > 0 && !selectedCurriculumId) {
      setSelectedCurriculumId(curricula[0].curriculumId);
    }
  }, [curricula, selectedCurriculumId]);

  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];

  const positions = buildLayout(nodes);
  const posMap = Object.fromEntries(positions.map((p) => [p.node.id, p]));
  const semBands = getSemesterBands(positions);

  const svgWidth = positions.length > 0
    ? Math.max(...positions.map((p) => p.x)) + NODE_W / 2 + SEM_PADDING
    : 400;
  const svgHeight = positions.length > 0
    ? Math.max(...positions.map((p) => p.y)) + NODE_H / 2 + SEM_PADDING
    : 300;

  // Compute which nodes are highlighted based on hover
  const getHighlightedNodes = useCallback(() => {
    if (!hoveredNode) return new Set<string>();
    const connected = new Set<string>([hoveredNode]);
    for (const edge of edges) {
      if (edge.from === hoveredNode) connected.add(edge.to);
      if (edge.to === hoveredNode) connected.add(edge.from);
    }
    return connected;
  }, [hoveredNode, edges]);

  const highlighted = getHighlightedNodes();

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Link href="/dashboard/catalog" className="hover:text-foreground transition-colors">
              Catalog
            </Link>
            <span>/</span>
            <span>Prerequisite Graph</span>
          </div>
          <h2 className="text-base font-bold">Prerequisite Graph Viewer</h2>
        </div>

        <div className="flex items-center gap-3">
          {/* Curriculum selector */}
          {loadingCurr ? (
            <Skeleton className="h-9 w-48" />
          ) : (
            <select
              value={selectedCurriculumId}
              onChange={(e) => setSelectedCurriculumId(e.target.value)}
              className="h-9 px-3 rounded-lg border border-border bg-background text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-violet-500"
            >
              <option value="">Select curriculum…</option>
              {curricula.map((c) => (
                <option key={c.curriculumId} value={c.curriculumId}>
                  {c.name} v{c.version}
                </option>
              ))}
            </select>
          )}

          {/* Zoom controls */}
          <div className="flex items-center gap-1 border border-border rounded-lg overflow-hidden">
            <button
              onClick={() => setZoom((z) => Math.max(0.4, z - 0.15))}
              className="h-9 w-9 flex items-center justify-center hover:bg-accent/10 text-muted-foreground hover:text-foreground transition-colors"
            >
              <ZoomOut className="h-4 w-4" />
            </button>
            <span className="text-2xs font-bold px-2 tabular-nums">
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={() => setZoom((z) => Math.min(2, z + 0.15))}
              className="h-9 w-9 flex items-center justify-center hover:bg-accent/10 text-muted-foreground hover:text-foreground transition-colors"
            >
              <ZoomIn className="h-4 w-4" />
            </button>
            <button
              onClick={() => setZoom(1)}
              className="h-9 w-9 flex items-center justify-center hover:bg-accent/10 text-muted-foreground hover:text-foreground transition-colors border-l border-border"
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 flex-wrap">
        {(Object.entries(TYPE_COLORS) as [SubjectType, string][]).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5">
            <div className="h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-2xs font-semibold text-muted-foreground uppercase">{type}</span>
          </div>
        ))}
        <div className="flex items-center gap-1.5">
          <svg width="20" height="12">
            <defs>
              <marker id="legend-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                <path d="M0,0 L0,6 L8,3 z" fill="#6b7280" />
              </marker>
            </defs>
            <line
              x1="0" y1="6" x2="14" y2="6"
              stroke="#6b7280" strokeWidth="1.5"
              markerEnd="url(#legend-arrow)"
              strokeDasharray="3 2"
            />
          </svg>
          <span className="text-2xs font-semibold text-muted-foreground uppercase">Requires →</span>
        </div>
      </div>

      {/* Graph Canvas */}
      <Card glass className="overflow-auto" style={{ minHeight: 400 }}>
        {!selectedCurriculumId ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
            <GitMerge className="h-10 w-10 text-muted-foreground opacity-30" />
            <p className="text-sm text-muted-foreground">Select a curriculum to visualize its prerequisite graph.</p>
          </div>
        ) : loadingGraph ? (
          <div className="p-8 space-y-4">
            <Skeleton className="h-48 w-full" />
          </div>
        ) : nodes.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
            <GitMerge className="h-10 w-10 text-muted-foreground opacity-30" />
            <p className="text-sm text-muted-foreground">No subjects found in this curriculum.</p>
            <Link
              href={`/dashboard/catalog/curricula/${selectedCurriculumId}`}
              className="text-xs text-violet-400 hover:underline"
            >
              Add subjects first →
            </Link>
          </div>
        ) : (
          <div
            style={{
              transform: `scale(${zoom})`,
              transformOrigin: "top left",
              width: svgWidth * zoom,
              height: svgHeight * zoom,
            }}
          >
            <svg
              ref={svgRef}
              width={svgWidth}
              height={svgHeight}
              className="overflow-visible"
            >
              <defs>
                <marker
                  id="arrow"
                  markerWidth="10"
                  markerHeight="10"
                  refX="8"
                  refY="3"
                  orient="auto"
                >
                  <path d="M0,0 L0,6 L10,3 z" fill="#6b7280" />
                </marker>
                <marker
                  id="arrow-highlight"
                  markerWidth="10"
                  markerHeight="10"
                  refX="8"
                  refY="3"
                  orient="auto"
                >
                  <path d="M0,0 L0,6 L10,3 z" fill="#a78bfa" />
                </marker>
                <filter id="glow">
                  <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {/* Semester swimlanes */}
              {semBands.map((band, idx) => (
                <g key={band.sem}>
                  <rect
                    x={band.x}
                    y={0}
                    width={band.width}
                    height={svgHeight}
                    fill={SEMESTER_COLORS[idx % SEMESTER_COLORS.length]}
                    fillOpacity={0.03}
                    rx={8}
                  />
                  <text
                    x={band.x + band.width / 2}
                    y={18}
                    textAnchor="middle"
                    fontSize="9"
                    fontWeight="700"
                    fill={SEMESTER_COLORS[idx % SEMESTER_COLORS.length]}
                    opacity={0.7}
                    letterSpacing="1.5"
                    style={{ textTransform: "uppercase" }}
                  >
                    SEM {band.sem}
                  </text>
                </g>
              ))}

              {/* Edges (arrows) */}
              {edges.map((edge, idx) => {
                const from = posMap[edge.from];
                const to = posMap[edge.to];
                if (!from || !to) return null;

                const isHighlighted =
                  hoveredNode &&
                  (edge.from === hoveredNode || edge.to === hoveredNode);

                // Draw curve from node → prerequisite
                const x1 = from.x;
                const y1 = from.y + NODE_H / 4;
                const x2 = to.x + NODE_W / 2;
                const y2 = to.y + NODE_H / 4;
                const mx = (x1 + x2) / 2;

                return (
                  <path
                    key={idx}
                    d={`M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`}
                    stroke={isHighlighted ? "#a78bfa" : "#4b5563"}
                    strokeWidth={isHighlighted ? 2 : 1.2}
                    strokeDasharray={isHighlighted ? undefined : "4 3"}
                    fill="none"
                    markerEnd={isHighlighted ? "url(#arrow-highlight)" : "url(#arrow)"}
                    opacity={hoveredNode && !isHighlighted ? 0.2 : 0.8}
                  />
                );
              })}

              {/* Nodes */}
              {positions.map(({ x, y, node }) => {
                const nodeColor = TYPE_COLORS[node.type as SubjectType] || "#94a3b8";
                const isHovered = hoveredNode === node.id;
                const isDimmed = hoveredNode && !highlighted.has(node.id);

                return (
                  <g
                    key={node.id}
                    transform={`translate(${x - NODE_W / 2}, ${y - NODE_H / 2})`}
                    onMouseEnter={() => setHoveredNode(node.id)}
                    onMouseLeave={() => setHoveredNode(null)}
                    style={{ cursor: "pointer" }}
                    opacity={isDimmed ? 0.25 : 1}
                  >
                    {/* Node card */}
                    <rect
                      width={NODE_W}
                      height={NODE_H}
                      rx={10}
                      fill="#1a1a2e"
                      stroke={isHovered ? nodeColor : "#374151"}
                      strokeWidth={isHovered ? 2 : 1}
                      filter={isHovered ? "url(#glow)" : undefined}
                    />
                    {/* Color bar */}
                    <rect
                      x={0}
                      y={0}
                      width={4}
                      height={NODE_H}
                      rx={10}
                      fill={nodeColor}
                      opacity={0.9}
                    />
                    {/* Code */}
                    <text
                      x={14}
                      y={20}
                      fontSize="9"
                      fontWeight="700"
                      fill={nodeColor}
                      letterSpacing="0.5"
                      fontFamily="monospace"
                    >
                      {node.code}
                    </text>
                    {/* Name (truncated) */}
                    <text x={14} y={36} fontSize="8.5" fill="#d1d5db" fontWeight="500">
                      {node.name.length > 16 ? node.name.slice(0, 15) + "…" : node.name}
                    </text>
                    {/* Credits */}
                    <text x={14} y={50} fontSize="8" fill="#6b7280">
                      {node.credits} credits
                    </text>
                    {/* Elective badge */}
                    {node.isElective && (
                      <rect
                        x={NODE_W - 28}
                        y={6}
                        width={22}
                        height={12}
                        rx={4}
                        fill="#7c3aed"
                        fillOpacity={0.3}
                      />
                    )}
                    {node.isElective && (
                      <text x={NODE_W - 17} y={15} fontSize="7" fill="#a78bfa" textAnchor="middle">
                        OE
                      </text>
                    )}
                  </g>
                );
              })}
            </svg>
          </div>
        )}
      </Card>

      {/* Info Banner */}
      <div className="flex items-start gap-2.5 p-3.5 rounded-lg border border-violet-500/20 bg-violet-500/5">
        <Info className="h-4 w-4 text-violet-400 flex-shrink-0 mt-0.5" />
        <p className="text-2xs text-muted-foreground leading-relaxed">
          Arrows indicate prerequisites — an arrow from <strong>CS301 → CS101</strong> means CS301
          requires CS101. Hover a node to highlight its direct connections. The catalog engine
          enforces that no circular prerequisites exist using DFS cycle detection.
        </p>
      </div>
    </div>
  );
}
