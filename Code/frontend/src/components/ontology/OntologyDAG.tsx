"use client"

import { useCallback, useMemo, useState, useEffect } from "react"
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  Panel,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  MarkerType,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import { ChevronDown, ChevronRight, Maximize2, Minimize2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

import { cn } from "@/lib/utils"

// Threshold for auto-grouping children
const GROUP_THRESHOLD = 15

interface OntologyNode {
  name: string
  label: string | null
  comment: string | null
  children: string[]
  depth: number
  has_more?: boolean // For lazy loading: indicates unloaded children
}

interface OntologyDAGProps {
  nodes: Record<string, OntologyNode>
  root: string
  selectedNode: string | null
  onNodeSelect: (nodeId: string) => void
  onNodeToggle?: (nodeId: string) => void
  highlightedPath?: string[]
  expandedNodes?: Set<string>
}

// Custom node data type
interface OntologyNodeData {
  label: string
  isSelected: boolean
  isHighlighted: boolean
  isExpanded: boolean
  childCount: number
  hasChildren: boolean
  depth: number
  isGroup?: boolean
  onToggle: () => void
}

// Get group key for a node label
function getGroupKey(label: string): string {
  if (!label) return "#"
  const firstChar = label.charAt(0).toUpperCase()
  if (/[0-9]/.test(firstChar)) return "0-9"
  if (/[A-Z]/.test(firstChar)) return firstChar
  return "#"
}

// Group children by first letter
function groupChildren(
  childIds: string[],
  nodes: Record<string, OntologyNode>
): Map<string, string[]> {
  const groups = new Map<string, string[]>()

  childIds.forEach((childId) => {
    const child = nodes[childId]
    if (!child) return
    const label = child.label || child.name
    const key = getGroupKey(label)

    if (!groups.has(key)) {
      groups.set(key, [])
    }
    groups.get(key)!.push(childId)
  })

  // Sort groups: # first, then 0-9, then A-Z
  const sortedGroups = new Map<string, string[]>()
  const keys = Array.from(groups.keys()).sort((a, b) => {
    if (a === "#") return -1
    if (b === "#") return 1
    if (a === "0-9") return -1
    if (b === "0-9") return 1
    return a.localeCompare(b)
  })

  keys.forEach((key) => {
    sortedGroups.set(key, groups.get(key)!)
  })

  return sortedGroups
}

// Custom node component with expand/collapse
function OntologyNodeComponent({ data }: { data: OntologyNodeData }) {
  const handleExpandClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    data.onToggle()
  }

  return (
    <div
      className={cn(
        "px-3 py-2 rounded-lg border-2 shadow-sm transition-all min-w-[120px] text-center relative",
        data.isGroup
          ? "bg-muted/50 border-dashed border-muted-foreground/50 hover:border-muted-foreground"
          : data.isSelected
            ? "bg-primary text-primary-foreground border-primary"
            : data.isHighlighted
              ? "bg-primary/20 border-primary/50"
              : "bg-background border-border hover:border-primary/50"
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-primary" />
      <div className="flex items-center justify-center gap-1">
        <span className={cn(
          "text-sm font-medium truncate max-w-[150px]",
          data.isGroup && "text-muted-foreground"
        )}>
          {data.label}
        </span>
        {data.hasChildren && (
          <button
            onClick={handleExpandClick}
            className={cn(
              "p-0.5 rounded hover:bg-black/10 transition-colors flex items-center",
              data.isSelected && "hover:bg-white/20"
            )}
            title={data.isExpanded ? "Collapse" : `Expand (${data.childCount})`}
          >
            {data.isExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
            {!data.isExpanded && data.childCount > 0 && (
              <span className="text-xs opacity-70">+{data.childCount}</span>
            )}
          </button>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-primary" />
    </div>
  )
}

const nodeTypes = {
  ontology: OntologyNodeComponent,
}

// Helper to create group node ID
const makeGroupId = (parentId: string, groupKey: string) =>
  `__group__${parentId}__${groupKey}`

// Check if an ID is a group node
const isGroupId = (id: string) => id.startsWith("__group__")

export function OntologyDAG({
  nodes: ontologyNodes,
  root,
  selectedNode,
  onNodeSelect,
  highlightedPath = [],
}: OntologyDAGProps) {
  // Track which nodes are expanded (show their children)
  // Initially only root is expanded
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(() => new Set([root]))

  // Precompute which nodes need grouping and their groups
  const groupingInfo = useMemo(() => {
    const needsGrouping = new Map<string, Map<string, string[]>>()

    Object.entries(ontologyNodes).forEach(([nodeId, node]) => {
      if (node.children.length > GROUP_THRESHOLD) {
        const groups = groupChildren(node.children, ontologyNodes)
        needsGrouping.set(nodeId, groups)
      }
    })

    return needsGrouping
  }, [ontologyNodes])

  // Reset expanded nodes when root changes
  useEffect(() => {
    // Intentional: reset expansion when root changes to avoid stale open branches
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setExpandedNodes(new Set([root]))
  }, [root])

  // Toggle node expansion
  const toggleNode = useCallback((nodeId: string) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev)
      if (next.has(nodeId)) {
        next.delete(nodeId)
      } else {
        next.add(nodeId)
      }
      return next
    })
  }, [])

  // Expand all nodes up to a certain depth
  const expandToDepth = useCallback(
    (maxDepth: number) => {
      const toExpand = new Set<string>()
      Object.entries(ontologyNodes).forEach(([url, node]) => {
        if (node.depth < maxDepth && node.children.length > 0) {
          toExpand.add(url)
        }
      })
      setExpandedNodes(toExpand)
    },
    [ontologyNodes]
  )

  // Expand all nodes
  const expandAll = useCallback(() => {
    const allWithChildren = new Set<string>()
    Object.entries(ontologyNodes).forEach(([url, node]) => {
      if (node.children.length > 0) {
        allWithChildren.add(url)
      }
    })
    setExpandedNodes(allWithChildren)
  }, [ontologyNodes])

  // Collapse all (only show root's children)
  const collapseAll = useCallback(() => {
    setExpandedNodes(new Set([root]))
  }, [root])

  // Calculate max depth for the dropdown
  const maxDepth = useMemo(() => {
    let max = 0
    Object.values(ontologyNodes).forEach((node) => {
      if (node.depth > max) max = node.depth
    })
    return max
  }, [ontologyNodes])

  // Calculate which nodes (and group nodes) are visible based on expansion state
  const { visibleNodes, visibleGroups } = useMemo(() => {
    const visible = new Set<string>()
    const groups = new Map<string, { parentId: string; groupKey: string; children: string[] }>()
    const queue: string[] = [root]

    while (queue.length > 0) {
      const nodeId = queue.shift()!
      if (visible.has(nodeId)) continue
      visible.add(nodeId)

      const node = ontologyNodes[nodeId]
      if (!node) continue

      // Only add children if this node is expanded
      if (expandedNodes.has(nodeId)) {
        const nodeGroups = groupingInfo.get(nodeId)

        if (nodeGroups) {
          // This node needs grouping - add group nodes instead of direct children
          nodeGroups.forEach((childIds, groupKey) => {
            const groupId = makeGroupId(nodeId, groupKey)
            groups.set(groupId, { parentId: nodeId, groupKey, children: childIds })

            // If group is expanded, add its children
            if (expandedNodes.has(groupId)) {
              childIds.forEach((childId) => {
                if (!visible.has(childId)) {
                  queue.push(childId)
                }
              })
            }
          })
        } else {
          // No grouping needed - add children directly
          node.children.forEach((child) => {
            if (!visible.has(child)) {
              queue.push(child)
            }
          })
        }
      }
    }

    return { visibleNodes: visible, visibleGroups: groups }
  }, [ontologyNodes, root, expandedNodes, groupingInfo])

  // Convert ontology data to React Flow nodes and edges
  const { flowNodes, flowEdges } = useMemo(() => {
    const nodes: Node[] = []
    const edges: Edge[] = []

    // Subtree layout algorithm
    const nodePositions: Record<string, { x: number; y: number }> = {}
    const nodeWidth = 160
    const horizontalGap = 40
    const verticalSpacing = 100

    // Get effective children for a node (either groups or direct children)
    const getEffectiveChildren = (nodeId: string): string[] => {
      if (!expandedNodes.has(nodeId)) return []

      const nodeGroups = groupingInfo.get(nodeId)
      if (nodeGroups) {
        // Return group IDs
        return Array.from(nodeGroups.keys()).map((key) => makeGroupId(nodeId, key))
      }

      const node = ontologyNodes[nodeId]
      if (!node) return []
      return node.children.filter((c) => visibleNodes.has(c))
    }

    // Get children for a group node
    const getGroupChildren = (groupId: string): string[] => {
      const group = visibleGroups.get(groupId)
      if (!group || !expandedNodes.has(groupId)) return []
      return group.children.filter((c) => visibleNodes.has(c))
    }

    // Calculate the width of each subtree (memoized)
    const subtreeWidths: Record<string, number> = {}

    const getSubtreeWidth = (nodeId: string): number => {
      if (subtreeWidths[nodeId] !== undefined) {
        return subtreeWidths[nodeId]
      }

      // Handle group nodes
      if (isGroupId(nodeId)) {
        const group = visibleGroups.get(nodeId)
        if (!group) {
          subtreeWidths[nodeId] = nodeWidth
          return nodeWidth
        }

        if (!expandedNodes.has(nodeId)) {
          subtreeWidths[nodeId] = nodeWidth
          return nodeWidth
        }

        const visibleChildren = group.children.filter((c) => visibleNodes.has(c))
        if (visibleChildren.length === 0) {
          subtreeWidths[nodeId] = nodeWidth
          return nodeWidth
        }

        const childrenWidth =
          visibleChildren.reduce((sum, childId) => sum + getSubtreeWidth(childId), 0) +
          (visibleChildren.length - 1) * horizontalGap

        subtreeWidths[nodeId] = Math.max(nodeWidth, childrenWidth)
        return subtreeWidths[nodeId]
      }

      // Handle regular nodes
      const node = ontologyNodes[nodeId]
      if (!node || !visibleNodes.has(nodeId)) {
        subtreeWidths[nodeId] = 0
        return 0
      }

      if (!expandedNodes.has(nodeId) || node.children.length === 0) {
        subtreeWidths[nodeId] = nodeWidth
        return nodeWidth
      }

      const effectiveChildren = getEffectiveChildren(nodeId)
      if (effectiveChildren.length === 0) {
        subtreeWidths[nodeId] = nodeWidth
        return nodeWidth
      }

      const childrenWidth =
        effectiveChildren.reduce((sum, childId) => sum + getSubtreeWidth(childId), 0) +
        (effectiveChildren.length - 1) * horizontalGap

      subtreeWidths[nodeId] = Math.max(nodeWidth, childrenWidth)
      return subtreeWidths[nodeId]
    }

    // Position nodes recursively
    const positionSubtree = (nodeId: string, x: number, y: number, parentDepth: number) => {
      const subtreeWidth = getSubtreeWidth(nodeId)
      nodePositions[nodeId] = { x: x + subtreeWidth / 2, y }

      // Handle group nodes
      if (isGroupId(nodeId)) {
        const visibleChildren = getGroupChildren(nodeId)
        if (visibleChildren.length > 0) {
          let childX = x
          visibleChildren.forEach((childId) => {
            const childWidth = getSubtreeWidth(childId)
            const childNode = ontologyNodes[childId]
            positionSubtree(childId, childX, y + verticalSpacing, childNode?.depth ?? parentDepth + 1)
            childX += childWidth + horizontalGap
          })
        }
        return
      }

      // Handle regular nodes
      const effectiveChildren = getEffectiveChildren(nodeId)
      if (effectiveChildren.length > 0) {
        let childX = x
        effectiveChildren.forEach((childId) => {
          const childWidth = getSubtreeWidth(childId)
          const childNode = ontologyNodes[childId]
          positionSubtree(childId, childX, y + verticalSpacing, childNode?.depth ?? parentDepth + 1)
          childX += childWidth + horizontalGap
        })
      }
    }

    // Start layout from root
    const rootWidth = getSubtreeWidth(root)
    positionSubtree(root, -rootWidth / 2, 0, 0)

    // Create React Flow nodes for visible regular nodes
    Object.entries(ontologyNodes)
      .filter(([url]) => visibleNodes.has(url))
      .forEach(([url, node]) => {
        const pos = nodePositions[url] || { x: 0, y: 0 }
        const nodeGroups = groupingInfo.get(url)
        const effectiveChildCount = nodeGroups ? nodeGroups.size : node.children.length
        const isExpanded = expandedNodes.has(url)

        nodes.push({
          id: url,
          type: "ontology",
          position: pos,
          data: {
            label: node.label || node.name,
            isSelected: url === selectedNode,
            isHighlighted: highlightedPath.includes(url),
            isExpanded,
            childCount: effectiveChildCount,
            hasChildren: effectiveChildCount > 0,
            depth: node.depth,
            isGroup: false,
            onToggle: () => toggleNode(url),
          },
        })

        // Create edges to effective children
        if (isExpanded) {
          const effectiveChildren = getEffectiveChildren(url)
          effectiveChildren.forEach((childId) => {
            edges.push({
              id: `${url}-${childId}`,
              source: url,
              target: childId,
              type: "default",
              style: { stroke: "#94a3b8", strokeWidth: 1.5 },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                width: 16,
                height: 16,
                color: "#94a3b8",
              },
            })
          })
        }
      })

    // Create React Flow nodes for visible group nodes
    visibleGroups.forEach((group, groupId) => {
      const pos = nodePositions[groupId] || { x: 0, y: 0 }
      const isExpanded = expandedNodes.has(groupId)

      nodes.push({
        id: groupId,
        type: "ontology",
        position: pos,
        data: {
          label: `${group.groupKey} (${group.children.length})`,
          isSelected: false,
          isHighlighted: false,
          isExpanded,
          childCount: group.children.length,
          hasChildren: group.children.length > 0,
          depth: (ontologyNodes[group.parentId]?.depth ?? 0) + 1,
          isGroup: true,
          onToggle: () => toggleNode(groupId),
        },
      })

      // Create edges from group to its children
      if (isExpanded) {
        group.children
          .filter((childId) => visibleNodes.has(childId))
          .forEach((childId) => {
            const isHighlighted = highlightedPath.includes(childId)
            edges.push({
              id: `${groupId}-${childId}`,
              source: groupId,
              target: childId,
              type: "default",
              style: {
                stroke: isHighlighted ? "#3b82f6" : "#94a3b8",
                strokeWidth: isHighlighted ? 2.5 : 1.5,
              },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                width: 16,
                height: 16,
                color: isHighlighted ? "#3b82f6" : "#94a3b8",
              },
              animated: isHighlighted,
            })
          })
      }
    })

    return { flowNodes: nodes, flowEdges: edges }
  }, [ontologyNodes, root, selectedNode, highlightedPath, visibleNodes, visibleGroups, expandedNodes, groupingInfo, toggleNode])

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges)

  // Sync nodes/edges when flowNodes/flowEdges change
  useEffect(() => {
    setNodes(flowNodes)
    setEdges(flowEdges)
  }, [flowNodes, flowEdges, setNodes, setEdges])

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onNodeSelect(node.id)
    },
    [onNodeSelect]
  )

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        maxZoom={2}
        defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
      >
        <Background />
        <Controls />
        <Panel position="top-right" className="flex gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                Depth
                <ChevronDown className="ml-1 h-3 w-3" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {[1, 2, 3, 4, 5].filter((d) => d <= maxDepth).map((depth) => (
                <DropdownMenuItem key={depth} onClick={() => expandToDepth(depth)}>
                  Expand {depth} {depth === 1 ? "level" : "levels"}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          <Button variant="outline" size="sm" onClick={expandAll} title="Expand all">
            <Maximize2 className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={collapseAll} title="Collapse all">
            <Minimize2 className="h-4 w-4" />
          </Button>
        </Panel>
        <MiniMap
          nodeColor={(node) =>
            node.data?.isSelected
              ? "hsl(var(--primary))"
              : node.data?.isHighlighted
                ? "hsl(var(--primary) / 0.5)"
                : "hsl(var(--muted))"
          }
          maskColor="hsl(var(--background) / 0.8)"
        />
      </ReactFlow>
    </div>
  )
}
