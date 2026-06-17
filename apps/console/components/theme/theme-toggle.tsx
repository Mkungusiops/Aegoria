"use client";

import * as React from "react";
import { Moon, Sun } from "lucide-react";

/**
 * Light/dark switch. The actual theme is a `light` class on <html> (dark is the
 * default). A tiny inline script in the root layout applies the persisted choice
 * before paint (no flash); this button just flips + persists it.
 */
export function ThemeToggle() {
  const [theme, setTheme] = React.useState<"dark" | "light">("dark");
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
    setTheme(document.documentElement.classList.contains("light") ? "light" : "dark");
  }, []);

  function toggle() {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    document.documentElement.classList.toggle("light", next === "light");
    try {
      localStorage.setItem("aegoria-theme", next);
    } catch {
      /* ignore */
    }
  }

  return (
    <button
      onClick={toggle}
      aria-label="Toggle light / dark theme"
      title={mounted ? `Switch to ${theme === "light" ? "dark" : "light"} mode` : "Toggle theme"}
      className="grid h-9 w-9 place-items-center rounded-md border border-hairline bg-veil-2 text-muted transition-colors hover:border-auralis/40 hover:text-auralis"
    >
      {mounted && theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
    </button>
  );
}

/** Inline, render-blocking script that applies the saved theme before paint. */
export const themeInitScript = `(function(){try{var t=localStorage.getItem('aegoria-theme');if(t==='light'){document.documentElement.classList.add('light');}}catch(e){}})();`;
