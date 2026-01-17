"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { ArrowLeft, Play, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { tablesApi, ontologiesApi, runsApi } from "@/lib/api"
import type { TableInfo, OntologyInfo, DecisionMode, PromptType } from "@/lib/types"

export default function NewAnnotationPage() {
  const router = useRouter()

  // Data states
  const [tables, setTables] = useState<TableInfo[]>([])
  const [ontologies, setOntologies] = useState<OntologyInfo[]>([])
  const [loading, setLoading] = useState(true)

  // Selection states
  const [selectedTable, setSelectedTable] = useState<string>("")
  const [selectedOntology, setSelectedOntology] = useState<string>("")
  const [selectedColumns, setSelectedColumns] = useState<Set<string>>(new Set())
  const [tableColumns, setTableColumns] = useState<string[]>([])

  // Configuration states
  const [mode, setMode] = useState<DecisionMode>("single")
  const [promptType, setPromptType] = useState<PromptType>("cot")
  const [maxDepth, setMaxDepth] = useState(3)
  const [sampleRows, setSampleRows] = useState(5)
  const [edmConfig, setEdmConfig] = useState({
    classesPerAgent: 30,
    agentsPerClass: 3,
    consensusThreshold: 0.8,
  })

  // Submission state
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load tables and ontologies on mount
  useEffect(() => {
    async function loadData() {
      try {
        const [tablesData, ontologiesData] = await Promise.all([
          tablesApi.list(),
          ontologiesApi.list(),
        ])
        setTables(tablesData)
        setOntologies(ontologiesData)
      } catch (err) {
        console.error("Failed to load data:", err)
        setError("Failed to load tables and ontologies")
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  // Load columns when table is selected
  useEffect(() => {
    if (selectedTable) {
      const table = tables.find(t => t.id === selectedTable)
      if (table) {
        setTableColumns(table.columns)
        setSelectedColumns(new Set()) // Reset selection
      }
    } else {
      setTableColumns([])
      setSelectedColumns(new Set())
    }
  }, [selectedTable, tables])

  const toggleColumn = (column: string) => {
    setSelectedColumns((prev) => {
      const next = new Set(prev)
      if (next.has(column)) {
        next.delete(column)
      } else {
        next.add(column)
      }
      return next
    })
  }

  const selectAllColumns = () => {
    setSelectedColumns(new Set(tableColumns))
  }

  const clearAllColumns = () => {
    setSelectedColumns(new Set())
  }

  const handleSubmit = async () => {
    setIsSubmitting(true)
    setError(null)

    try {
      const response = await runsApi.create({
        table_id: selectedTable,
        ontology_id: selectedOntology,
        columns: Array.from(selectedColumns),
        mode,
        prompt_type: promptType,
        max_depth: maxDepth,
        k: sampleRows,
        edm_options: mode === "edm" ? {
          classes_per_agent: edmConfig.classesPerAgent,
          agents_per_class: edmConfig.agentsPerClass,
          consensus_threshold: edmConfig.consensusThreshold,
        } : undefined,
      })

      // Redirect to the run detail page
      router.push(`/annotations/${response.run_id}`)
    } catch (err) {
      console.error("Failed to create run:", err)
      setError(err instanceof Error ? err.message : "Failed to create annotation run")
      setIsSubmitting(false)
    }
  }

  const isValid = selectedTable && selectedOntology && selectedColumns.size > 0

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/annotations">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">New Annotation Run</h1>
          <p className="text-muted-foreground">
            Configure and start a new semantic annotation.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Step 1: Select Table */}
        <Card>
          <CardHeader>
            <CardTitle>Step 1: Select Table</CardTitle>
            <CardDescription>Choose a table to annotate</CardDescription>
          </CardHeader>
          <CardContent>
            <Select value={selectedTable} onValueChange={setSelectedTable}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select a table..." />
              </SelectTrigger>
              <SelectContent>
                {tables.map((table) => (
                  <SelectItem key={table.id} value={table.id}>
                    {table.name} ({table.columns.length} columns)
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {tables.length === 0 && (
              <p className="text-sm text-muted-foreground mt-2">
                No tables available. <Link href="/tables" className="text-primary hover:underline">Upload one</Link> first.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Step 2: Select Ontology */}
        <Card>
          <CardHeader>
            <CardTitle>Step 2: Select Ontology</CardTitle>
            <CardDescription>Choose an ontology for annotation</CardDescription>
          </CardHeader>
          <CardContent>
            <Select value={selectedOntology} onValueChange={setSelectedOntology}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select an ontology..." />
              </SelectTrigger>
              <SelectContent>
                {ontologies.map((ontology) => (
                  <SelectItem key={ontology.id} value={ontology.id}>
                    {ontology.filename || ontology.id} ({ontology.class_count} classes)
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {ontologies.length === 0 && (
              <p className="text-sm text-muted-foreground mt-2">
                No ontologies available. <Link href="/ontology" className="text-primary hover:underline">Upload one</Link> first.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Step 3: Select Columns */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Step 3: Select Columns</CardTitle>
                <CardDescription>
                  {selectedColumns.size} columns selected
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={selectAllColumns} disabled={!selectedTable}>
                  Select All
                </Button>
                <Button variant="outline" size="sm" onClick={clearAllColumns} disabled={!selectedTable}>
                  Clear
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {selectedTable ? (
              tableColumns.length > 0 ? (
                <div className="grid gap-2 max-h-[200px] overflow-y-auto">
                  {tableColumns.map((column) => (
                    <div key={column} className="flex items-center space-x-2">
                      <Checkbox
                        id={column}
                        checked={selectedColumns.has(column)}
                        onCheckedChange={() => toggleColumn(column)}
                      />
                      <label
                        htmlFor={column}
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                      >
                        {column}
                      </label>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No columns found in this table.
                </p>
              )
            ) : (
              <p className="text-sm text-muted-foreground">
                Please select a table first.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Step 4: Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>Step 4: Configuration</CardTitle>
            <CardDescription>Set annotation parameters</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Decision Mode */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Decision Mode</label>
              <div className="flex gap-2">
                <Button
                  variant={mode === "single" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setMode("single")}
                >
                  Single
                </Button>
                <Button
                  variant={mode === "edm" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setMode("edm")}
                >
                  EDM
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                {mode === "single" && "Single agent makes decisions"}
                {mode === "edm" && "Multiple agents vote on decisions (Ensemble Decision Making)"}
              </p>
            </div>

            {/* Prompt Type */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Prompt Type</label>
              <div className="flex gap-2">
                <Button
                  variant={promptType === "direct" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setPromptType("direct")}
                >
                  Direct
                </Button>
                <Button
                  variant={promptType === "cot" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setPromptType("cot")}
                >
                  CoT
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                {promptType === "direct" && "Direct answer without reasoning"}
                {promptType === "cot" && "Chain-of-thought reasoning before answer"}
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              {/* Max Depth */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Max Depth</label>
                <Input
                  type="number"
                  min={1}
                  max={10}
                  value={maxDepth}
                  onChange={(e) => setMaxDepth(parseInt(e.target.value) || 1)}
                />
                <p className="text-xs text-muted-foreground">
                  Maximum ontology hierarchy depth
                </p>
              </div>

              {/* Sample Rows */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Sample Rows (k)</label>
                <Input
                  type="number"
                  min={1}
                  max={20}
                  value={sampleRows}
                  onChange={(e) => setSampleRows(parseInt(e.target.value) || 1)}
                />
                <p className="text-xs text-muted-foreground">
                  Number of table rows to include
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* EDM Options - Only show when EDM mode is selected */}
        {mode === "edm" && (
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>EDM Options</CardTitle>
              <CardDescription>Configure ensemble decision making parameters</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 md:grid-cols-3">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Classes per Agent</label>
                  <Input
                    type="number"
                    min={1}
                    value={edmConfig.classesPerAgent}
                    onChange={(e) =>
                      setEdmConfig((prev) => ({
                        ...prev,
                        classesPerAgent: parseInt(e.target.value) || 1,
                      }))
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Number of ontology classes each agent sees
                  </p>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Agents per Class</label>
                  <Input
                    type="number"
                    min={1}
                    value={edmConfig.agentsPerClass}
                    onChange={(e) =>
                      setEdmConfig((prev) => ({
                        ...prev,
                        agentsPerClass: parseInt(e.target.value) || 1,
                      }))
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Number of agents that see each class
                  </p>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Consensus Threshold</label>
                  <Input
                    type="number"
                    min={0}
                    max={1}
                    step={0.1}
                    value={edmConfig.consensusThreshold}
                    onChange={(e) =>
                      setEdmConfig((prev) => ({
                        ...prev,
                        consensusThreshold: parseFloat(e.target.value) || 0,
                      }))
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Minimum vote percentage to select a class (0-1)
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-4">
        <Button variant="outline" asChild>
          <Link href="/annotations">Cancel</Link>
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={!isValid || isSubmitting}
        >
          {isSubmitting ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Creating...
            </>
          ) : (
            <>
              <Play className="mr-2 h-4 w-4" />
              Start Annotation
            </>
          )}
        </Button>
      </div>
    </div>
  )
}
