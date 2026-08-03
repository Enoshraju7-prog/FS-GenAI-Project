export type Theme = "light" | "dark" | "system"

const STORAGE_KEY = "theme"

// Dark is the designed default — the light palette exists, but the product was styled
// for the dark canvas.
export function getStoredTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY)
  return stored === "light" || stored === "dark" || stored === "system" ? stored : "dark"
}

export function setStoredTheme(theme: Theme): void {
  localStorage.setItem(STORAGE_KEY, theme)
  applyTheme(theme)
}

// shadcn's tokens hang off a `.dark` class on the root element (see the
// `@custom-variant dark` rule in index.css), so switching themes is just toggling it.
export function applyTheme(theme: Theme): void {
  const dark = theme === "dark" || (theme === "system" && prefersDark())
  document.documentElement.classList.toggle("dark", dark)
}

export function prefersDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches
}

/** Re-applies the theme when the OS flips, but only while following the system. */
export function watchSystemTheme(onChange: () => void): () => void {
  const query = window.matchMedia("(prefers-color-scheme: dark)")
  query.addEventListener("change", onChange)
  return () => query.removeEventListener("change", onChange)
}
