"use client"

import { useState, useEffect, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
import {
  Search,
  ChevronRight,
  ChevronDown,
  Network,
  TreePine,
  GitBranch,
  ArrowLeft,
  Loader2,
  AlertCircle,
} from "lucide-react"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { OntologyDAG } from "@/components/ontology/OntologyDAG"
import { ontologiesApi } from "@/lib/api"
import type { OntologyNode } from "@/lib/types"

function TreeNode({
  nodeUrl,
  node,
  nodes,
  selectedNode,
  onSelect,
  expandedNodes,
  onToggle,
}: {
  nodeUrl: string
  node: OntologyNode
  nodes: Record<string, OntologyNode>
  selectedNode: string | null
  onSelect: (url: string) => void
  expandedNodes: Set<string>
  onToggle: (url: string) => void
}) {
  const hasChildren = node.children.length > 0
  const isExpanded = expandedNodes.has(nodeUrl)
  const isSelected = selectedNode === nodeUrl

  return (
    <div>
      <div
        className={`flex items-center gap-1 py-1 px-2 rounded-md cursor-pointer hover:bg-muted ${
          isSelected ? "bg-primary/10 text-primary" : ""
        }`}
        style={{ paddingLeft: `${node.depth * 16 + 8}px` }}
        onClick={() => onSelect(nodeUrl)}
      >
        {hasChildren ? (
          <button
            onClick={(e) => {
              e.stopPropagation()
              onToggle(nodeUrl)
            }}
            className="p-0.5 hover:bg-muted-foreground/20 rounded"
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
        ) : (
          <span className="w-5" />
        )}
        <span className="text-sm">{node.label || node.name}</span>
        {hasChildren && (
          <Badge variant="secondary" className="ml-auto text-xs">
            {node.children.length}
          </Badge>
        )}
      </div>
      {hasChildren && isExpanded && (
        <div>
          {node.children.map((childUrl) =>
            nodes[childUrl] ? (
              <TreeNode
                key={childUrl}
                nodeUrl={childUrl}
                node={nodes[childUrl]}
                nodes={nodes}
                selectedNode={selectedNode}
                onSelect={onSelect}
                expandedNodes={expandedNodes}
                onToggle={onToggle}
              />
            ) : null
          )}
        </div>
      )}
    </div>
  )
}

export default function OntologyDetailPage() {
  const params = useParams()
  const router = useRouter()
  const ontologyId = decodeURIComponent(params.ontologyId as string)

  // State for ontology info
  const [ontologyInfo, setOntologyInfo] = useState<{ filename: string | null } | null>(null)

  // State for ontology tree
  const [treeData, setTreeData] = useState<{
    root: string
    nodes: Record<string, OntologyNode>
    truncated?: boolean
    total_nodes?: number
  } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // State for UI
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<
    { url: string; name: string; label: string | null }[]
  >([])
  const [searchLoading, setSearchLoading] = useState(false)

  // Fetch ontology info and tree
  const fetchTree = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [info, tree] = await Promise.all([
        ontologiesApi.get(ontologyId),
        ontologiesApi.getTree(ontologyId),
      ])
      setOntologyInfo(info)
      setTreeData(tree)
      // Expand root nodes by default
      const rootChildren = tree.nodes[tree.root]?.children || []
      setExpandedNodes(new Set([tree.root, ...rootChildren]))
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load ontology")
    } finally {
      setLoading(false)
    }
  }, [ontologyId])

  // Search classes
  const handleSearch = useCallback(
    async (query: string) => {
      if (!query.trim()) {
        setSearchResults([])
        return
      }
      setSearchLoading(true)
      try {
        const result = await ontologiesApi.getClasses(ontologyId, query)
        setSearchResults(result.classes)
      } catch (err) {
        console.error("Search failed:", err)
        setSearchResults([])
      } finally {
        setSearchLoading(false)
      }
    },
    [ontologyId]
  )

  useEffect(() => {
    fetchTree()
  }, [fetchTree])

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      handleSearch(searchQuery)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery, handleSearch])

  const toggleNode = (url: string) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev)
      if (next.has(url)) {
        next.delete(url)
      } else {
        next.add(url)
      }
      return next
    })
  }

  const selected = selectedNode && treeData ? treeData.nodes[selectedNode] : null

  // Build path from root to selected node
  const getPathToNode = (target: string): string[] => {
    if (!treeData) return []
    const path: string[] = []
    let current = target
    const visited = new Set<string>()
    while (current && !visited.has(current)) {
      visited.add(current)
      path.unshift(current)
      const parent = Object.entries(treeData.nodes).find(([, node]) =>
        node.children.includes(current)
      )
      if (parent) {
        current = parent[0]
      } else {
        break
      }
    }
    return path
  }

  const pathToSelected = selectedNode ? getPathToNode(selectedNode) : []

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4">
        <AlertCircle className="h-12 w-12 text-destructive" />
        <p className="text-muted-foreground">{error}</p>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => router.push("/ontology")}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to List
          </Button>
          <Button onClick={fetchTree}>Retry</Button>
        </div>
      </div>
    )
  }

  if (!treeData) return null

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/ontology">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{ontologyInfo?.filename || ontologyId}</h1>
          <p className="text-muted-foreground">
            Explore the ontology class hierarchy
          </p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
        {/* Main View with Tabs */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Network className="h-5 w-5" />
                Class Hierarchy
              </CardTitle>
              <div className="relative w-64">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search classes..."
                  className="pl-8"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                {searchLoading && (
                  <Loader2 className="absolute right-2 top-2.5 h-4 w-4 animate-spin text-muted-foreground" />
                )}
              </div>
            </div>
            <CardDescription>
              {Object.keys(treeData.nodes).length} classes in the ontology
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/* Search Results */}
            {searchQuery && searchResults.length > 0 && (
              <div className="mb-4 p-3 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground mb-2">
                  Found {searchResults.length} matches:
                </p>
                <div className="flex flex-wrap gap-1">
                  {searchResults.slice(0, 10).map((result) => (
                    <Badge
                      key={result.url}
                      variant="secondary"
                      className="cursor-pointer hover:bg-primary/20"
                      onClick={() => {
                        setSelectedNode(result.url)
                        const path = getPathToNode(result.url)
                        setExpandedNodes((prev) => new Set([...prev, ...path]))
                      }}
                    >
                      {result.label || result.name}
                    </Badge>
                  ))}
                  {searchResults.length > 10 && (
                    <Badge variant="outline">+{searchResults.length - 10} more</Badge>
                  )}
                </div>
              </div>
            )}

            <Tabs defaultValue="tree" className="w-full">
              <TabsList className="mb-4">
                <TabsTrigger value="tree" className="flex items-center gap-2">
                  <TreePine className="h-4 w-4" />
                  Tree View
                </TabsTrigger>
                <TabsTrigger value="graph" className="flex items-center gap-2">
                  <GitBranch className="h-4 w-4" />
                  Graph View
                </TabsTrigger>
              </TabsList>

              <TabsContent value="tree" className="mt-0">
                <ScrollArea className="h-[500px]">
                  {/* Render from root (Thing) to show depth 0 */}
                  {treeData.nodes[treeData.root] && (
                    <TreeNode
                      nodeUrl={treeData.root}
                      node={treeData.nodes[treeData.root]}
                      nodes={treeData.nodes}
                      selectedNode={selectedNode}
                      onSelect={setSelectedNode}
                      expandedNodes={expandedNodes}
                      onToggle={toggleNode}
                    />
                  )}
                </ScrollArea>
              </TabsContent>

              <TabsContent value="graph" className="mt-0">
                <div className="h-[500px] border rounded-lg overflow-hidden">
                  <OntologyDAG
                    nodes={treeData.nodes}
                    root={treeData.root}
                    selectedNode={selectedNode}
                    onNodeSelect={setSelectedNode}
                    highlightedPath={pathToSelected}
                  />
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* Details Panel */}
        <Card>
          <CardHeader>
            <CardTitle>Class Details</CardTitle>
            <CardDescription>
              {selected
                ? `Details for ${selected.label || selected.name}`
                : "Select a class to view details"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {selected ? (
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Name
                  </label>
                  <p className="text-sm font-medium">{selected.name}</p>
                </div>

                {selected.label && (
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Label
                    </label>
                    <p className="text-sm">{selected.label}</p>
                  </div>
                )}

                {selected.comment && (
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Description
                    </label>
                    <p className="text-sm text-muted-foreground">{selected.comment}</p>
                  </div>
                )}

                <Separator />

                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Depth
                  </label>
                  <p className="text-sm">{selected.depth}</p>
                </div>

                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Children
                  </label>
                  <p className="text-sm">{selected.children.length} direct children</p>
                  {selected.children.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {selected.children.slice(0, 5).map((childUrl) => {
                        const child = treeData.nodes[childUrl]
                        return child ? (
                          <Badge
                            key={childUrl}
                            variant="secondary"
                            className="cursor-pointer hover:bg-primary/20"
                            onClick={() => {
                              setSelectedNode(childUrl)
                              setExpandedNodes((prev) => new Set([...prev, selectedNode!]))
                            }}
                          >
                            {child.label || child.name}
                          </Badge>
                        ) : null
                      })}
                      {selected.children.length > 5 && (
                        <Badge variant="outline">+{selected.children.length - 5}</Badge>
                      )}
                    </div>
                  )}
                </div>

                <Separator />

                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Path from Root
                  </label>
                  <div className="flex items-center gap-1 mt-1 flex-wrap">
                    {pathToSelected.map((nodeUrl, i) => {
                      const pathNode = treeData.nodes[nodeUrl]
                      return pathNode ? (
                        <span key={nodeUrl} className="flex items-center gap-1">
                          <Badge
                            variant={nodeUrl === selectedNode ? "default" : "outline"}
                            className="cursor-pointer"
                            onClick={() => setSelectedNode(nodeUrl)}
                          >
                            {pathNode.label || pathNode.name}
                          </Badge>
                          {i < pathToSelected.length - 1 && (
                            <ChevronRight className="h-3 w-3 text-muted-foreground" />
                          )}
                        </span>
                      ) : null
                    })}
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Click on a class in the tree view to see its details.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
