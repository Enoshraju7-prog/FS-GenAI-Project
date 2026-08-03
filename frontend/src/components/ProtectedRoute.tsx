import { useEffect, useState } from "react"
import { Navigate, Outlet } from "react-router-dom"
import { supabase } from "@/lib/supabase"
import type { Session } from "@supabase/supabase-js"

export default function ProtectedRoute() {
  const [session, setSession] = useState<Session | null | undefined>(undefined)

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session ?? null))

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      // `undefined` means "still loading" here, so it must never come from an auth
      // event — a sign-out arriving as undefined renders null and blanks the page
      // instead of redirecting to /login.
      setSession(session ?? null)
    })

    return () => subscription.unsubscribe()
  }, [])

  if (session === undefined) return null // still loading

  return session ? <Outlet /> : <Navigate to="/login" replace />
}
