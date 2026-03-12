import { useEffect, useState } from 'react';
import { invoke } from "@tauri-apps/api/core";

const STORAGE_KEY = 'gera:theme';

export function ThemeToggle() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'dark' || stored === 'light') return stored;
    } catch (e) {}
    return 'light';
  });

  useEffect(() => {
    const applyTheme = async () => {
      document.documentElement.dataset.theme = theme;
      await invoke("set_theme", { dark: theme === 'dark' });
      try { localStorage.setItem(STORAGE_KEY, theme); } catch (e) {}
    };
    applyTheme();
  }, [theme]);

  return (
    <button
      aria-pressed={theme === 'dark'}
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      title="Toggle theme"
      className="icon-btn"
    >
      {theme === 'dark' ? '🌙' : '☀️'}
    </button>
  );
}

export default ThemeToggle;
