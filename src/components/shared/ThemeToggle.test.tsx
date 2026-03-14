import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeToggle } from "./ThemeToggle";

// invoke is already shimmed via the test alias for @tauri-apps/api/core

// jsdom 28 ships without a working localStorage — provide a simple in-memory stub
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
    key: (i: number) => Object.keys(store)[i] ?? null,
    get length() { return Object.keys(store).length; },
  };
})();
vi.stubGlobal("localStorage", localStorageMock);

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
});

describe("ThemeToggle", () => {
  it("renders a button", () => {
    render(<ThemeToggle />);
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("defaults to light mode when localStorage is empty", () => {
    render(<ThemeToggle />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-pressed", "false");
  });

  it("restores dark mode from localStorage", () => {
    localStorage.setItem("gera:theme", "dark");
    render(<ThemeToggle />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-pressed", "true");
  });

  it("sets data-theme on <html> on mount", async () => {
    render(<ThemeToggle />);
    await waitFor(() => {
      expect(document.documentElement.dataset.theme).toBe("light");
    });
  });

  it("toggles to dark mode when clicked from light", async () => {
    render(<ThemeToggle />);
    await userEvent.click(screen.getByRole("button"));
    await waitFor(() => {
      expect(document.documentElement.dataset.theme).toBe("dark");
    });
  });

  it("toggles back to light mode when clicked from dark", async () => {
    localStorage.setItem("gera:theme", "dark");
    render(<ThemeToggle />);
    await userEvent.click(screen.getByRole("button"));
    await waitFor(() => {
      expect(document.documentElement.dataset.theme).toBe("light");
    });
  });

  it("persists the chosen theme to localStorage", async () => {
    render(<ThemeToggle />);
    await userEvent.click(screen.getByRole("button"));
    await waitFor(() => {
      expect(localStorage.getItem("gera:theme")).toBe("dark");
    });
  });

  it("shows the title hint for the opposite mode", async () => {
    render(<ThemeToggle />);
    expect(screen.getByRole("button")).toHaveAttribute("title", "Switch to dark mode");
    await userEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("button")).toHaveAttribute("title", "Switch to light mode");
  });
});
