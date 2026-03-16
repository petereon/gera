import "./styles/variables.css";
import "./styles/layout.css";
import "./styles/components.css";
import "./styles/views.css";
import { useEffect } from "react";
import { listen } from "@tauri-apps/api/event";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { newVault, openVault } from "./api";
import { useAppStore } from "./stores/useAppStore";
import { useGeraSync } from "./hooks/useGeraSync";
import { useWindowWidth } from "./hooks/useWindowWidth";
import { useKeyboard } from "./hooks/useKeyboard";
import { useTour, isTourDone } from "./hooks/useTour";
import { Sidebar } from "./components/layout/Sidebar";
import { Inspector } from "./components/layout/Inspector";
import { TasksView } from "./components/tasks/TasksView";
import { CalendarView } from "./components/calendar/CalendarView";
import { NotesView } from "./components/notes/NotesView";
import { CommandPalette } from "./components/command-palette/CommandPalette";
import { SettingsModal } from "./components/settings/SettingsModal";

/** Below this window width, the inspector collapses into a modal overlay. */
const PORTRAIT_BREAKPOINT = 1000;

function AppLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const currentPath = location.pathname.split("/")[1] || "tasks";
  const loading = useAppStore((state) => state.loading);
  const settingsOpen = useAppStore((state) => state.settingsOpen);
  const setSettingsOpen = useAppStore((state) => state.setSettingsOpen);
  const width = useWindowWidth();
  const isPortrait = width < PORTRAIT_BREAKPOINT;

  // Setup data sync and listen to filesystem changes
  useGeraSync();
  // Register global keyboard shortcuts
  useKeyboard();

  const { startTour } = useTour();

  // Fire tour once after the workspace finishes loading
  useEffect(() => {
    if (!loading && !isTourDone()) {
      const id = setTimeout(startTour, 600);
      return () => clearTimeout(id);
    }
  }, [loading]);

  if (loading) {
    return (
      <div className="app-container" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ color: "var(--text-tertiary)", fontSize: 16 }}>Loading workspace…</div>
      </div>
    );
  }

  const isCalendar = currentPath === "calendar";
  // Show inspector in the grid only when on calendar AND not in portrait mode
  const showInspectorColumn = isCalendar && !isPortrait;

  return (
    <>
      <div className={`app-container ${showInspectorColumn ? "" : "no-inspector"}${isPortrait ? " portrait" : ""}`}>
        <Sidebar isPortrait={isPortrait} />
        <main className="main-content">
          {children}
        </main>
        <Inspector isVisible={isCalendar} isModal={isPortrait} />
      </div>
      <CommandPalette />
      <SettingsModal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </>
  );
}

function App() {
  // Handle vault menu events from the native File menu
  useEffect(() => {
    const handlers = [
      listen<void>("vault:new", async () => {
        const selected = await openDialog({ directory: true, title: "New Vault — Choose Folder" });
        if (selected) await newVault(selected as string);
      }),
      listen<void>("vault:open", async () => {
        const selected = await openDialog({ directory: true, title: "Open Vault — Choose Folder" });
        if (selected) await openVault(selected as string);
      }),
      listen<string>("vault:open-path", async (event) => {
        await openVault(event.payload);
      }),
    ];
    return () => { handlers.forEach((p) => p.then((unlisten) => unlisten())); };
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/tasks" replace />} />
        <Route 
          path="/tasks" 
          element={
            <AppLayout>
              <TasksView />
            </AppLayout>
          } 
        />
        <Route 
          path="/calendar" 
          element={
            <AppLayout>
              <CalendarView />
            </AppLayout>
          } 
        />
        <Route 
          path="/notes" 
          element={
            <AppLayout>
              <NotesView />
            </AppLayout>
          } 
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
