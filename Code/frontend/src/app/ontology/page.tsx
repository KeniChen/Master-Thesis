"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import Link from "next/link"
import { Network, Eye, Trash2, Upload, RefreshCw, FileUp, Loader2, AlertCircle } from "lucide-react"

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
import { ontologiesApi } from "@/lib/api"
import type { OntologyInfo } from "@/lib/types"

export default function OntologiesPage() {
  const [ontologies, setOntologies] = useState<OntologyInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Upload state
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Delete state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<OntologyInfo | null>(null)
  const [deleting, setDeleting] = useState(false)

  const fetchOntologies = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const list = await ontologiesApi.list()
      setOntologies(list)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch ontologies")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchOntologies()
  }, [fetchOntologies])

  const handleUpload = async () => {
    if (!uploadFile) return

    setUploading(true)
    setUploadError(null)
    try {
      await ontologiesApi.upload(uploadFile)
      setUploadDialogOpen(false)
      setUploadFile(null)
      await fetchOntologies()
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed")
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return

    setDeleting(true)
    try {
      await ontologiesApi.delete(deleteTarget.id)
      setDeleteDialogOpen(false)
      setDeleteTarget(null)
      await fetchOntologies()
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
        <Button onClick={fetchOntologies}>
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
          <h1 className="text-3xl font-bold tracking-tight">Ontologies</h1>
          <p className="text-muted-foreground">
            Manage RDF/OWL ontologies for semantic annotation.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchOntologies}>
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button size="sm" onClick={() => setUploadDialogOpen(true)}>
            <Upload className="h-4 w-4 mr-2" />
            Upload
          </Button>
        </div>
      </div>

      {ontologies.length === 0 ? (
        <Card className="p-12">
          <div className="flex flex-col items-center justify-center gap-4 text-center">
            <FileUp className="h-12 w-12 text-muted-foreground" />
            <div>
              <h3 className="text-lg font-semibold">No ontologies found</h3>
              <p className="text-muted-foreground">
                Upload an RDF/OWL file to get started
              </p>
            </div>
            <Button onClick={() => setUploadDialogOpen(true)}>
              <Upload className="h-4 w-4 mr-2" />
              Upload Ontology
            </Button>
          </div>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Network className="h-5 w-5" />
              Available Ontologies
            </CardTitle>
            <CardDescription>
              {ontologies.length} ontologies loaded from data directory
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>File Name</TableHead>
                  <TableHead>Classes</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {ontologies.map((onto) => (
                  <TableRow key={onto.id}>
                    <TableCell className="font-mono text-sm">{onto.id}</TableCell>
                    <TableCell className="font-medium">{onto.filename}</TableCell>
                    <TableCell>{onto.class_count}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button variant="ghost" size="icon" asChild>
                          <Link href={`/ontology/${encodeURIComponent(onto.id)}`}>
                            <Eye className="h-4 w-4" />
                          </Link>
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-destructive hover:text-destructive"
                          onClick={() => {
                            setDeleteTarget(onto)
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
            <DialogTitle>Upload Ontology</DialogTitle>
            <DialogDescription>
              Upload an RDF or OWL file containing your ontology.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <input
              ref={fileInputRef}
              type="file"
              accept=".rdf,.owl,.xml"
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
                    Supported formats: .rdf, .owl
                  </p>
                </div>
              )}
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

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Ontology</DialogTitle>
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
