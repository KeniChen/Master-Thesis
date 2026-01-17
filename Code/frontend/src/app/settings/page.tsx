"use client"

import { useEffect, useState } from "react"
import { Save, RefreshCw, CheckCircle2, XCircle, Check, X, Plus, Download, Send } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { providersApi, configApi, llmApi } from "@/lib/api"
import type {
  ProviderName,
  ProviderStatus,
  ProviderInfo,
  ProvidersResponse,
} from "@/lib/types"
import { PROVIDER_LABELS } from "@/lib/types"

const PROVIDER_ORDER: ProviderName[] = [
  "ollama",
  "azure_openai",
  "openai",
  "anthropic",
  "google",
  "litellm",
]

// Provider-specific form fields (connection settings only, models managed separately)
const PROVIDER_FIELDS: Record<ProviderName, { key: string; label: string; type: string; placeholder: string }[]> = {
  ollama: [
    { key: "base_url", label: "Base URL", type: "text", placeholder: "http://localhost:11434" },
  ],
  azure_openai: [
    { key: "endpoint", label: "Endpoint", type: "text", placeholder: "https://xxx.openai.azure.com" },
    { key: "api_key", label: "API Key", type: "password", placeholder: "Enter your API key" },
  ],
  openai: [
    { key: "api_key", label: "API Key", type: "password", placeholder: "sk-..." },
  ],
  anthropic: [
    { key: "api_key", label: "API Key", type: "password", placeholder: "sk-ant-..." },
  ],
  google: [
    { key: "api_key", label: "API Key", type: "password", placeholder: "Enter your API key" },
  ],
  litellm: [
    { key: "api_key", label: "API Key", type: "password", placeholder: "Enter your API key" },
    { key: "api_base", label: "API Base (optional)", type: "text", placeholder: "http://localhost:4000" },
  ],
}

// Model placeholder examples for each provider
const MODEL_PLACEHOLDERS: Record<ProviderName, string> = {
  ollama: "llama3.1:8b",
  azure_openai: "gpt-4",
  openai: "gpt-4",
  anthropic: "claude-3-sonnet-20240229",
  google: "gemini-pro",
  litellm: "azure-gpt-4",
}

function StatusDot({ status }: { status: ProviderStatus }) {
  if (status === "connected") {
    return <span className="inline-block w-2 h-2 rounded-full bg-green-500 mr-1.5" />
  }
  if (status === "error") {
    return <span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-1.5" />
  }
  return null
}

// Sensitive fields that should be masked
const SENSITIVE_FIELDS = ["api_key"]

export default function SettingsPage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [providersData, setProvidersData] = useState<ProvidersResponse | null>(null)
  const [selectedProvider, setSelectedProvider] = useState<ProviderName>("ollama")
  const [localConfigs, setLocalConfigs] = useState<Record<ProviderName, Record<string, string>>>({} as Record<ProviderName, Record<string, string>>)
  // Track which sensitive fields are configured on server and their masked display
  const [configuredSecrets, setConfiguredSecrets] = useState<Record<ProviderName, Record<string, string>>>({} as Record<ProviderName, Record<string, string>>)
  // Models management
  const [localModels, setLocalModels] = useState<Record<ProviderName, string[]>>({} as Record<ProviderName, string[]>)
  const [defaultModels, setDefaultModels] = useState<Record<ProviderName, string>>({} as Record<ProviderName, string>)
  const [newModelInput, setNewModelInput] = useState("")
  const [testingProvider, setTestingProvider] = useState<ProviderName | null>(null)
  const [testResult, setTestResult] = useState<{ provider: ProviderName; success: boolean; message: string } | null>(null)
  // Model fetching state
  const [fetchingModels, setFetchingModels] = useState(false)
  // Chat test state
  const [chatInput, setChatInput] = useState("")
  const [chatResponse, setChatResponse] = useState<{ response: string; latency_ms?: number } | null>(null)
  const [chatting, setChatting] = useState(false)

  const [defaults, setDefaults] = useState({
    mode: "single",
    maxDepth: 3,
    k: 5,
  })

  // Load providers data
  useEffect(() => {
    loadProviders()
  }, [])

  // Clear chat response when switching providers
  useEffect(() => {
    setChatResponse(null)
  }, [selectedProvider])

  const loadProviders = async () => {
    try {
      setLoading(true)
      const data = await providersApi.list()
      setProvidersData(data)

      // Initialize local configs from server data
      const configs: Record<ProviderName, Record<string, string>> = {} as Record<ProviderName, Record<string, string>>
      const secrets: Record<ProviderName, Record<string, string>> = {} as Record<ProviderName, Record<string, string>>
      const models: Record<ProviderName, string[]> = {} as Record<ProviderName, string[]>
      const defModels: Record<ProviderName, string> = {} as Record<ProviderName, string>

      for (const provider of PROVIDER_ORDER) {
        const providerConfig = data.providers[provider].config
        configs[provider] = {}
        secrets[provider] = {}
        models[provider] = []
        defModels[provider] = ""

        // Separate models from other config fields
        for (const key in providerConfig) {
          const value = providerConfig[key]
          if (key === "models" && Array.isArray(value)) {
            models[provider] = value
          } else if (key === "default_model" && typeof value === "string") {
            defModels[provider] = value
          } else if (typeof value === "string") {
            // Track masked values (•••...) and store the masked display
            if (value && /^•+$/.test(value)) {
              secrets[provider][key] = value
              configs[provider][key] = ""
            } else {
              configs[provider][key] = value
            }
          }
        }
      }
      setLocalConfigs(configs)
      setConfiguredSecrets(secrets)
      setLocalModels(models)
      setDefaultModels(defModels)
    } catch (error) {
      console.error("Failed to load providers:", error)
    } finally {
      setLoading(false)
    }
  }

  const handleConfigChange = (provider: ProviderName, key: string, value: string) => {
    setLocalConfigs(prev => ({
      ...prev,
      [provider]: {
        ...prev[provider],
        [key]: value,
      },
    }))
    // When user starts typing in a secret field, clear the configured status
    if (SENSITIVE_FIELDS.includes(key) && value !== "") {
      setConfiguredSecrets(prev => {
        const newSecrets = { ...prev }
        const { [key]: _, ...rest } = prev[provider] || {}
        void _
        newSecrets[provider] = rest
        return newSecrets
      })
    }
  }

  const isSecretConfigured = (provider: ProviderName, key: string) => {
    return key in (configuredSecrets[provider] || {}) && !localConfigs[provider]?.[key]
  }

  const getMaskedValue = (provider: ProviderName, key: string) => {
    return configuredSecrets[provider]?.[key] || ""
  }

  // Model management functions
  const handleAddModel = (provider: ProviderName, model: string) => {
    if (!model.trim()) return
    const trimmedModel = model.trim()
    setLocalModels(prev => {
      const currentModels = prev[provider] || []
      if (currentModels.includes(trimmedModel)) return prev
      return {
        ...prev,
        [provider]: [...currentModels, trimmedModel],
      }
    })
    // If this is the first model, set it as default
    if (!localModels[provider]?.length && !defaultModels[provider]) {
      setDefaultModels(prev => ({ ...prev, [provider]: trimmedModel }))
    }
    setNewModelInput("")
  }

  const handleRemoveModel = (provider: ProviderName, model: string) => {
    setLocalModels(prev => ({
      ...prev,
      [provider]: (prev[provider] || []).filter(m => m !== model),
    }))
    // If removed model was default, clear or set to first remaining
    if (defaultModels[provider] === model) {
      const remaining = (localModels[provider] || []).filter(m => m !== model)
      setDefaultModels(prev => ({ ...prev, [provider]: remaining[0] || "" }))
    }
  }

  const handleSetDefaultModel = (provider: ProviderName, model: string) => {
    setDefaultModels(prev => ({ ...prev, [provider]: model }))
  }

  const handleFetchModels = async (provider: ProviderName) => {
    setFetchingModels(true)
    try {
      const result = await providersApi.listModels(provider)
      if (result.models.length > 0) {
        // Deduplicate fetched models and merge with existing
        const uniqueFetched = [...new Set(result.models)]
        setLocalModels(prev => {
          const current = prev[provider] || []
          const merged = [...new Set([...current, ...uniqueFetched])]
          return {
            ...prev,
            [provider]: merged,
          }
        })
        // Set first model as default if none set
        if (!defaultModels[provider] && uniqueFetched.length > 0) {
          setDefaultModels(prev => ({ ...prev, [provider]: uniqueFetched[0] }))
        }
      }
    } catch (error) {
      console.error("Failed to fetch models:", error)
    } finally {
      setFetchingModels(false)
    }
  }

  const handleChat = async () => {
    if (!chatInput.trim()) return
    setChatting(true)
    setChatResponse(null)
    try {
      const result = await llmApi.chat(
        chatInput,
        selectedProvider,
        defaultModels[selectedProvider] || undefined
      )
      setChatResponse({
        response: result.response,
        latency_ms: result.latency_ms,
      })
    } catch (error) {
      setChatResponse({
        response: error instanceof Error ? error.message : "Chat failed",
      })
    } finally {
      setChatting(false)
    }
  }

  const handleTestProvider = async (provider: ProviderName) => {
    setTestingProvider(provider)
    setTestResult(null)
    try {
      // First save the config if changed
      const config = localConfigs[provider]
      // Filter out empty optional fields and masked values
      const filteredConfig: Record<string, string | string[]> = {}
      for (const [key, value] of Object.entries(config)) {
        if (value && !/^•+$/.test(value)) {
          filteredConfig[key] = value
        }
      }
      // Add models and default_model
      const models = localModels[provider] || []
      const defaultModel = defaultModels[provider] || ""
      filteredConfig.models = models
      filteredConfig.default_model = defaultModel
      await providersApi.update(provider, filteredConfig)

      // Then test
      const result = await providersApi.test(provider)
      setTestResult({
        provider,
        success: result.success,
        message: result.message,
      })

      // Refresh providers data to update status
      await loadProviders()
    } catch (error) {
      setTestResult({
        provider,
        success: false,
        message: error instanceof Error ? error.message : "Test failed",
      })
    } finally {
      setTestingProvider(null)
    }
  }

  const handleSetActive = async (provider: ProviderName) => {
    try {
      await providersApi.setActive(provider)
      setProvidersData(prev => prev ? { ...prev, active_provider: provider } : null)
    } catch (error) {
      console.error("Failed to set active provider:", error)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      // Save all provider configs
      for (const provider of PROVIDER_ORDER) {
        const config = localConfigs[provider]
        const filteredConfig: Record<string, string | string[]> = {}
        for (const [key, value] of Object.entries(config)) {
          if (value && !/^•+$/.test(value)) {
            filteredConfig[key] = value
          }
        }
        // Add models and default_model
        const models = localModels[provider] || []
        const defaultModel = defaultModels[provider] || ""
        filteredConfig.models = models
        filteredConfig.default_model = defaultModel
        await providersApi.update(provider, filteredConfig)
      }

      // Save defaults
      await configApi.update({
        defaults: {
          mode: defaults.mode as "single" | "edm",
          prompt_type: "cot",
          max_depth: defaults.maxDepth,
          k: defaults.k,
          edm_options: {
            classes_per_agent: 30,
            agents_per_class: 3,
            consensus_threshold: 0.8,
          },
        },
      })

      // Refresh
      await loadProviders()
    } catch (error) {
      console.error("Failed to save:", error)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  const activeProvider = providersData?.active_provider || "ollama"
  const providers = providersData?.providers || {} as Record<ProviderName, ProviderInfo>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Configure LLM providers and default parameters.
        </p>
      </div>

      <div className="grid gap-6">
        {/* LLM Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>LLM Configuration</CardTitle>
            <CardDescription>
              Configure the language model provider for semantic annotation.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Provider Selection */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Provider</label>
              <div className="flex flex-wrap gap-2">
                {PROVIDER_ORDER.map((provider) => {
                  const info = providers[provider]
                  const isSelected = selectedProvider === provider
                  const isActive = activeProvider === provider

                  return (
                    <Button
                      key={provider}
                      variant={isSelected ? "default" : "outline"}
                      onClick={() => setSelectedProvider(provider)}
                      className="relative"
                    >
                      <StatusDot status={info?.status || "unknown"} />
                      {PROVIDER_LABELS[provider]}
                      {isActive && (
                        <Check className="ml-1.5 h-3 w-3" />
                      )}
                    </Button>
                  )
                })}
              </div>
              <p className="text-xs text-muted-foreground">
                Click to configure. <Check className="inline h-3 w-3" /> = Active provider used for annotation.
              </p>
            </div>

            <Separator />

            {/* Provider Settings */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium">{PROVIDER_LABELS[selectedProvider]} Settings</h4>
                {activeProvider !== selectedProvider && providers[selectedProvider]?.configured && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleSetActive(selectedProvider)}
                  >
                    Set as Active
                  </Button>
                )}
              </div>

              {/* Connection Settings */}
              {PROVIDER_FIELDS[selectedProvider].length > 0 && (
                <div className="grid gap-4 md:grid-cols-2">
                  {PROVIDER_FIELDS[selectedProvider].map((field) => {
                    const isConfigured = isSecretConfigured(selectedProvider, field.key)
                    const displayValue = isConfigured ? getMaskedValue(selectedProvider, field.key) : (localConfigs[selectedProvider]?.[field.key] || "")
                    const placeholder = isConfigured ? "Configured, enter new value to update" : field.placeholder

                    return (
                      <div key={field.key} className={field.key === "api_key" ? "md:col-span-2" : ""}>
                        <div className="space-y-2">
                          <label className="text-sm font-medium">{field.label}</label>
                          <Input
                            type={field.type}
                            value={displayValue}
                            onChange={(e) => handleConfigChange(selectedProvider, field.key, e.target.value)}
                            placeholder={placeholder}
                            onFocus={(e) => {
                              // Clear the masked value when user focuses on the field
                              if (isConfigured) {
                                e.target.value = ""
                              }
                            }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Models Management */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">Models</label>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleFetchModels(selectedProvider)}
                    disabled={fetchingModels}
                  >
                    <Download className={`mr-1.5 h-3 w-3 ${fetchingModels ? "animate-pulse" : ""}`} />
                    {fetchingModels ? "Fetching..." : "Fetch from Server"}
                  </Button>
                </div>

                {/* Model Tags */}
                <div className="flex flex-wrap gap-2">
                  {(localModels[selectedProvider] || []).map((model) => {
                    const isDefault = model === defaultModels[selectedProvider]
                    return (
                      <Badge
                        key={model}
                        variant={isDefault ? "default" : "secondary"}
                        className="pl-2 pr-1 py-1 flex items-center gap-1"
                      >
                        <span>{model}</span>
                        <button
                          onClick={() => handleRemoveModel(selectedProvider, model)}
                          className={`ml-1 rounded p-0.5 ${isDefault ? "hover:bg-primary-foreground/20" : "hover:bg-muted"}`}
                          title="Remove model"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    )
                  })}
                  {(localModels[selectedProvider] || []).length === 0 && (
                    <span className="text-sm text-muted-foreground">No models configured</span>
                  )}
                </div>

                {/* Add Model Input */}
                <div className="flex gap-2">
                  <Input
                    placeholder={MODEL_PLACEHOLDERS[selectedProvider]}
                    value={newModelInput}
                    onChange={(e) => setNewModelInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault()
                        handleAddModel(selectedProvider, newModelInput)
                      }
                    }}
                    className="flex-1"
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => handleAddModel(selectedProvider, newModelInput)}
                    disabled={!newModelInput.trim()}
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>

                {/* Default Model Select */}
                {(localModels[selectedProvider] || []).length > 0 && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Default Model</label>
                    <Select
                      value={defaultModels[selectedProvider] || ""}
                      onValueChange={(value) => handleSetDefaultModel(selectedProvider, value)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select default model" />
                      </SelectTrigger>
                      <SelectContent>
                        {(localModels[selectedProvider] || []).map((model) => (
                          <SelectItem key={model} value={model}>
                            {model}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>

              <Separator />

              {/* Quick Chat Test */}
              <div className="space-y-3">
                <label className="text-sm font-medium">Quick Test</label>
                <div className="flex gap-2">
                  <Input
                    placeholder="Say hello..."
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault()
                        handleChat()
                      }
                    }}
                    className="flex-1"
                  />
                  <Button
                    onClick={handleChat}
                    disabled={chatting || !chatInput.trim()}
                  >
                    <Send className={`h-4 w-4 ${chatting ? "animate-pulse" : ""}`} />
                  </Button>
                </div>
                {chatResponse && (
                  <div className="p-3 rounded-md bg-muted text-sm">
                    <p className="whitespace-pre-wrap">{chatResponse.response}</p>
                    {chatResponse.latency_ms && (
                      <p className="text-xs text-muted-foreground mt-2">
                        ({chatResponse.latency_ms}ms)
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Button
                  variant="outline"
                  onClick={() => handleTestProvider(selectedProvider)}
                  disabled={testingProvider === selectedProvider}
                >
                  <RefreshCw className={`mr-2 h-4 w-4 ${testingProvider === selectedProvider ? "animate-spin" : ""}`} />
                  Test Connection
                </Button>
                {testResult && testResult.provider === selectedProvider && (
                  <Badge variant={testResult.success ? "default" : "destructive"} className={testResult.success ? "bg-green-500" : ""}>
                    {testResult.success ? (
                      <CheckCircle2 className="mr-1 h-3 w-3" />
                    ) : (
                      <XCircle className="mr-1 h-3 w-3" />
                    )}
                    {testResult.success ? "Connected" : testResult.message}
                  </Badge>
                )}
              </div>
              <Button onClick={handleSave} disabled={saving}>
                <Save className="mr-2 h-4 w-4" />
                {saving ? "Saving..." : "Save"}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Default Run Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>Default Run Configuration</CardTitle>
            <CardDescription>
              Set default parameters for new annotation runs.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Default Mode</label>
                <Select
                  value={defaults.mode}
                  onValueChange={(value) =>
                    setDefaults((prev) => ({ ...prev, mode: value }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="single">Single</SelectItem>
                    <SelectItem value="edm">EDM</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Max Depth</label>
                <Input
                  type="number"
                  min={1}
                  max={10}
                  value={defaults.maxDepth}
                  onChange={(e) =>
                    setDefaults((prev) => ({
                      ...prev,
                      maxDepth: parseInt(e.target.value) || 1,
                    }))
                  }
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Sample Rows (k)</label>
                <Input
                  type="number"
                  min={1}
                  max={20}
                  value={defaults.k}
                  onChange={(e) =>
                    setDefaults((prev) => ({
                      ...prev,
                      k: parseInt(e.target.value) || 1,
                    }))
                  }
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Data Paths */}
        <Card>
          <CardHeader>
            <CardTitle>Data Paths</CardTitle>
            <CardDescription>
              Configure paths to data files (read-only, set in backend config).
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Ontology</label>
                <Input
                  value="data/ontology/BEO_clean.rdf"
                  disabled
                  className="bg-muted"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Tables Directory</label>
                <Input
                  value="data/tables/"
                  disabled
                  className="bg-muted"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Labels</label>
                <Input
                  value="data/labels/ground_truth.csv"
                  disabled
                  className="bg-muted"
                />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-4">
        <Button variant="outline" onClick={loadProviders}>
          Reset
        </Button>
        <Button onClick={handleSave} disabled={saving}>
          <Save className="mr-2 h-4 w-4" />
          {saving ? "Saving..." : "Save Changes"}
        </Button>
      </div>
    </div>
  )
}
