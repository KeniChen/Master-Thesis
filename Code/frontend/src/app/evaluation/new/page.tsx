"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import { FileText, FolderArchive, Loader2, AlertCircle, Play, CheckCircle2 } from "lucide-react"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { labelsApi, batchesApi, evaluationsApi } from "@/lib/api"
import type { LabelsInfo, BatchInfo, EvaluationResult } from "@/lib/types"

export default function NewEvaluationPage() {
  const router = useRouter()

  // Data state
  const [labels, setLabels] = useState<LabelsInfo[]>([])
  const [batches, setBatches] = useState<BatchInfo[]>([])
  const [loadingLabels, setLoadingLabels] = useState(true)
  const [loadingBatches, setLoadingBatches] = useState(true)

  // Form state
  const [selectedBatch, setSelectedBatch] = useState("")
  const [selectedLabels, setSelectedLabels] = useState("")

  // Evaluation state
  const [evaluating, setEvaluating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<EvaluationResult | null>(null)

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
      if (list.length > 0 && !selectedBatch) {
        setSelectedBatch(list[0].id)
      }
    } catch (err) {
      console.error("Failed to fetch batches:", err)
    } finally {
      setLoadingBatches(false)
    }
  }, [selectedBatch])

  useEffect(() => {
    fetchLabels()
    fetchBatches()
  }, [fetchLabels, fetchBatches])

  const handleEvaluate = async () => {
    if (!selectedBatch || !selectedLabels) {
      setError("Please select both a batch file and labels")
      return
    }

    // Find the selected batch to get its filename
    const batch = batches.find(b => b.id === selectedBatch)
    if (!batch) {
      setError("Selected batch not found")
      return
    }

    setEvaluating(true)
    setError(null)
    setResult(null)

    try {
      // Use the batch filename as the path (relative to batches directory)
      const evalResult = await evaluationsApi.run(batch.filename, selectedLabels)
      setResult(evalResult)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evaluation failed")
    } finally {
      setEvaluating(false)
    }
  }

  const formatPercent = (value: number) => `${(value * 100).toFixed(2)}%`

  // Get selected batch info for display
  const selectedBatchInfo = batches.find(b => b.id === selectedBatch)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">New Evaluation</h1>
        <p className="text-muted-foreground">
          Evaluate batch experiment results against ground truth labels.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Input Card */}
        <Card>
          <CardHeader>
            <CardTitle>Evaluation Setup</CardTitle>
            <CardDescription>
              Select a batch result file and ground truth labels to evaluate.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Batch Selection */}
            <div className="space-y-2">
              <Label>Batch Result</Label>
              {loadingBatches ? (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading batches...
                </div>
              ) : batches.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  No batches found.{" "}
                  <Button
                    variant="link"
                    className="p-0 h-auto"
                    onClick={() => router.push("/batches")}
                  >
                    Upload a batch first
                  </Button>
                </div>
              ) : (
                <>
                  <Select value={selectedBatch} onValueChange={setSelectedBatch}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select batch file" />
                    </SelectTrigger>
                    <SelectContent className="w-[480px]">
                      {batches.map((batch) => (
                        <SelectItem key={batch.id} value={batch.id}>
                          <div className="flex items-center gap-2 flex-wrap">
                            <FolderArchive className="h-4 w-4 flex-shrink-0" />
                            <span>{batch.name}</span>
                            <span className="text-muted-foreground text-xs">
                              ({batch.stats.total_columns} cols)
                            </span>
                            {batch.config.provider && (
                              <Badge variant="outline" className="bg-blue-50 text-xs">
                                {batch.config.provider}
                              </Badge>
                            )}
                            {batch.config.model && (
                              <Badge variant="outline" className="bg-purple-50 text-xs">
                                {batch.config.model}
                              </Badge>
                            )}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {selectedBatchInfo && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      <Badge variant="outline">{selectedBatchInfo.config.mode}</Badge>
                      <Badge variant="outline">{selectedBatchInfo.config.prompt_type}</Badge>
                      {selectedBatchInfo.config.ontology_id && (
                        <Badge variant="secondary">
                          {selectedBatchInfo.config.ontology_id.replace(".rdf", "")}
                        </Badge>
                      )}
                      {selectedBatchInfo.config.provider && (
                        <Badge variant="outline" className="bg-blue-50">
                          {selectedBatchInfo.config.provider}
                        </Badge>
                      )}
                      {selectedBatchInfo.config.model && (
                        <Badge variant="outline" className="bg-purple-50 text-xs">
                          {selectedBatchInfo.config.model}
                        </Badge>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Labels Selection */}
            <div className="space-y-2">
              <Label>Ground Truth Labels</Label>
              {loadingLabels ? (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading labels...
                </div>
              ) : labels.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  No labels found.{" "}
                  <Button
                    variant="link"
                    className="p-0 h-auto"
                    onClick={() => router.push("/labels")}
                  >
                    Upload labels first
                  </Button>
                </div>
              ) : (
                <Select value={selectedLabels} onValueChange={setSelectedLabels}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select labels file" />
                  </SelectTrigger>
                  <SelectContent>
                    {labels.map((label) => (
                      <SelectItem key={label.id} value={label.id}>
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4" />
                          <span>{label.name}</span>
                          <span className="text-muted-foreground text-xs">
                            ({label.stats?.total_columns ?? 0} columns)
                          </span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            {error && (
              <div className="flex items-center gap-2 text-destructive text-sm">
                <AlertCircle className="h-4 w-4" />
                {error}
              </div>
            )}

            <Button
              onClick={handleEvaluate}
              disabled={!selectedBatch || !selectedLabels || evaluating}
              className="w-full"
            >
              {evaluating ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Evaluating...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Run Evaluation
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Results Card */}
        <Card>
          <CardHeader>
            <CardTitle>Results</CardTitle>
            <CardDescription>
              {result
                ? `Evaluation completed: ${result.run_id}`
                : "Run an evaluation to see results"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {result ? (
              <div className="space-y-6">
                {/* Summary */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Evaluated</p>
                    <p className="text-2xl font-bold">{result.summary.evaluated_columns}</p>
                    <p className="text-xs text-muted-foreground">
                      of {result.summary.total_columns} columns
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">Skipped</p>
                    <p className="text-2xl font-bold">{result.summary.skipped_columns}</p>
                    <p className="text-xs text-muted-foreground">no ground truth</p>
                  </div>
                </div>

                {/* Metrics */}
                <div className="space-y-4">
                  <div>
                    <h4 className="font-medium mb-2 flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      Path-Level Metrics
                    </h4>
                    <div className="grid grid-cols-3 gap-2 text-sm">
                      <div className="bg-muted p-2 rounded">
                        <p className="text-muted-foreground">Precision</p>
                        <p className="font-mono">{formatPercent(result.metrics.path_level.macro_precision)}</p>
                      </div>
                      <div className="bg-muted p-2 rounded">
                        <p className="text-muted-foreground">Recall</p>
                        <p className="font-mono">{formatPercent(result.metrics.path_level.macro_recall)}</p>
                      </div>
                      <div className="bg-primary/10 p-2 rounded">
                        <p className="text-muted-foreground">F1</p>
                        <p className="font-mono font-bold">{formatPercent(result.metrics.path_level.macro_f1)}</p>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="font-medium mb-2 flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-blue-600" />
                      Node-Level Metrics
                    </h4>
                    <div className="grid grid-cols-3 gap-2 text-sm">
                      <div className="bg-muted p-2 rounded">
                        <p className="text-muted-foreground">Precision</p>
                        <p className="font-mono">{formatPercent(result.metrics.node_level.macro_precision)}</p>
                      </div>
                      <div className="bg-muted p-2 rounded">
                        <p className="text-muted-foreground">Recall</p>
                        <p className="font-mono">{formatPercent(result.metrics.node_level.macro_recall)}</p>
                      </div>
                      <div className="bg-primary/10 p-2 rounded">
                        <p className="text-muted-foreground">F1</p>
                        <p className="font-mono font-bold">{formatPercent(result.metrics.node_level.macro_f1)}</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Config */}
                <div className="text-xs text-muted-foreground">
                  <p>
                    Config: {result.config.mode} | {result.config.prompt_type} | max_depth={result.config.max_depth}
                  </p>
                  <p>Labels: {result.labels_id}</p>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <FileText className="h-12 w-12 mb-4" />
                <p>No evaluation results yet</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
