"use client"

import { useState } from "react"
import { ChevronDown, ChevronUp, CheckCircle2, Users } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { LLMDetailPanel } from "./LLMDetailPanel"
import type { EDMResult, AgentResult } from "@/lib/types"

interface EDMVotingViewProps {
  edmResult: EDMResult
  showAgentDetails?: boolean
}

const INITIAL_VOTES_SHOWN = 5

export function EDMVotingView({
  edmResult,
  showAgentDetails = true,
}: EDMVotingViewProps) {
  const [expandedAgents, setExpandedAgents] = useState<Set<number>>(new Set())
  const [showAllVotes, setShowAllVotes] = useState(false)

  const toggleAgent = (agentId: number) => {
    setExpandedAgents((prev) => {
      const next = new Set(prev)
      if (next.has(agentId)) {
        next.delete(agentId)
      } else {
        next.add(agentId)
      }
      return next
    })
  }

  const thresholdPercent = edmResult.consensus_threshold * 100

  return (
    <div className="space-y-4">
      {/* Voting Summary */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Voting Results
          </span>
          <Badge variant="outline">
            <Users className="mr-1 h-3 w-3" />
            {edmResult.total_agents} agents | {thresholdPercent}% threshold
          </Badge>
        </div>

        <div className="space-y-2">
          {(showAllVotes ? edmResult.votes_summary : edmResult.votes_summary.slice(0, INITIAL_VOTES_SHOWN)).map((vote, idx) => {
            const percentage = vote.percentage * 100
            const isSelected = vote.selected

            return (
              <div key={`${vote.class_name}-${idx}`} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    {isSelected && (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    )}
                    <span className={isSelected ? "font-medium" : ""}>
                      {vote.class_name}
                    </span>
                  </div>
                  <span className="text-muted-foreground">
                    {vote.vote_count}/{vote.total_agents} ({percentage.toFixed(0)}%)
                  </span>
                </div>
                <div className="relative">
                  <Progress
                    value={percentage}
                    className={`h-2 ${isSelected ? "[&>div]:bg-green-500" : ""}`}
                  />
                  {/* Threshold line */}
                  <div
                    className="absolute top-0 bottom-0 w-0.5 bg-red-400"
                    style={{ left: `${thresholdPercent}%` }}
                    title={`Threshold: ${thresholdPercent}%`}
                  />
                </div>
              </div>
            )
          })}
          {edmResult.votes_summary.length > INITIAL_VOTES_SHOWN && (
            <button
              onClick={() => setShowAllVotes(!showAllVotes)}
              className="w-full py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded transition-colors flex items-center justify-center gap-1"
            >
              {showAllVotes ? (
                <>
                  <ChevronUp className="h-3 w-3" />
                  Show less
                </>
              ) : (
                <>
                  <ChevronDown className="h-3 w-3" />
                  Show {edmResult.votes_summary.length - INITIAL_VOTES_SHOWN} more
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Agent Details */}
      {showAgentDetails && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Agent Details
            </span>
            <button
              onClick={() => {
                if (expandedAgents.size === edmResult.agents.length) {
                  setExpandedAgents(new Set())
                } else {
                  setExpandedAgents(new Set(edmResult.agents.map((a) => a.agent_id)))
                }
              }}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              {expandedAgents.size === edmResult.agents.length ? "Collapse all" : "Expand all"}
            </button>
          </div>

          <div className="space-y-2">
            {edmResult.agents.map((agent) => (
              <AgentCard
                key={agent.agent_id}
                agent={agent}
                isExpanded={expandedAgents.has(agent.agent_id)}
                onToggle={() => toggleAgent(agent.agent_id)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

interface AgentCardProps {
  agent: AgentResult
  isExpanded: boolean
  onToggle: () => void
}

function AgentCard({ agent, isExpanded, onToggle }: AgentCardProps) {
  const hasError = agent.status === "failed"

  return (
    <div className={`border rounded-lg overflow-hidden ${hasError ? "border-red-300" : ""}`}>
      <button
        onClick={onToggle}
        className={`w-full flex items-center justify-between p-2 hover:bg-muted/50 transition-colors ${
          hasError ? "bg-red-50 dark:bg-red-950/20" : "bg-muted/30"
        }`}
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronUp className="h-4 w-4" />
          )}
          <Badge variant="outline" className="text-xs">
            Agent {agent.agent_id}
          </Badge>
          <span className="text-xs text-muted-foreground">
            Saw {agent.assigned_classes.length} classes
          </span>
        </div>
        <div className="flex items-center gap-1">
          {hasError ? (
            <Badge variant="destructive" className="text-xs">
              Failed
            </Badge>
          ) : (
            agent.voted_classes.map((cls) => (
              <Badge key={cls} variant="secondary" className="text-xs">
                {cls}
              </Badge>
            ))
          )}
        </div>
      </button>

      {isExpanded && (
        <div className="p-3 border-t space-y-3">
          {/* Assigned classes */}
          <div>
            <span className="text-xs font-medium text-muted-foreground">
              Assigned Classes:
            </span>
            <div className="flex flex-wrap gap-1 mt-1">
              {agent.assigned_classes.map((cls, idx) => (
                <Badge
                  key={`${cls}-${idx}`}
                  variant={agent.voted_classes.includes(cls) ? "default" : "outline"}
                  className="text-xs"
                >
                  {agent.voted_classes.includes(cls) && (
                    <CheckCircle2 className="mr-1 h-3 w-3" />
                  )}
                  {cls}
                </Badge>
              ))}
            </div>
          </div>

          {/* Error message */}
          {agent.error && (
            <div className="p-2 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded text-xs text-red-700 dark:text-red-300">
              {agent.error}
            </div>
          )}

          {/* LLM Details */}
          {agent.llm_request && agent.llm_response && (
            <LLMDetailPanel
              request={agent.llm_request}
              response={agent.llm_response}
              showReasoning={true}
            />
          )}
        </div>
      )}
    </div>
  )
}
