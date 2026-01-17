"use client"

import { useState, useEffect, useCallback } from "react"
import { GitCompare, Loader2, AlertCircle, Plus, X, Trophy, FileText, FolderArchive } from "lucide-react"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { labelsApi, batchesApi, evaluationsApi } from "@/lib/api"
import type { LabelsInfo, BatchInfo, EvaluationComparison } from "@/lib/types"

export default function ComparePage() {
  // Data state
  const [labels, setLabels] = useState<LabelsInfo[]>([])
  const [batches, setBatches] = useState<BatchInfo[]>([])
  const [loadingLabels, setLoadingLabels] = useState(true)
  const [loadingBatches, setLoadingBatches] = useState(true)

  // Form state
  const [selectedLabels, setSelectedLabels] = useState("")
  const [selectedBatches, setSelectedBatches] = useState<string[]>(["", ""])

  // Comparison state
  const [comparing, setComparing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [comparison, setComparison] = useState<EvaluationComparison | null>(null)

  const fetchLabels = useCallback(async () => {
    setLoadingLabels(true)
    try {
      const list = await labelsApi.list()
      setLabels(list)
      if (list.length > 0 && !selectedLabels) {
        setSelectedLabels(list[0].id)
      }
    } catch (err) {
      console.error("Failed to fetch labels:", err)
    } finally {
      setLoadingLabels(false)
    }
  }, [selectedLabels])

  const fetchBatches = useCallback(async () => {
    setLoadingBatches(true)
    try {
      const list = await batchesApi.list()
      setBatches(list)
    } catch (err) {
      console.error("Failed to fetch batches:", err)
    } finally {
      setLoadingBatches(false)
    }
  }, [])

  useEffect(() => {
    fetchLabels()
    fetchBatches()
  }, [fetchLabels, fetchBatches])

  const addBatchSlot = () => {
    setSelectedBatches((prev) => [...prev, ""])
  }

  const removeBatchSlot = (index: number) => {
    if (selectedBatches.length <= 2) return
    setSelectedBatches((prev) => prev.filter((_, i) => i !== index))
  }

  const updateBatchSelection = (index: number, value: string) => {
    setSelectedBatches((prev) => prev.map((p, i) => (i === index ? value : p)))
  }

  const handleCompare = async () => {
    const selected = selectedBatches.filter((id) => id.trim())
    if (selected.length < 2) {
      setError("Please select at least 2 batch files")
      return
    }
    if (!selectedLabels) {
      setError("Please select a labels file")
      return
    }

    // Convert batch IDs to filenames for the API
    const paths = selected.map((id) => {
      const batch = batches.find((b) => b.id === id)
      return batch?.filename ?? id
    })

    setComparing(true)
    setError(null)
    setComparison(null)

    try {
      const result = await evaluationsApi.compare(paths, selectedLabels)
      setComparison(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Comparison failed")
    } finally {
      setComparing(false)
    }
  }

  // Get batch info by ID for display
  const getBatchInfo = (id: string) => batches.find((b) => b.id === id)

  const formatPercent = (value: number | null) =>
    value !== null ? `${(value * 100).toFixed(2)}%` : "-"

  const isBest = (value: number, best: number | null) =>
    best !== null && Math.abs(value - best) < 0.0001

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Compare Experiments</h1>
        <p className="text-muted-foreground">
          Compare evaluation results across multiple experiments side-by-side.
        </p>
      </div>

      {/* Setup Card */}
      <Card>
        <CardHeader>
          <CardTitle>Comparison Setup</CardTitle>
          <CardDescription>
            Select batch files and ground truth labels to compare.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Labels Selection */}
          <div className="space-y-2">
            <Label>Ground Truth Labels</Label>
            {loadingLabels ? (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading labels...
              </div>
            ) : (
              <Select value={selectedLabels} onValueChange={setSelectedLabels}>
                <SelectTrigger className="max-w-md">
                  <SelectValue placeholder="Select labels file" />
                </SelectTrigger>
                <SelectContent>
                  {labels.map((label) => (
                    <SelectItem key={label.id} value={label.id}>
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        <span>{label.name}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {/* Batch Selection */}
          <div className="space-y-2">
            <Label>Batch Files to Compare</Label>
            {loadingBatches ? (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading batches...
              </div>
            ) : batches.length === 0 ? (
              <div className="text-sm text-muted-foreground">
                No batches found. Upload batch files first.
              </div>
            ) : (
              <>
                <div className="space-y-2">
                  {selectedBatches.map((batchId, index) => (
                    <div key={index} className="flex gap-2">
                      <Select
                        value={batchId}
                        onValueChange={(value) => updateBatchSelection(index, value)}
                      >
                        <SelectTrigger className="flex-1">
                          <SelectValue placeholder={`Select batch ${index + 1}`} />
                        </SelectTrigger>
                        <SelectContent>
                          {batches.map((batch) => (
                            <SelectItem key={batch.id} value={batch.id}>
                              <div className="flex items-center gap-1.5">
                                <FolderArchive className="h-3.5 w-3.5 flex-shrink-0" />
                                <span className="truncate max-w-[180px]">{batch.name}</span>
                                <span className="text-muted-foreground text-xs">{batch.stats.total_columns}c</span>
                                {batch.config.provider && (
                                  <Badge variant="outline" className="h-5 px-1 text-[10px]">{batch.config.provider}</Badge>
                                )}
                                {batch.config.model && (
                                  <Badge variant="secondary" className="h-5 px-1 text-[10px]">{batch.config.model}</Badge>
                                )}
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {selectedBatches.length > 2 && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => removeBatchSlot(index)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
                <Button variant="outline" size="sm" onClick={addBatchSlot}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Another
                </Button>
              </>
            )}
          </div>

          {error && (
            <div className="flex items-center gap-2 text-destructive text-sm">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}

          <Button
            onClick={handleCompare}
            disabled={comparing || selectedBatches.filter(b => b).length < 2 || !selectedLabels}
            className="w-full sm:w-auto"
          >
            {comparing ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Comparing...
              </>
            ) : (
              <>
                <GitCompare className="h-4 w-4 mr-2" />
                Compare Experiments
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Results Card */}
      {comparison && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <GitCompare className="h-5 w-5" />
              Comparison Results
            </CardTitle>
            <CardDescription>
              {comparison.successful} of {comparison.total_batches} experiments compared successfully
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Best Scores Summary */}
            <div className="flex gap-4 p-4 bg-muted rounded-lg">
              <div className="flex items-center gap-2">
                <Trophy className="h-5 w-5 text-yellow-500" />
                <span className="font-medium">Best Scores:</span>
              </div>
              <div className="flex gap-6">
                <div>
                  <span className="text-muted-foreground">Path F1:</span>{" "}
                  <span className="font-mono font-bold">
                    {formatPercent(comparison.best_scores.path_macro_f1)}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">Node F1:</span>{" "}
                  <span className="font-mono font-bold">
                    {formatPercent(comparison.best_scores.node_macro_f1)}
                  </span>
                </div>
              </div>
            </div>

            {/* Comparison Table */}
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Experiment</TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Mode</TableHead>
                  <TableHead>Prompt</TableHead>
                  <TableHead>Path F1</TableHead>
                  <TableHead>Node F1</TableHead>
                  <TableHead>Columns</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {comparison.results.map((result, index) => (
                  <TableRow key={index}>
                    <TableCell className="font-mono text-sm max-w-xs truncate">
                      {result.run_id || result.batch_path}
                    </TableCell>
                    {result.error ? (
                      <>
                        <TableCell colSpan={7} className="text-destructive">
                          {result.error}
                        </TableCell>
                        <TableCell>
                          <Badge variant="destructive">Failed</Badge>
                        </TableCell>
                      </>
                    ) : (
                      <>
                        <TableCell>
                          {result.config.provider && (
                            <Badge variant="outline" className="text-xs">{result.config.provider}</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {result.config.model && (
                            <Badge variant="secondary" className="text-xs">{result.config.model}</Badge>
                          )}
                        </TableCell>
                        <TableCell>{result.config.mode}</TableCell>
                        <TableCell>{result.config.prompt_type}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Progress
                              value={result.metrics.path_level.macro_f1 * 100}
                              className="w-16 h-2"
                            />
                            <span className="font-mono text-sm">
                              {formatPercent(result.metrics.path_level.macro_f1)}
                            </span>
                            {isBest(
                              result.metrics.path_level.macro_f1,
                              comparison.best_scores.path_macro_f1
                            ) && (
                              <Trophy className="h-4 w-4 text-yellow-500" />
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Progress
                              value={result.metrics.node_level.macro_f1 * 100}
                              className="w-16 h-2"
                            />
                            <span className="font-mono text-sm">
                              {formatPercent(result.metrics.node_level.macro_f1)}
                            </span>
                            {isBest(
                              result.metrics.node_level.macro_f1,
                              comparison.best_scores.node_macro_f1
                            ) && (
                              <Trophy className="h-4 w-4 text-yellow-500" />
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          {result.summary.evaluated_columns}/{result.summary.total_columns}
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">Success</Badge>
                        </TableCell>
                      </>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {/* Detailed Metrics */}
            <div className="grid gap-4 md:grid-cols-2">
              {comparison.results
                .filter((r) => !r.error)
                .map((result, index) => (
                  <Card key={index}>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium">
                        {result.run_id}
                      </CardTitle>
                      <CardDescription className="space-y-1">
                        <div className="flex flex-wrap gap-1">
                          {result.config.provider && (
                            <Badge variant="outline" className="h-5 px-1 text-[10px]">{result.config.provider}</Badge>
                          )}
                          {result.config.model && (
                            <Badge variant="secondary" className="h-5 px-1 text-[10px]">{result.config.model}</Badge>
                          )}
                        </div>
                        <div>{result.config.mode} | {result.config.prompt_type}</div>
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">Path-Level</p>
                        <div className="grid grid-cols-3 gap-2 text-xs">
                          <div>
                            <span className="text-muted-foreground">P:</span>{" "}
                            {formatPercent(result.metrics.path_level.macro_precision)}
                          </div>
                          <div>
                            <span className="text-muted-foreground">R:</span>{" "}
                            {formatPercent(result.metrics.path_level.macro_recall)}
                          </div>
                          <div className="font-bold">
                            <span className="text-muted-foreground">F1:</span>{" "}
                            {formatPercent(result.metrics.path_level.macro_f1)}
                          </div>
                        </div>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">Node-Level</p>
                        <div className="grid grid-cols-3 gap-2 text-xs">
                          <div>
                            <span className="text-muted-foreground">P:</span>{" "}
                            {formatPercent(result.metrics.node_level.macro_precision)}
                          </div>
                          <div>
                            <span className="text-muted-foreground">R:</span>{" "}
                            {formatPercent(result.metrics.node_level.macro_recall)}
                          </div>
                          <div className="font-bold">
                            <span className="text-muted-foreground">F1:</span>{" "}
                            {formatPercent(result.metrics.node_level.macro_f1)}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
