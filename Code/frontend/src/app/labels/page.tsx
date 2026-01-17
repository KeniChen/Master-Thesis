"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { FileText, Eye, Trash2, Upload, RefreshCw, FileUp, Loader2, AlertCircle } from "lucide-react"

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
import { labelsApi } from "@/lib/api"
import type { LabelsInfo, LabelsPreview } from "@/lib/types"

export default function LabelsPage() {
  const [labels, setLabels] = useState<LabelsInfo[]>([])
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
  const [previewTarget, setPreviewTarget] = useState<LabelsInfo | null>(null)
  const [previewData, setPreviewData] = useState<LabelsPreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  // Delete state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<LabelsInfo | null>(null)
  const [deleting, setDeleting] = useState(false)

  const fetchLabels = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const list = await labelsApi.list()
      setLabels(list)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch labels")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchLabels()
  }, [fetchLabels])

  const handleUpload = async () => {
    if (!uploadFile) return

    setUploading(true)
    setUploadError(null)
    try {
      await labelsApi.upload(uploadFile)
      setUploadDialogOpen(false)
      setUploadFile(null)
      await fetchLabels()
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed")
    } finally {
      setUploading(false)
    }
  }

  const handlePreview = async (label: LabelsInfo) => {
    setPreviewTarget(label)
    setPreviewDialogOpen(true)
    setPreviewLoading(true)
    setPreviewData(null)
    try {
      const data = await labelsApi.preview(label.id, 10)
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
      await labelsApi.delete(deleteTarget.id)
      setDeleteDialogOpen(false)
      setDeleteTarget(null)
      await fetchLabels()
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
        <Button onClick={fetchLabels}>
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
          <h1 className="text-3xl font-bold tracking-tight">Ground Truth Labels</h1>
          <p className="text-muted-foreground">
            Manage ground truth label files for evaluation.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchLabels}>
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button size="sm" onClick={() => setUploadDialogOpen(true)}>
            <Upload className="h-4 w-4 mr-2" />
            Upload
          </Button>
        </div>
      </div>

      {labels.length === 0 ? (
        <Card className="p-12">
          <div className="flex flex-col items-center justify-center gap-4 text-center">
            <FileUp className="h-12 w-12 text-muted-foreground" />
            <div>
              <h3 className="text-lg font-semibold">No labels found</h3>
              <p className="text-muted-foreground">
                Upload a CSV file containing ground truth labels
              </p>
            </div>
            <Button onClick={() => setUploadDialogOpen(true)}>
              <Upload className="h-4 w-4 mr-2" />
              Upload Labels
            </Button>
          </div>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Available Labels
            </CardTitle>
            <CardDescription>
              {labels.length} label files loaded from data directory
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>File</TableHead>
                  <TableHead>Tables</TableHead>
                  <TableHead>Columns</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {labels.map((label) => (
                  <TableRow key={label.id}>
                    <TableCell className="font-medium">{label.name}</TableCell>
                    <TableCell className="font-mono text-sm">{label.filename}</TableCell>
                    <TableCell>{label.stats?.total_tables ?? "-"}</TableCell>
                    <TableCell>{label.stats?.total_columns ?? "-"}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handlePreview(label)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-destructive hover:text-destructive"
                          onClick={() => {
                            setDeleteTarget(label)
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
            <DialogTitle>Upload Labels</DialogTitle>
            <DialogDescription>
              Upload a CSV file containing ground truth labels.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
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
                    Supported format: .csv
                  </p>
                </div>
              )}
            </div>
            <div className="text-xs text-muted-foreground space-y-1">
              <p><strong>Expected columns:</strong></p>
              <ul className="list-disc list-inside">
                <li>table_id, column_id, column_name</li>
                <li>class1_level1_name, class1_level2_name</li>
                <li>class2_level1_name, class2_level2_name (optional)</li>
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
              Showing first {previewData?.preview_rows ?? 0} of {previewData?.total_rows ?? 0} rows
            </DialogDescription>
          </DialogHeader>
          {previewLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : previewData ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    {previewData.columns.map((col) => (
                      <TableHead key={col} className="whitespace-nowrap">
                        {col}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {previewData.rows.map((row, idx) => (
                    <TableRow key={idx}>
                      {previewData.columns.map((col) => (
                        <TableCell key={col} className="whitespace-nowrap">
                          {String(row[col] ?? "-")}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
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
            <DialogTitle>Delete Labels</DialogTitle>
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
