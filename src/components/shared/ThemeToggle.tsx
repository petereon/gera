import { useEffect, useState } from 'react';
import { invoke } from "@tauri-apps/api/core";
import './ThemeToggle.css';

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

  const dark = theme === 'dark';

  return (
    <button
      aria-pressed={dark}
      onClick={() => setTheme(dark ? 'light' : 'dark')}
      title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
      className={`theme-toggle${dark ? ' theme-toggle--dark' : ''}`}
    >
      <span className="theme-toggle__knob">
        {dark ? (
          /* Moon icon */
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z" />
          </svg>
        ) : (
          /* Sun icon */
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <circle cx="12" cy="12" r="5" />
            <line x1="12" y1="1"  x2="12" y2="3"  stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <line x1="12" y1="21" x2="12" y2="23" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <line x1="4.22" y1="4.22"  x2="5.64" y2="5.64"  stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <line x1="1"  y1="12" x2="3"  y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <line x1="21" y1="12" x2="23" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        )}
      </span>
    </button>
  );
}

export default ThemeToggle;
