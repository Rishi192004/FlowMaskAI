import React, { useState } from 'react';
import { ProcessMapEdge, ProcessMapNode } from '../../types/api';

interface ProcessMapCanvasProps {
  nodes: ProcessMapNode[];
  edges: ProcessMapEdge[];
  onSelectNode?: (node: ProcessMapNode) => void;
}

export const ProcessMapCanvas: React.FC<ProcessMapCanvasProps> = ({
  nodes,
  edges,
  onSelectNode,
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Layout node positions dynamically in a staged pipeline column layout
  const nodeMap = new Map<string, ProcessMapNode>();
  nodes.forEach(n => nodeMap.set(n.id, n));

  // Determine stage levels by tracing DFG
  const levels: Record<string, number> = {};
  nodes.forEach(n => {
    if (n.is_start) {
      levels[n.id] = 0;
    }
  });

  // Iteratively assign levels
  for (let pass = 0; pass < 5; pass++) {
    edges.forEach(e => {
      const srcLvl = levels[e.source] ?? 0;
      const tgtLvl = levels[e.target] ?? (srcLvl + 1);
      if (srcLvl + 1 > tgtLvl) {
        levels[e.target] = srcLvl + 1;
      }
    });
  }

  // Ensure end nodes have highest level
  const maxLvl = Math.max(...Object.values(levels), 1);
  nodes.forEach(n => {
    if (n.is_end && (levels[n.id] ?? 0) < maxLvl) {
      levels[n.id] = maxLvl + 1;
    }
  });

  // Group nodes by level
  const columnGroups: Record<number, ProcessMapNode[]> = {};
  nodes.forEach(n => {
    const lvl = levels[n.id] ?? 1;
    if (!columnGroups[lvl]) {
      columnGroups[lvl] = [];
    }
    columnGroups[lvl].push(n);
  });

  const sortedLevels = Object.keys(columnGroups)
    .map(Number)
    .sort((a, b) => a - b);

  // Compute (x, y) coordinates for each node
  const nodeCoords = new Map<string, { x: number; y: number }>();
  const colWidth = 240;
  const rowHeight = 140;

  sortedLevels.forEach((lvl, colIdx) => {
    const colNodes = columnGroups[lvl];
    colNodes.forEach((n, rowIdx) => {
      const x = 80 + colIdx * colWidth;
      const y = 80 + rowIdx * rowHeight;
      nodeCoords.set(n.id, { x, y });
    });
  });

  const svgWidth = Math.max(900, (sortedLevels.length + 1) * colWidth);
  const maxNodesInCol = Math.max(...Object.values(columnGroups).map(g => g.length), 1);
  const svgHeight = Math.max(450, (maxNodesInCol + 1) * rowHeight);

  return (
    <div className="relative w-full overflow-x-auto bg-[#080C15] border border-surface-border rounded-xl p-4">
      <div className="absolute top-4 right-4 z-10 flex gap-4 text-xs font-mono text-slate-400 bg-surface/80 backdrop-blur px-3 py-1.5 rounded-lg border border-surface-border">
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Start
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500" /> Standard
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> Bottleneck
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-purple-500" /> End
        </span>
      </div>

      <svg width={svgWidth} height={svgHeight} className="overflow-visible">
        <defs>
          <marker
            id="arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#475569" />
          </marker>
          <marker
            id="arrow-bottleneck"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#F43F5E" />
          </marker>
        </defs>

        {/* Draw Edges */}
        {edges.map(e => {
          const src = nodeCoords.get(e.source);
          const tgt = nodeCoords.get(e.target);
          if (!src || !tgt) return null;

          const isSelf = e.source === e.target;
          let pathD = '';
          let labelX = 0;
          let labelY = 0;

          if (isSelf) {
            // Self-loop (rework loop)
            pathD = `M ${src.x + 80} ${src.y} C ${src.x + 80} ${src.y - 60}, ${src.x + 140} ${src.y - 60}, ${src.x + 140} ${src.y + 20} C ${src.x + 140} ${src.y + 60}, ${src.x + 80} ${src.y + 60}, ${src.x + 80} ${src.y + 40}`;
            labelX = src.x + 150;
            labelY = src.y;
          } else {
            const startX = src.x + 160;
            const startY = src.y + 35;
            const endX = tgt.x;
            const endY = tgt.y + 35;
            const dx = endX - startX;
            pathD = `M ${startX} ${startY} C ${startX + dx * 0.5} ${startY}, ${endX - dx * 0.5} ${endY}, ${endX} ${endY}`;
            labelX = (startX + endX) / 2;
            labelY = (startY + endY) / 2 - 10;
          }

          const strokeColor = e.is_bottleneck ? '#F43F5E' : '#334155';
          const markerId = e.is_bottleneck ? 'url(#arrow-bottleneck)' : 'url(#arrow)';

          return (
            <g key={e.id} className="transition-all hover:opacity-100 opacity-80">
              <path
                d={pathD}
                fill="none"
                stroke={strokeColor}
                strokeWidth={Math.min(4, Math.max(1.5, Math.log10(e.frequency + 1) * 2))}
                markerEnd={markerId}
              />
              <text
                x={labelX}
                y={labelY}
                fill={e.is_bottleneck ? '#FDA4AF' : '#94A3B8'}
                fontSize="10"
                fontFamily="JetBrains Mono"
                textAnchor="middle"
                className="select-none bg-surface"
              >
                {e.frequency}x ({e.avg_duration_hours}h)
              </text>
            </g>
          );
        })}

        {/* Draw Nodes */}
        {nodes.map(n => {
          const coords = nodeCoords.get(n.id);
          if (!coords) return null;

          const isSelected = selectedNodeId === n.id;
          let borderColor = 'border-slate-700';
          let badgeBg = 'bg-blue-500/20 text-blue-300';

          if (n.is_start) {
            borderColor = 'stroke-emerald-500';
            badgeBg = 'bg-emerald-500/20 text-emerald-300';
          } else if (n.is_end) {
            borderColor = 'stroke-purple-500';
            badgeBg = 'bg-purple-500/20 text-purple-300';
          } else if (n.is_bottleneck) {
            borderColor = 'stroke-rose-500';
            badgeBg = 'bg-rose-500/20 text-rose-300';
          } else {
            borderColor = 'stroke-slate-600';
          }

          return (
            <g
              key={n.id}
              transform={`translate(${coords.x}, ${coords.y})`}
              onClick={() => {
                setSelectedNodeId(n.id);
                if (onSelectNode) onSelectNode(n);
              }}
              className="cursor-pointer group"
            >
              {/* Card Container */}
              <rect
                width="160"
                height="70"
                rx="8"
                fill="#151D30"
                stroke={isSelected ? '#3B82F6' : (n.is_bottleneck ? '#F43F5E' : '#1E293B')}
                strokeWidth={isSelected ? '2.5' : '1.5'}
                className="group-hover:stroke-blue-400 transition-colors shadow-lg"
              />

              {/* Status Indicator Bar */}
              <rect
                x="0"
                y="0"
                width="4"
                height="70"
                rx="2"
                fill={n.is_start ? '#10B981' : n.is_end ? '#A855F7' : n.is_bottleneck ? '#F43F5E' : '#3B82F6'}
              />

              {/* Activity Label */}
              <text
                x="14"
                y="24"
                fill="#F8FAFC"
                fontSize="11"
                fontWeight="600"
                className="select-none font-sans"
              >
                {n.label.length > 20 ? n.label.slice(0, 18) + '...' : n.label}
              </text>

              {/* Frequency */}
              <text
                x="14"
                y="46"
                fill="#94A3B8"
                fontSize="10"
                fontFamily="JetBrains Mono"
                className="select-none"
              >
                Volume: <tspan fill="#E2E8F0" fontWeight="600">{n.frequency.toLocaleString()}</tspan>
              </text>

              {/* Duration */}
              <text
                x="14"
                y="60"
                fill="#94A3B8"
                fontSize="10"
                fontFamily="JetBrains Mono"
                className="select-none"
              >
                Avg Wait: <tspan fill={n.is_bottleneck ? '#F43F5E' : '#E2E8F0'} fontWeight="600">{n.avg_duration_hours}h</tspan>
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};
