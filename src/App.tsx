import "./styles/variables.css";
import "./styles/layout.css";
import "./styles/components.css";
import "./styles/views.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useAppStore } from "./stores/useAppStore";
import { useGeraSync } from "./hooks/useGeraSync";
import { useWindowWidth } from "./hooks/useWindowWidth";
import { Sidebar } from "./components/layout/Sidebar";
import { Inspector } from "./components/layout/Inspector";
import { TasksView } from "./components/tasks/TasksView";
import { CalendarView } from "./components/calendar/CalendarView";
import { NotesView } from "./components/notes/NotesView";

/** Below this window width, the inspector collapses into a modal overlay. */
const PORTRAIT_BREAKPOINT = 1000;

function AppLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const currentPath = location.pathname.split("/")[1] || "tasks";
  const loading = useAppStore((state) => state.loading);
  const width = useWindowWidth();
  const isPortrait = width < PORTRAIT_BREAKPOINT;

  // Setup data sync and listen to filesystem changes
  useGeraSync();

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
    <div className={`app-container ${showInspectorColumn ? "" : "no-inspector"}${isPortrait ? " portrait" : ""}`}>
      <Sidebar isPortrait={isPortrait} />
      <main className="main-content">
        {children}
      </main>
      <Inspector isVisible={isCalendar} isModal={isPortrait} />
    </div>
  );
}

function App() {
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
