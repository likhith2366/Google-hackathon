export type RiskProfile = {
  score: number
  caution_level: string
  reasons: string[]
}

export type ParsedAddress = {
  house_number: string
  street_name: string
  borough: string
}

export type BuildingContext = {
  violations: Record<string, unknown>[]
  complaints: Record<string, unknown>[]
  litigations: Record<string, unknown>[]
  risk_profile: RiskProfile
}

export type AnalyzeResponse = {
  session_id: string
  address: ParsedAddress
  violations: Record<string, unknown>[]
  complaints: Record<string, unknown>[]
  litigations: Record<string, unknown>[]
  risk_profile: RiskProfile
  summary: string
  data_warning: boolean
}

export type ChatResponse = {
  reply: string
  session_id: string
}

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8080'

export async function analyze(query: string): Promise<AnalyzeResponse> {
  const res = await fetch(`${BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail ?? `Error ${res.status}`)
  }
  return res.json() as Promise<AnalyzeResponse>
}

export async function chat(
  session_id: string,
  message: string,
  context: BuildingContext,
): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id, message, context }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail ?? `Error ${res.status}`)
  }
  return res.json() as Promise<ChatResponse>
}
