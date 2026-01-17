"use client"

import { useState, useEffect, useMemo } from "react"
import Link from "next/link"
import { Plus, CheckCircle2, XCircle, Clock, Filter, Trash2, Loader2, Eye } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { runsApi } from "@/lib/api"
import type { RunListItem, RunStatus, DecisionMode } from "@/lib/types"

const statusIcons: Record<RunStatus, React.ReactNode> = {
  completed: <CheckCircle2 className="h-4 w-4 text-green-500" />,
  failed: <XCircle className="h-4 w-4 text-red-500" />,
  running: <Clock className="h-4 w-4 text-yellow-500 animate-pulse" />,
  pending: <Clock className="h-4 w-4 text-muted-foreground" />,
  partial: <CheckCircle2 className="h-4 w-4 text-yellow-500" />,
}

const modeColors: Record<DecisionMode, string> = {
  single: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  edm: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleString()
}

function formatMode(run: RunListItem) {
  const modeLabel = run.mode === "single" ? "Single" : "EDM"
  const promptLabel = run.prompt_type === "direct" ? "Direct" : "CoT"
  return `${modeLabel} ${promptLabel}`
}

export default function AnnotationsPage() {
  const [runs, setRuns] = useState<RunListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState("all")
  const [modeFilter, setModeFilter] = useState("all")

  useEffect(() => {
    runsApi.list()
      .then(setRuns)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const filteredRuns = useMemo(() => {
    return runs.filter(run => {
      if (statusFilter !== "all" && run.status !== statusFilter) return false
      if (modeFilter !== "all" && run.mode !== modeFilter) return false
      return true
    })
  }, [runs, statusFilter, modeFilter])

  const handleDelete = async (runId: string) => {
    if (confirm("Are you sure you want to delete this run?")) {
      try {
        await runsApi.delete(runId)
        setRuns(prev => prev.filter(r => r.run_id !== runId))
      } catch (error) {
        console.error("Failed to delete run:", error)
      }
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Annotation Runs</h1>
          <p className="text-muted-foreground">
            View and manage semantic annotation runs.
          </p>
        </div>
        <Button asChild>
          <Link href="/annotations/new">
            <Plus className="mr-2 h-4 w-4" />
            New Run
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Run History</CardTitle>
              <CardDescription>
                {loading ? "Loading..." : `${filteredRuns.length} annotation runs`}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[120px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="running">Running</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>
              <Select value={modeFilter} onValueChange={setModeFilter}>
                <SelectTrigger className="w-[100px]">
                  <SelectValue placeholder="Mode" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Modes</SelectItem>
                  <SelectItem value="single">Single</SelectItem>
                  <SelectItem value="edm">EDM</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : filteredRuns.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {runs.length === 0 ? "No annotation runs yet. Create one to get started!" : "No runs match the selected filters."}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Status</TableHead>
                  <TableHead>Run ID</TableHead>
                  <TableHead>Table</TableHead>
                  <TableHead>Mode</TableHead>
                  <TableHead className="text-right">Columns</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRuns.map((run) => (
                  <TableRow key={run.run_id}>
                    <TableCell>
                      {statusIcons[run.status]}
                    </TableCell>
                    <TableCell>
                      <Link
                        href={`/annotations/${run.run_id}`}
                        className="font-medium hover:underline"
                      >
                        {run.run_id}
                      </Link>
                    </TableCell>
                    <TableCell>{run.table_name}</TableCell>
                    <TableCell>
                      <Badge
                        variant="secondary"
                        className={modeColors[run.mode]}
                      >
                        {formatMode(run)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">{run.column_count}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDate(run.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button variant="ghost" size="icon" asChild>
                          <Link href={`/annotations/${run.run_id}`}>
                            <Eye className="h-4 w-4" />
                          </Link>
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(run.run_id)}
                          className="text-red-500 hover:text-red-700 hover:bg-red-100"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
