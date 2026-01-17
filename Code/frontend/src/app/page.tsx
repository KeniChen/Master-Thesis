"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import {
  Table2,
  Network,
  Play,
  History,
  ArrowRight,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
} from "lucide-react"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { tablesApi, ontologiesApi, runsApi, providersApi, healthApi } from "@/lib/api"
import type { RunListItem, RunStatus } from "@/lib/types"

interface Stats {
  tables: number
  columns: number
  ontologies: number
  runs: number
}

interface SystemStatus {
  provider?: string
  model?: string
  online: boolean
}

const statusIcons: Record<RunStatus, React.ReactNode> = {
  completed: <CheckCircle2 className="h-4 w-4 text-green-500" />,
  failed: <XCircle className="h-4 w-4 text-red-500" />,
  running: <Clock className="h-4 w-4 text-yellow-500 animate-pulse" />,
  pending: <Clock className="h-4 w-4 text-muted-foreground" />,
  partial: <CheckCircle2 className="h-4 w-4 text-yellow-500" />,
}

function formatMode(run: RunListItem) {
  const modeLabel = run.mode === "single" ? "Single" : "EDM"
  const promptLabel = run.prompt_type === "direct" ? "Direct" : "CoT"
  return `${modeLabel} ${promptLabel}`
}

function formatTimeAgo(dateString: string) {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return "just now"
  if (diffMins < 60) return `${diffMins} min ago`
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`
  return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats>({ tables: 0, columns: 0, ontologies: 0, runs: 0 })
  const [recentRuns, setRecentRuns] = useState<RunListItem[]>([])
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({ online: false })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const [tables, ontologies, runs, providers, health] = await Promise.all([
          tablesApi.list().catch(() => []),
          ontologiesApi.list().catch(() => []),
          runsApi.list().catch(() => []),
          providersApi.list().catch(() => null),
          healthApi.check().catch(() => ({ status: "error" })),
        ])

        setStats({
          tables: tables.length,
          columns: tables.reduce((sum, t) => sum + (t.columns?.length || 0), 0),
          ontologies: ontologies.length,
          runs: runs.length,
        })

        setRecentRuns(runs.slice(0, 3))

        if (providers) {
          const activeProviderName = providers.active_provider
          const activeProviderConfig = providers.providers[activeProviderName]
          setSystemStatus({
            provider: activeProviderName,
            model: activeProviderConfig?.config?.default_model as string | undefined,
            online: health.status === "ok",
          })
        } else {
          setSystemStatus({ online: health.status === "ok" })
        }
      } catch (error) {
        console.error("Failed to fetch dashboard data:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome to SAED-LLM Visualization. Monitor and manage semantic annotations.
        </p>
      </div>

      {/* Quick Action Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="hover:border-primary/50 transition-colors">
          <Link href="/tables">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Tables</CardTitle>
              <Table2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.tables}</div>
              <p className="text-xs text-muted-foreground">
                {stats.columns} columns total
              </p>
            </CardContent>
          </Link>
        </Card>

        <Card className="hover:border-primary/50 transition-colors">
          <Link href="/ontology">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Ontologies</CardTitle>
              <Network className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.ontologies}</div>
              <p className="text-xs text-muted-foreground">
                Available for annotation
              </p>
            </CardContent>
          </Link>
        </Card>

        <Card className="hover:border-primary/50 transition-colors">
          <Link href="/annotations/new">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">New Run</CardTitle>
              <Play className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">Start</div>
              <p className="text-xs text-muted-foreground">
                Create new annotation
              </p>
            </CardContent>
          </Link>
        </Card>

        <Card className="hover:border-primary/50 transition-colors">
          <Link href="/annotations">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Run History</CardTitle>
              <History className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.runs}</div>
              <p className="text-xs text-muted-foreground">
                Total annotation runs
              </p>
            </CardContent>
          </Link>
        </Card>
      </div>

      {/* Recent Runs */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recent Runs</CardTitle>
            <CardDescription>
              Latest annotation runs and their status
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link href="/annotations">
              View All
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          {recentRuns.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No annotation runs yet. <Link href="/annotations/new" className="text-primary hover:underline">Create one</Link> to get started!
            </div>
          ) : (
            <div className="space-y-4">
              {recentRuns.map((run) => (
                <div
                  key={run.run_id}
                  className="flex items-center justify-between rounded-lg border p-4 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    {statusIcons[run.status]}
                    <div>
                      <Link
                        href={`/annotations/${run.run_id}`}
                        className="font-medium hover:underline"
                      >
                        {run.run_id}
                      </Link>
                      <p className="text-sm text-muted-foreground">
                        {run.table_name} - {run.column_count} columns
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <Badge variant="secondary">{formatMode(run)}</Badge>
                    <span className="text-sm text-muted-foreground">{formatTimeAgo(run.created_at)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* System Status */}
      <Card>
        <CardHeader>
          <CardTitle>System Status</CardTitle>
          <CardDescription>
            Current configuration and connection status
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            {systemStatus.provider && (
              <div className="flex items-center gap-2 rounded-lg border px-3 py-2">
                <div className={`h-2 w-2 rounded-full ${systemStatus.online ? "bg-green-500" : "bg-red-500"}`} />
                <span className="text-sm font-medium">LLM: {systemStatus.provider}</span>
                {systemStatus.model && (
                  <span className="text-sm text-muted-foreground">({systemStatus.model})</span>
                )}
              </div>
            )}
            <div className="flex items-center gap-2 rounded-lg border px-3 py-2">
              <div className={`h-2 w-2 rounded-full ${systemStatus.online ? "bg-green-500" : "bg-red-500"}`} />
              <span className="text-sm font-medium">API: {systemStatus.online ? "Online" : "Offline"}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
