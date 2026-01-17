"use client"

import { useState } from "react"
import { ChevronDown, ChevronUp, Clock, MessageSquare, Lightbulb, CheckCircle2, Coins } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { LLMRequest, LLMResponse } from "@/lib/types"

interface LLMDetailPanelProps {
  request?: LLMRequest | null
  response?: LLMResponse | null
  showReasoning?: boolean
  defaultExpanded?: boolean
}

export function LLMDetailPanel({
  request,
  response,
  showReasoning = true,
  defaultExpanded = false,
}: LLMDetailPanelProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  if (!response) {
    return null
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      {/* Collapsed view - just answer */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 bg-muted/30 hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">LLM Response</span>
          {response.latency_ms && (
            <Badge variant="outline" className="text-xs">
              <Clock className="mr-1 h-3 w-3" />
              {response.latency_ms}ms
            </Badge>
          )}
          {(response.input_tokens || response.output_tokens) && (
            <Badge variant="outline" className="text-xs">
              <Coins className="mr-1 h-3 w-3" />
              {response.input_tokens ?? 0} in / {response.output_tokens ?? 0} out
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="font-mono text-xs">
            {response.answer || "No answer"}
          </Badge>
          {isExpanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </div>
      </button>

      {/* Expanded view */}
      {isExpanded && (
        <div className="p-4 space-y-4 border-t">
          {/* Request */}
          {request && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Request
                </span>
                <Badge variant="outline" className="text-xs">
                  {request.model}
                </Badge>
              </div>
              <ScrollArea className="h-[200px]">
                <pre className="text-xs font-mono p-3 bg-muted rounded-lg whitespace-pre-wrap break-words">
                  {request.prompt}
                </pre>
              </ScrollArea>
            </div>
          )}

          {/* Reasoning (CoT mode) */}
          {showReasoning && response.reasoning && (
            <div className="space-y-2">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                <Lightbulb className="h-4 w-4 text-amber-500" /> Reasoning
              </span>
              <div className="p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg">
                <p className="text-sm leading-relaxed whitespace-pre-wrap">
                  {response.reasoning}
                </p>
              </div>
            </div>
          )}

          {/* Answer */}
          <div className="space-y-2">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1">
              <CheckCircle2 className="h-4 w-4 text-green-500" /> Answer
            </span>
            <div className="p-3 bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-lg">
              <p className="text-sm font-medium">
                {response.answer || "No answer provided"}
              </p>
            </div>
          </div>

          {/* Raw response (collapsible) */}
          <details className="text-xs">
            <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
              View raw response
            </summary>
            <pre className="mt-2 p-2 bg-muted rounded text-xs font-mono overflow-auto max-h-[150px]">
              {response.raw}
            </pre>
          </details>
        </div>
      )}
    </div>
  )
}
