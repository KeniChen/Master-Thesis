"use client"

import { use, useEffect, useState } from "react"
import Link from "next/link"
import {
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  Clock,
  Loader2,
  Network,
  XCircle,
  AlertTriangle,
  RefreshCw,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Progress } from "@/components/ui/progress"
import { BFSStepCard } from "@/components/run"
import { runsApi, tablesApi } from "@/lib/api"
import type { RunResult, ColumnResult, DecisionMode, TablePreview } from "@/lib/types"

export default function RunDetailPage({
  params,
}: {
  params: Promise<{ runId: string }>
}) {
  const { runId } = use(params)
  const [run, setRun] = useState<RunResult | null>(null)
  const [tablePreview, setTablePreview] = useState<TablePreview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedColumn, setSelectedColumn] = useState(0)
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set([0]))
  const [isStreaming, setIsStreaming] = useState(false)

  // Fetch run data
  const fetchRun = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await runsApi.get(runId)
      setRun(data)

      // Fetch table preview if we have the table ID
      if (data.config.table_id) {
        try {
          const preview = await tablesApi.preview(data.config.table_id, data.config.k || 5)
          setTablePreview(preview)
        } catch {
          // Silently ignore table preview errors
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load run")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRun()
  }, [runId])

  // Set up SSE streaming for running/pending runs
  useEffect(() => {
    if (!run || !["pending", "running"].includes(run.status)) {
      return
    }

    setIsStreaming(true)

    const unsubscribe = runsApi.stream(runId, {
      onStep: (data) => {
        // Refresh run data when a step completes
        fetchRun()
      },
      onColumnComplete: (data) => {
        fetchRun()
      },
      onRunComplete: (data) => {
        setIsStreaming(false)
        fetchRun()
      },
      onError: (data) => {
        setIsStreaming(false)
        setError(data.error)
      },
    })

    return unsubscribe
  }, [run?.status, runId])

  const currentColumn = run?.columns[selectedColumn]

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="h-4 w-4 text-green-500" />
      case "failed":
        return <XCircle className="h-4 w-4 text-red-500" />
      case "partial":
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />
      case "running":
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
      case "pending":
        return <Clock className="h-4 w-4 text-gray-400" />
      default:
        return null
    }
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      completed: "default",
      failed: "destructive",
      partial: "secondary",
      running: "default",
      pending: "outline",
    }

    const colors: Record<string, string> = {
      completed: "bg-green-500",
      running: "bg-blue-500",
    }

    return (
      <Badge variant={variants[status] || "outline"} className={colors[status] || ""}>
        {getStatusIcon(status)}
        <span className="ml-1 capitalize">{status}</span>
      </Badge>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error || !run) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/annotations">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Link>
        </Button>
        <Card>
          <CardContent className="flex flex-col items-center justify-center h-[200px] gap-4">
            <XCircle className="h-12 w-12 text-red-500" />
            <p className="text-muted-foreground">{error || "Run not found"}</p>
            <Button onClick={fetchRun}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const mode = run.config.mode as DecisionMode
  const showReasoning = run.config.prompt_type === "cot"
  const progressPercent = run.summary
    ? ((run.summary.completed_columns + run.summary.failed_columns + run.summary.partial_columns) /
        run.summary.total_columns) *
      100
    : 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/annotations">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Link>
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{runId}</h1>
            <p className="text-muted-foreground">
              {run.config.table_id} | {run.columns.length} columns |{" "}
              <Badge variant="outline">{mode.toUpperCase()}</Badge>{" "}
              <Badge variant="outline">{run.config.prompt_type.toUpperCase()}</Badge>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isStreaming && (
            <Badge variant="outline" className="animate-pulse">
              <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              Live
            </Badge>
          )}
          {getStatusBadge(run.status)}
        </div>
      </div>

      {/* Progress bar for running tasks */}
      {["pending", "running"].includes(run.status) && run.summary && (
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Progress</span>
              <span className="text-sm text-muted-foreground">
                {run.summary.completed_columns}/{run.summary.total_columns} columns
              </span>
            </div>
            <Progress value={progressPercent} className="h-2" />
          </CardContent>
        </Card>
      )}

      {/* Three Column Layout */}
      <div className="grid gap-4 lg:grid-cols-[250px_1fr_300px]">
        {/* Left: Table Panel */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Table</CardTitle>
            <CardDescription>{run.config.table_id}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {tablePreview && (
              <>
                <div>
                  <label className="text-xs font-medium text-muted-foreground">
                    Preview ({run.config.k} rows)
                  </label>
                  <ScrollArea className="h-[150px] mt-1">
                    <div className="text-xs font-mono bg-muted p-2 rounded overflow-auto">
                      <table className="w-full">
                        <thead>
                          <tr>
                            {tablePreview.columns.map((col) => (
                              <th key={col} className="text-left px-1 pb-1 border-b">
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {tablePreview.rows.map((row, i) => (
                            <tr key={i}>
                              {tablePreview.columns.map((col) => (
                                <td key={col} className="px-1 py-0.5">
                                  {String(row[col] ?? "")}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </ScrollArea>
                </div>
                <Separator />
              </>
            )}

            <div>
              <label className="text-xs font-medium text-muted-foreground">
                Annotated Columns
              </label>
              <div className="space-y-1 mt-1">
                {run.columns.length > 0 ? (
                  run.columns.map((col, i) => (
                    <button
                      key={col.column_name}
                      onClick={() => setSelectedColumn(i)}
                      className={`w-full flex items-center justify-between text-left text-sm px-2 py-1.5 rounded ${
                        selectedColumn === i
                          ? "bg-primary text-primary-foreground"
                          : "hover:bg-muted"
                      }`}
                    >
                      <span>{col.column_name}</span>
                      {getStatusIcon(col.status)}
                    </button>
                  ))
                ) : (
                  <div className="text-sm text-muted-foreground py-2">
                    {run.status === "pending" ? "Waiting to start..." : "No columns processed yet"}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Center: Decision Flow */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Decision Flow</CardTitle>
            <CardDescription>
              {currentColumn
                ? `Column: ${currentColumn.column_name}`
                : "Select a column to view details"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {currentColumn ? (
              <ScrollArea className="h-[500px] pr-4">
                <div className="space-y-4">
                  {currentColumn.steps.map((step, i) => (
                    <BFSStepCard
                      key={`${step.level}-${step.parent}`}
                      step={step}
                      stepIndex={i}
                      isLast={i === currentColumn.steps.length - 1}
                      defaultExpanded={i === 0}
                      mode={mode}
                      showReasoning={showReasoning}
                    />
                  ))}

                  {/* Final Path(s) */}
                  {currentColumn.final_paths.length > 0 && (
                    <div className="border rounded-lg p-4 bg-green-50 dark:bg-green-950/30">
                      <label className="text-xs font-medium text-green-700 dark:text-green-300 uppercase tracking-wider">
                        Final Path{currentColumn.final_paths.length > 1 ? "s" : ""}
                      </label>
                      <div className="space-y-2 mt-2">
                        {currentColumn.final_paths.map((path, i) => (
                          <div key={i} className="flex items-center gap-1 flex-wrap">
                            {path.map((node, j) => (
                              <span key={`${node}-${j}`} className="flex items-center gap-1">
                                <Badge
                                  variant={j === path.length - 1 ? "default" : "secondary"}
                                  className={j === path.length - 1 ? "bg-green-500" : ""}
                                >
                                  {node}
                                </Badge>
                                {j < path.length - 1 && (
                                  <ChevronRight className="h-3 w-3 text-muted-foreground" />
                                )}
                              </span>
                            ))}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Column error */}
                  {currentColumn.error && (
                    <div className="border border-red-200 dark:border-red-800 rounded-lg p-4 bg-red-50 dark:bg-red-950/30">
                      <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
                        <XCircle className="h-4 w-4" />
                        <span className="text-sm font-medium">Error</span>
                      </div>
                      <p className="text-sm text-red-600 dark:text-red-400 mt-1">
                        {currentColumn.error}
                      </p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            ) : (
              <div className="flex items-center justify-center h-[200px] text-muted-foreground">
                {run.status === "pending" ? (
                  <div className="text-center">
                    <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2" />
                    <p>Waiting for annotation to start...</p>
                  </div>
                ) : (
                  <p>Select a column to view its decision flow</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Right: Ontology Panel */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Network className="h-4 w-4" />
              Ontology Path
            </CardTitle>
            <CardDescription>
              {run.config.ontology_id}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {currentColumn && currentColumn.final_paths.length > 0 ? (
              <div className="space-y-4">
                {currentColumn.final_paths.map((path, pathIndex) => (
                  <div key={pathIndex} className="space-y-2">
                    {currentColumn.final_paths.length > 1 && (
                      <label className="text-xs font-medium text-muted-foreground">
                        Path {pathIndex + 1}
                      </label>
                    )}
                    {path.map((node, i) => (
                      <div
                        key={`${node}-${i}`}
                        className="flex items-center gap-2"
                        style={{ paddingLeft: `${i * 16}px` }}
                      >
                        {i > 0 && (
                          <div className="w-4 h-4 border-l-2 border-b-2 border-primary rounded-bl" />
                        )}
                        <div
                          className={`px-3 py-2 rounded-lg border ${
                            i === path.length - 1
                              ? "bg-primary text-primary-foreground border-primary"
                              : "bg-muted"
                          }`}
                        >
                          <span className="text-sm font-medium">{node}</span>
                        </div>
                      </div>
                    ))}
                    {pathIndex < currentColumn.final_paths.length - 1 && (
                      <Separator className="my-4" />
                    )}
                  </div>
                ))}

                <Separator className="my-4" />

                <div>
                  <label className="text-xs font-medium text-muted-foreground">
                    Path Summary
                  </label>
                  <div className="space-y-1 mt-1">
                    {currentColumn.final_paths.map((path, i) => (
                      <p key={i} className="text-sm font-mono">
                        {path.join(" → ")}
                      </p>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-[200px] text-muted-foreground text-sm">
                {currentColumn ? "No path generated yet" : "Select a column to view path"}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Run Summary */}
      {run.summary && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Run Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold">{run.summary.total_columns}</p>
                <p className="text-xs text-muted-foreground">Total Columns</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-green-500">
                  {run.summary.completed_columns}
                </p>
                <p className="text-xs text-muted-foreground">Completed</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-yellow-500">
                  {run.summary.partial_columns}
                </p>
                <p className="text-xs text-muted-foreground">Partial</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-red-500">{run.summary.failed_columns}</p>
                <p className="text-xs text-muted-foreground">Failed</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Global error */}
      {run.error && (
        <Card className="border-red-200 dark:border-red-800">
          <CardContent className="py-4">
            <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
              <XCircle className="h-5 w-5" />
              <span className="font-medium">Run Error</span>
            </div>
            <p className="text-sm text-red-600 dark:text-red-400 mt-2">{run.error}</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
