import { env } from "@/lib/env"
import { supabase } from "@/lib/supabase"

export class ApiError extends Error {
  readonly status: number
  readonly isNetworkError: boolean

  constructor(status: number, message: string, isNetworkError = false) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.isNetworkError = isNetworkError
  }
}

async function getAuthHeader(): Promise<string | null> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  return token ? `Bearer ${token}` : null
}

export async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const authHeader = await getAuthHeader()

  const headers = new Headers(init.headers)
  headers.set("Content-Type", "application/json")
  if (authHeader) headers.set("Authorization", authHeader)

  let response: Response
  try {
    response = await fetch(`${env.apiBaseUrl}${path}`, { ...init, headers })
  } catch {
    throw new ApiError(0, "Network error — could not reach the server", true)
  }

  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText)
    throw new ApiError(response.status, text)
  }

  return response.json() as Promise<T>
}
