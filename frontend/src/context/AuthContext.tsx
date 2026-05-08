import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import client, { setToken } from '../api/client'

interface AuthCtx {
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const Ctx = createContext<AuthCtx | null>(null)

const INACTIVITY_MS = 30 * 60 * 1000

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const logout = useCallback(() => {
    setToken(null)
    setIsAuthenticated(false)
    client.post('/api/v1/auth/logout').catch(() => {})
  }, [])

  const resetTimer = useCallback(() => {
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(logout, INACTIVITY_MS)
  }, [logout])

  useEffect(() => {
    if (!isAuthenticated) return
    const events = ['mousemove', 'keydown', 'click', 'scroll']
    events.forEach((e) => window.addEventListener(e, resetTimer))
    resetTimer()
    return () => {
      events.forEach((e) => window.removeEventListener(e, resetTimer))
      if (timer.current) clearTimeout(timer.current)
    }
  }, [isAuthenticated, resetTimer])

  const login = async (username: string, password: string) => {
    const { data } = await client.post('/api/v1/auth/login', { username, password })
    setToken(data.access_token)
    setIsAuthenticated(true)
  }

  return <Ctx.Provider value={{ isAuthenticated, login, logout }}>{children}</Ctx.Provider>
}

export const useAuth = () => {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useAuth outside AuthProvider')
  return ctx
}
