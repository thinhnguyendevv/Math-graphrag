import React, { useEffect, useRef, useState } from "react";
import { EntityNode, RelationshipLink } from "../types";
import { Network, ZoomIn, ZoomOut, Zap, Info, Eye } from "lucide-react";

interface GraphVisualizerProps {
  nodes: EntityNode[];
  links: RelationshipLink[];
  onSelectNode?: (node: EntityNode) => void;
}

export default function GraphVisualizer({ nodes, links, onSelectNode }: GraphVisualizerProps) {
  const [activeNodes, setActiveNodes] = useState<EntityNode[]>([]);
  const [selectedNode, setSelectedNode] = useState<EntityNode | null>(null);
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [highlightedNodeIds, setHighlightedNodeIds] = useState<Set<string>>(new Set());

  const containerRef = useRef<HTMLDivElement>(null);
  const isDraggingRef = useRef<boolean>(false);
  const dragStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const dragNodeRef = useRef<EntityNode | null>(null);

  // Initialize nodes positions in a beautiful circular pattern with a random drift
  useEffect(() => {
    if (nodes.length === 0) return;

    const width = containerRef.current?.clientWidth || 500;
    const height = containerRef.current?.clientHeight || 450;
    const centerX = width / 2;
    const centerY = height / 2;

    const initialized = nodes.map((node, i) => {
      const angle = (i / nodes.length) * Math.PI * 2;
      const radius = Math.min(centerX, centerY) * 0.6 * (0.8 + Math.random() * 0.4);
      return {
        ...node,
        x: node.x !== undefined ? node.x : centerX + Math.cos(angle) * radius,
        y: node.y !== undefined ? node.y : centerY + Math.sin(angle) * radius,
        vx: 0,
        vy: 0,
      };
    });

    setActiveNodes(initialized);
  }, [nodes]);

  // Small internal force physics engine simulation
  useEffect(() => {
    if (activeNodes.length === 0) return;

    let animFrameId: number;
    const width = containerRef.current?.clientWidth || 500;
    const height = containerRef.current?.clientHeight || 450;
    const centerX = width / 2;
    const centerY = height / 2;

    const runPhysics = () => {
      setActiveNodes((prev) => {
        const next = prev.map((n) => ({ ...n }));

        // 1. Repulsion force between all nodes (prevent overlap)
        for (let i = 0; i < next.length; i++) {
          for (let j = i + 1; j < next.length; j++) {
            const n1 = next[i];
            const n2 = next[j];
            const dx = (n2.x || 0) - (n1.x || 0);
            const dy = (n2.y || 0) - (n1.y || 0);
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;

            const minDist = 110; // desired distance between nodes
            if (dist < minDist) {
              const force = (minDist - dist) / dist * 0.18;
              const fx = dx * force;
              const fy = dy * force;

              if (n1 !== dragNodeRef.current) {
                n1.vx = (n1.vx || 0) - fx;
                n1.vy = (n1.vy || 0) - fy;
              }
              if (n2 !== dragNodeRef.current) {
                n2.vx = (n2.vx || 0) + fx;
                n2.vy = (n2.vy || 0) + fy;
              }
            }
          }
        }

        // 2. Attraction force from links (relationships pull nodes together)
        links.forEach((link) => {
          // Find source and target nodes
          const sNode = next.find(
            (n) =>
              n.label.toLowerCase() === link.source.toLowerCase() ||
              n.id === link.source.toLowerCase()
          );
          const tNode = next.find(
            (n) =>
              n.label.toLowerCase() === link.target.toLowerCase() ||
              n.id === link.target.toLowerCase()
          );

          if (sNode && tNode) {
            const dx = (tNode.x || 0) - (sNode.x || 0);
            const dy = (tNode.y || 0) - (sNode.y || 0);
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const desiredLinkLength = 150;

            if (dist > desiredLinkLength) {
              const force = (dist - desiredLinkLength) / dist * 0.045;
              const fx = dx * force;
              const fy = dy * force;

              if (sNode !== dragNodeRef.current) {
                sNode.vx = (sNode.vx || 0) + fx;
                sNode.vy = (sNode.vy || 0) + fy;
              }
              if (tNode !== dragNodeRef.current) {
                tNode.vx = (tNode.vx || 0) - fx;
                tNode.vy = (tNode.vy || 0) - fy;
              }
            }
          }
        });

        // 3. Gravity pulling towards center
        next.forEach((n) => {
          if (n === dragNodeRef.current) return;
          const dx = centerX - (n.x || 0);
          const dy = centerY - (n.y || 0);
          n.vx = (n.vx || 0) + dx * 0.008;
          n.vy = (n.vy || 0) + dy * 0.008;
        });

        // 4. Update coordinates with resistance friction
        next.forEach((n) => {
          if (n === dragNodeRef.current) return;
          n.x = (n.x || 0) + (n.vx || 0);
          n.y = (n.y || 0) + (n.vy || 0);

          // Friction damping
          n.vx = (n.vx || 0) * 0.85;
          n.vy = (n.vy || 0) * 0.85;

          // Boundary constraint
          n.x = Math.max(30, Math.min(width - 30, n.x));
          n.y = Math.max(30, Math.min(height - 30, n.y));
        });

        return next;
      });

      animFrameId = requestAnimationFrame(runPhysics);
    };

    animFrameId = requestAnimationFrame(runPhysics);
    return () => cancelAnimationFrame(animFrameId);
  }, [activeNodes.length, links]);

  // Node coloring depending on their Entity Type
  const getNodeColor = (type: string) => {
    const t = type.toLowerCase();
    if (t.includes("tech") || t.includes("công nghệ")) return { bg: "#0969da", border: "#54aeff", fill: "#ddf4ff" };
    if (t.includes("concept") || t.includes("khái niệm") || t.includes("lý thuyết")) return { bg: "#8250df", border: "#c297ff", fill: "#f5f0ff" };
    if (t.includes("person") || t.includes("nhân vật") || t.includes("người")) return { bg: "#1a7f37", border: "#49e374", fill: "#eefcf1" };
    if (t.includes("organ") || t.includes("tổ chức") || t.includes("công ty")) return { bg: "#bf360c", border: "#ff8a65", fill: "#ffebe6" };
    if (t.includes("process") || t.includes("quy trình") || t.includes("phương pháp")) return { bg: "#9a6700", border: "#ffd33d", fill: "#fffbeb" };
    return { bg: "#656d76", border: "#afb8c1", fill: "#f6f8fa" };
  };

  const handleNodeClick = (node: EntityNode, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedNode(node);
    if (onSelectNode) onSelectNode(node);

    // Dynamic highlighting of neighboring nodes
    const neighbors = new Set<string>([node.id]);
    links.forEach((link) => {
      const srcMatch = link.source.toLowerCase() === node.label.toLowerCase() || link.source.toLowerCase() === node.id;
      const tgtMatch = link.target.toLowerCase() === node.label.toLowerCase() || link.target.toLowerCase() === node.id;

      if (srcMatch || tgtMatch) {
        // Find partner node ID
        const partnerLabel = srcMatch ? link.target : link.source;
        const partnerNode = activeNodes.find(
          (an) => an.label.toLowerCase() === partnerLabel.toLowerCase() || an.id === partnerLabel.toLowerCase()
        );
        if (partnerNode) {
          neighbors.add(partnerNode.id);
        }
      }
    });

    setHighlightedNodeIds(neighbors);
  };

  const handleSvgBgClick = () => {
    setSelectedNode(null);
    setHighlightedNodeIds(new Set());
  };

  // Node Drag Handlers
  const handleNodeMouseDown = (node: EntityNode, e: React.MouseEvent) => {
    e.stopPropagation();
    isDraggingRef.current = true;
    dragNodeRef.current = node;
    dragStartRef.current = { x: e.clientX, y: e.clientY };
  };

  const handleSvgMouseMove = (e: React.MouseEvent) => {
    if (!isDraggingRef.current || !dragNodeRef.current) return;

    const width = containerRef.current?.clientWidth || 500;
    const height = containerRef.current?.clientHeight || 450;
    const rect = containerRef.current?.getBoundingClientRect();

    if (!rect) return;

    // Relative calculation within container zoom boundary
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    setActiveNodes((prev) =>
      prev.map((n) => {
        if (n.id === dragNodeRef.current?.id) {
          return {
            ...n,
            x: mouseX,
            y: mouseY,
            vx: 0,
            vy: 0,
          };
        }
        return n;
      })
    );
  };

  const handleSvgMouseUpOrLeave = () => {
    isDraggingRef.current = false;
    dragNodeRef.current = null;
  };

  return (
    <div className="relative w-full h-full flex flex-col bg-slate-50 rounded-xl overflow-hidden border border-slate-200">
      <div className="p-3 border-b border-slate-200 bg-white flex justify-between items-center">
        <div className="flex items-center gap-2">
          <Network className="w-5 h-5 text-indigo-600" />
          <h3 className="font-semibold text-sm text-slate-800">Bản Đồ Tri Thức Động (Interactive Graph)</h3>
        </div>
        <div className="flex items-center gap-1.5 bg-slate-100 rounded-lg p-1">
          <button
            onClick={() => setZoom((prev) => Math.min(2, prev + 0.15))}
            className="p-1 hover:bg-white rounded transition text-slate-500"
            title="Phóng to"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom((prev) => Math.max(0.5, prev - 0.15))}
            className="p-1 hover:bg-white rounded transition text-slate-500"
            title="Thu nhỏ"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              setZoom(1);
              setPan({ x: 0, y: 0 });
            }}
            className="px-1.5 py-0.5 hover:bg-white rounded text-[10px] transition text-slate-500 font-mono"
            title="Reset view"
          >
            Reset
          </button>
        </div>
      </div>

      <div
        id="graphCanvasContainer"
        ref={containerRef}
        className="relative flex-1 w-full bg-slate-50 cursor-grab active:cursor-grabbing overflow-hidden"
        onMouseMove={handleSvgMouseMove}
        onMouseUp={handleSvgMouseUpOrLeave}
        onMouseLeave={handleSvgMouseUpOrLeave}
        onClick={handleSvgBgClick}
      >
        {activeNodes.length === 0 ? (
          <div className="absolute inset-0 flex flex-col justify-center items-center text-slate-500 gap-2 p-4 text-center">
            <Network className="w-10 h-10 text-slate-500 stroke-1 animate-pulse" />
            <p className="text-xs">Đồ thị chưa có dữ liệu</p>
            <p className="text-[11px] max-w-[220px] text-slate-500">
              Hãy dán văn bản hoặc tải tài liệu bên sidebar để LLM trích xuất các đỉnh (Nodes) và cung (Relationships).
            </p>
          </div>
        ) : (
          <svg className="w-full h-full select-none">
            <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
              {/* Relationship Links */}
              {links.map((link, idx) => {
                const sNode = activeNodes.find(
                  (an) =>
                    an.label.toLowerCase() === link.source.toLowerCase() ||
                    an.id === link.source.toLowerCase()
                );
                const tNode = activeNodes.find(
                  (an) =>
                    an.label.toLowerCase() === link.target.toLowerCase() ||
                    an.id === link.target.toLowerCase()
                );

                if (!sNode || !tNode) return null;

                const isHighlighted =
                  highlightedNodeIds.size === 0 ||
                  (highlightedNodeIds.has(sNode.id) && highlightedNodeIds.has(tNode.id));

                return (
                  <g key={`link-${idx}`} className="transition-opacity duration-300">
                    {/* Link line */}
                    <line
                      x1={sNode.x}
                      y1={sNode.y}
                      x2={tNode.x}
                      y2={tNode.y}
                      stroke={isHighlighted ? "#818cf8" : "#334155"}
                      strokeWidth={isHighlighted ? 2.5 : 1.2}
                      strokeDasharray={isHighlighted ? "" : "3,3"}
                      opacity={isHighlighted ? 0.9 : 0.25}
                    />
                    {/* Tiny relationship label text in center */}
                    <rect
                      x={((sNode.x || 0) + (tNode.x || 0)) / 2 - 35}
                      y={((sNode.y || 0) + (tNode.y || 0)) / 2 - 7}
                      width={70}
                      height={14}
                      rx={3}
                      fill="#0f172a"
                      opacity={isHighlighted ? 0.8 : 0.15}
                    />
                    <text
                      x={((sNode.x || 0) + (tNode.x || 0)) / 2}
                      y={((sNode.y || 0) + (tNode.y || 0)) / 2 + 3}
                      textAnchor="middle"
                      fill={isHighlighted ? "#c7d2fe" : "#475569"}
                      fontSize="7.5"
                      fontFamily="monospace"
                      opacity={isHighlighted ? 0.95 : 0.2}
                    >
                      {link.relationship.length > 12
                        ? `${link.relationship.substring(0, 10)}..`
                        : link.relationship}
                    </text>
                  </g>
                );
              })}

              {/* Entity Nodes */}
              {activeNodes.map((node) => {
                const colors = getNodeColor(node.type);
                const isSelected = selectedNode?.id === node.id;
                const isHighlighted = highlightedNodeIds.size === 0 || highlightedNodeIds.has(node.id);

                return (
                  <g
                    key={node.id}
                    transform={`translate(${node.x}, ${node.y})`}
                    className="cursor-pointer transition-all duration-200"
                    onClick={(e) => handleNodeClick(node, e)}
                    onMouseDown={(e) => handleNodeMouseDown(node, e)}
                  >
                    {/* Glow container */}
                    <circle
                      r={isSelected ? 26 : 21}
                      fill={colors.bg}
                      opacity={isSelected ? 0.35 : isHighlighted ? 0.15 : 0.05}
                      className="animate-pulse"
                    />

                    {/* Outer border ring */}
                    <circle
                      r={18}
                      fill={colors.bg}
                      stroke={isSelected ? "#ffffff" : colors.border}
                      strokeWidth={isSelected ? 3 : 1.5}
                      opacity={isHighlighted ? 1 : 0.3}
                    />

                    {/* Tiny type abbreviation inside node center */}
                    <text
                      y={4}
                      textAnchor="middle"
                      fill="#ffffff"
                      fontSize="9"
                      fontWeight="bold"
                      opacity={isHighlighted ? 1 : 0.4}
                      className="pointer-events-none uppercase"
                    >
                      {node.type ? node.type.substring(0, 2) : "EN"}
                    </text>

                    {/* Label name */}
                    <rect
                      y={26}
                      x={-45}
                      width={90}
                      height={16}
                      rx={4}
                      fill="#1e293b"
                      stroke={isSelected ? "#818cf8" : "#334155"}
                      strokeWidth={1}
                      opacity={isHighlighted ? 0.95 : 0.3}
                    />
                    <text
                      y={37}
                      textAnchor="middle"
                      fill={isSelected ? "#a5b4fc" : isHighlighted ? "#e2e8f0" : "#64748b"}
                      fontSize="8.5"
                      fontWeight={isSelected ? "semibold" : "normal"}
                      className="pointer-events-none"
                    >
                      {node.label.length > 14 ? `${node.label.substring(0, 12)}..` : node.label}
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>
        )}

        {/* Selected Entity Details Overlay Card inside Graph */}
        {selectedNode && (
          <div
            id="gDetailsOverlay"
            className="absolute bottom-3 left-3 right-3 md:left-4 md:right-4 bg-white/95 border border-slate-200 text-slate-800 p-3.5 rounded-xl text-xs backdrop-blur shadow-2xl animate-slide-up"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-start gap-1 mb-1.5">
              <div>
                <span className="px-2 py-0.5 rounded-md font-mono text-[9px] bg-indigo-50 text-indigo-700 border border-indigo-200 mr-2 uppercase">
                  {selectedNode.type || "Khái niệm"}
                </span>
                <strong className="text-sm text-slate-900 font-semibold">{selectedNode.label}</strong>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-slate-500 hover:text-slate-900 px-1 ml-2 font-mono text-xs"
              >
                ✕
              </button>
            </div>
            <p className="text-[11px] leading-relaxed text-slate-700">{selectedNode.description}</p>
          </div>
        )}
      </div>

      {nodes.length > 0 && (
        <div className="p-2.5 bg-slate-50 border-t border-slate-200 flex flex-wrap gap-2 text-[10px] text-slate-500 justify-center">
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-600"></span> Công nghệ (TE)
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-purple-600"></span> Khái niệm (LE)
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-600"></span> Nhân vật (PE)
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-600"></span> Quy trình (PR)
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-orange-700"></span> Tổ chức (OR)
          </div>
        </div>
      )}
    </div>
  );
}
