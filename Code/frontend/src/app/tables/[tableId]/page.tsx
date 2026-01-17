"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useParams } from "next/navigation"
import { ArrowLeft, Play, Code2, RefreshCw, AlertCircle } from "lucide-react"

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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import { tablesApi } from "@/lib/api"
import type { TablePreview } from "@/lib/types"

function generateMarkdownPreview(columns: string[], rows: Record<string, unknown>[]): string {
  if (columns.length === 0 || rows.length === 0) return ""

  const header = `| ${columns.join(" | ")} |`
  const separator = `|${columns.map(() => "---").join("|")}|`
  const dataRows = rows.map(
    (row) => `| ${columns.map((col) => String(row[col] ?? "")).join(" | ")} |`
  )

  return [header, separator, ...dataRows].join("\n")
}

export default function TableDetailPage() {
  const params = useParams()
  const tableId = params.tableId as string

  const [tableData, setTableData] = useState<TablePreview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchTable = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await tablesApi.get(decodeURIComponent(tableId), 20)
      setTableData(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load table")
    } finally {
      setLoading(false)
    }
  }, [tableId])

  useEffect(() => {
    if (tableId) {
      fetchTable()
    }
  }, [fetchTable, tableId])

  const markdownPreview = useMemo(() => {
    if (!tableData) return ""
    return generateMarkdownPreview(tableData.columns, tableData.rows)
  }, [tableData])

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/tables">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Link>
          </Button>
          <div className="space-y-2">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-48" />
          </div>
        </div>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-4 w-60" />
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/tables">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Link>
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Table Not Found</h1>
            <p className="text-muted-foreground">ID: {decodeURIComponent(tableId)}</p>
          </div>
        </div>
        <Card className="border-destructive">
          <CardContent className="flex flex-col items-center justify-center py-10">
            <AlertCircle className="h-12 w-12 text-destructive mb-4" />
            <p className="text-lg font-medium mb-2">Failed to load table</p>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button onClick={fetchTable}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Try Again
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!tableData) {
    return null
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/tables">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Link>
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{tableData.name}</h1>
            <p className="text-muted-foreground">
              ID: {tableData.id} | {tableData.columns.length} columns | {tableData.total_rows} rows
            </p>
          </div>
        </div>
        <Button asChild>
          <Link href={`/annotations/new?table=${encodeURIComponent(tableData.id)}`}>
            <Play className="mr-2 h-4 w-4" />
            Run Annotation
          </Link>
        </Button>
      </div>

      <Tabs defaultValue="preview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="preview">Data Preview</TabsTrigger>
          <TabsTrigger value="markdown">Markdown Preview</TabsTrigger>
        </TabsList>

        <TabsContent value="preview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Data Preview</CardTitle>
              <CardDescription>
                Showing {tableData.rows.length} of {tableData.total_rows} rows
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border overflow-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      {tableData.columns.map((col) => (
                        <TableHead key={col} className="whitespace-nowrap">
                          {col}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tableData.rows.map((row, i) => (
                      <TableRow key={i}>
                        {tableData.columns.map((col) => (
                          <TableCell key={col} className="whitespace-nowrap">
                            {String(row[col] ?? "")}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="markdown" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Code2 className="h-5 w-5" />
                Markdown Preview
              </CardTitle>
              <CardDescription>
                This is how the table appears to the LLM during annotation
              </CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="rounded-lg bg-muted p-4 overflow-auto text-sm font-mono">
                {markdownPreview}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
