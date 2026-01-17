"use client"

import { useState } from "react"
import { ChevronDown, ChevronRight, CheckCircle2, XCircle, AlertTriangle } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { LLMDetailPanel } from "./LLMDetailPanel"
import { EDMVotingView } from "./EDMVotingView"
import type { BFSStep } from "@/lib/types"

interface BFSStepCardProps {
  step: BFSStep
  stepIndex: number
  isLast: boolean
  defaultExpanded?: boolean
  mode: "single" | "edm"
  showReasoning?: boolean
}

export function BFSStepCard({
  step,
  stepIndex,
  isLast,
  defaultExpanded = false,
  mode,
  showReasoning = true,
}: BFSStepCardProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  const statusIcon = {
    completed: <CheckCircle2 className="h-4 w-4 text-green-500" />,
    failed: <XCircle className="h-4 w-4 text-red-500" />,
    terminated: <AlertTriangle className="h-4 w-4 text-yellow-500" />,
  }

  const statusColor = {
    completed: "border-green-200 dark:border-green-800",
    failed: "border-red-200 dark:border-red-800",
    terminated: "border-yellow-200 dark:border-yellow-800",
  }

  return (
    <div className="relative">
      {/* Connection line */}
      {stepIndex > 0 && (
        <div className="absolute -top-4 left-4 w-0.5 h-4 bg-border" />
      )}
      {!isLast && (
        <div className="absolute -bottom-4 left-4 w-0.5 h-4 bg-border" />
      )}

      <div
        className={`border rounded-lg overflow-hidden ${statusColor[step.status] || ""}`}
      >
        {/* Header */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center justify-between p-3 bg-muted/50 hover:bg-muted transition-colors"
        >
          <div className="flex items-center gap-2">
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            <Badge variant="outline">Level {step.level}</Badge>
            <span className="text-sm font-medium">Parent: {step.parent}</span>
            {statusIcon[step.status]}
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">{step.candidates.length} candidates</Badge>
            {step.selected.length > 0 && (
              <Badge variant="default" className="bg-green-500">
                {step.selected.length} selected
              </Badge>
            )}
          </div>
        </button>

        {/* Content */}
        {isExpanded && (
          <div className="p-4 space-y-4 border-t">
            {/* Candidates grid */}
            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Candidates
              </label>
              <div className="flex flex-wrap gap-1.5 mt-2">
                {step.candidates.map((candidate, idx) => {
                  const isSelected = step.selected.includes(candidate)
                  return (
                    <Badge
                      key={`${candidate}-${idx}`}
                      variant={isSelected ? "default" : "outline"}
                      className={isSelected ? "bg-green-500 hover:bg-green-600" : ""}
                    >
                      {isSelected && <CheckCircle2 className="mr-1 h-3 w-3" />}
                      {candidate}
                    </Badge>
                  )
                })}
              </div>
            </div>

            {/* Error message */}
            {step.error && (
              <div className="p-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg">
                <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
                  <XCircle className="h-4 w-4" />
                  <span className="text-sm font-medium">Error</span>
                </div>
                <p className="text-sm text-red-600 dark:text-red-400 mt-1">
                  {step.error}
                </p>
              </div>
            )}

            {/* Mode-specific view */}
            {mode === "edm" && step.edm_result ? (
              <EDMVotingView edmResult={step.edm_result} />
            ) : (
              <LLMDetailPanel
                request={step.llm_request}
                response={step.llm_response}
                showReasoning={showReasoning}
              />
            )}

            {/* Selected summary */}
            {step.selected.length > 0 && (
              <div className="pt-2 border-t">
                <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Selected
                </label>
                <div className="flex gap-1.5 mt-2">
                  {step.selected.map((s) => (
                    <Badge key={s} className="bg-green-500 hover:bg-green-600">
                      <CheckCircle2 className="mr-1 h-3 w-3" />
                      {s}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
