"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { FolderArchive, Eye, Trash2, Upload, RefreshCw, FileUp, Loader2, AlertCircle } from "lucide-react"

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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { batchesApi } from "@/lib/api"
import type { BatchInfo, BatchPreview } from "@/lib/types"

export default function BatchesPage() {
  const [batches, setBatches] = useState<BatchInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Upload state
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Preview state
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false)
  const [previewTarget, setPreviewTarget] = useState<BatchInfo | null>(null)
  const [previewData, setPreviewData] = useState<BatchPreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  // Delete state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<BatchInfo | null>(null)
  const [deleting, setDeleting] = useState(false)

  const fetchBatches = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const list = await batchesApi.list()
      setBatches(list)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch batches")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchBatches()
  }, [fetchBatches])

  const handleUpload = async () => {
    if (!uploadFile) return

    setUploading(true)
    setUploadError(null)
    try {
      await batchesApi.upload(uploadFile)
      setUploadDialogOpen(false)
      setUploadFile(null)
      await fetchBatches()
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed")
    } finally {
      setUploading(false)
    }
  }

  const handlePreview = async (batch: BatchInfo) => {
    setPreviewTarget(batch)
    setPreviewDialogOpen(true)
    setPreviewLoading(true)
    setPreviewData(null)
    try {
      const data = await batchesApi.preview(batch.id, 5)
      setPreviewData(data)
    } catch (err) {
      console.error("Preview failed:", err)
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return

    setDeleting(true)
    try {
      await batchesApi.delete(deleteTarget.id)
      setDeleteDialogOpen(false)
      setDeleteTarget(null)
      await fetchBatches()
    } catch (err) {
      console.error("Delete failed:", err)
    } finally {
      setDeleting(false)
    }
  }

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
        <Button onClick={fetchBatches}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Batch Results</h1>
          <p className="text-muted-foreground">
            Manage experiment batch result files for evaluation.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchBatches}>
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button size="sm" onClick={() => setUploadDialogOpen(true)}>
            <Upload className="h-4 w-4 mr-2" />
            Upload
          </Button>
        </div>
      </div>

      {batches.length === 0 ? (
        <Card className="p-12">
          <div className="flex flex-col items-center justify-center gap-4 text-center">
            <FileUp className="h-12 w-12 text-muted-foreground" />
            <div>
              <h3 className="text-lg font-semibold">No batch files found</h3>
              <p className="text-muted-foreground">
                Upload a batch JSON file from experiment runs
              </p>
            </div>
            <Button onClick={() => setUploadDialogOpen(true)}>
              <Upload className="h-4 w-4 mr-2" />
              Upload Batch
            </Button>
          </div>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FolderArchive className="h-5 w-5" />
              Available Batches
            </CardTitle>
            <CardDescription>
              {batches.length} batch files loaded from data directory
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Config</TableHead>
                  <TableHead>Tables</TableHead>
                  <TableHead>Columns</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {batches.map((batch) => (
                  <TableRow key={batch.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{batch.name}</p>
                        <p className="text-xs text-muted-foreground font-mono">
                          {batch.filename}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        <Badge variant="outline">{batch.config.mode}</Badge>
                        <Badge variant="outline">{batch.config.prompt_type}</Badge>
                        {batch.config.ontology_id && (
                          <Badge variant="secondary">
                            {batch.config.ontology_id.replace(".rdf", "")}
                          </Badge>
                        )}
                        {batch.config.provider && (
                          <Badge variant="outline" className="bg-blue-50">
                            {batch.config.provider}
                          </Badge>
                        )}
                        {batch.config.model && (
                          <Badge variant="outline" className="bg-purple-50 text-xs">
                            {batch.config.model}
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>{batch.stats.total_tables}</TableCell>
                    <TableCell>
                      <span className="text-green-600">{batch.stats.completed_columns}</span>
                      <span className="text-muted-foreground"> / {batch.stats.total_columns}</span>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handlePreview(batch)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-destructive hover:text-destructive"
                          onClick={() => {
                            setDeleteTarget(batch)
                            setDeleteDialogOpen(true)
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Upload Dialog */}
      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upload Batch</DialogTitle>
            <DialogDescription>
              Upload a batch JSON file from experiment runs.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) setUploadFile(file)
              }}
            />
            <div
              className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => fileInputRef.current?.click()}
            >
              {uploadFile ? (
                <div className="flex items-center justify-center gap-2">
                  <FileUp className="h-6 w-6 text-primary" />
                  <span className="font-medium">{uploadFile.name}</span>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <Upload className="h-8 w-8 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    Click to select a file or drag and drop
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Supported format: .json (batch_*.json)
                  </p>
                </div>
              )}
            </div>
            <div className="text-xs text-muted-foreground space-y-1">
              <p><strong>Expected format:</strong></p>
              <ul className="list-disc list-inside">
                <li>run_id, config, tables array</li>
                <li>Each table has columns with final_paths</li>
              </ul>
            </div>
            {uploadError && (
              <p className="text-sm text-destructive">{uploadError}</p>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setUploadDialogOpen(false)
                setUploadFile(null)
                setUploadError(null)
              }}
            >
              Cancel
            </Button>
            <Button onClick={handleUpload} disabled={!uploadFile || uploading}>
              {uploading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Upload
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Preview Dialog */}
      <Dialog open={previewDialogOpen} onOpenChange={setPreviewDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>Preview: {previewTarget?.filename}</DialogTitle>
            <DialogDescription>
              Showing {previewData?.preview_tables ?? 0} of {previewData?.total_tables ?? 0} tables
            </DialogDescription>
          </DialogHeader>
          {previewLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : previewData ? (
            <div className="space-y-4">
              {/* Summary */}
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="bg-muted p-3 rounded">
                  <p className="text-muted-foreground">Mode</p>
                  <p className="font-medium">{previewData.config.mode}</p>
                </div>
                <div className="bg-muted p-3 rounded">
                  <p className="text-muted-foreground">Prompt Type</p>
                  <p className="font-medium">{previewData.config.prompt_type}</p>
                </div>
                <div className="bg-muted p-3 rounded">
                  <p className="text-muted-foreground">Ontology</p>
                  <p className="font-medium">{previewData.config.ontology_id}</p>
                </div>
                {(previewData.config.provider || previewData.config.model) && (
                  <>
                    <div className="bg-muted p-3 rounded">
                      <p className="text-muted-foreground">Provider</p>
                      <p className="font-medium">{previewData.config.provider || "-"}</p>
                    </div>
                    <div className="bg-muted p-3 rounded col-span-2">
                      <p className="text-muted-foreground">Model</p>
                      <p className="font-medium font-mono text-xs">{previewData.config.model || "-"}</p>
                    </div>
                  </>
                )}
              </div>

              {/* Tables preview */}
              {previewData.tables.map((table, idx) => (
                <div key={idx} className="border rounded p-3">
                  <div className="flex items-center justify-between mb-2">
                    <p className="font-medium">{table.table_name || table.table_id}</p>
                    <Badge variant="outline">
                      {table.columns.length} / {table.total_columns} columns shown
                    </Badge>
                  </div>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Column</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Predicted Paths</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {table.columns.map((col, cidx) => (
                        <TableRow key={cidx}>
                          <TableCell className="font-mono text-sm">{col.column_name}</TableCell>
                          <TableCell>
                            <Badge variant={col.status === "completed" ? "default" : "secondary"}>
                              {col.status}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm">
                            {col.final_paths.length > 0
                              ? col.final_paths.map(p => p.join(" / ")).join(" | ")
                              : "-"
                            }
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ))}
            </div>
          ) : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setPreviewDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Batch</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &quot;{deleteTarget?.filename}&quot;? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setDeleteDialogOpen(false)
                setDeleteTarget(null)
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
