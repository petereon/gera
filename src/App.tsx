import "./styles/variables.css";
import "./styles/layout.css";
import "./styles/components.css";
import "./styles/views.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useAppStore } from "./stores/useAppStore";
import { useGeraSync } from "./hooks/useGeraSync";
import { Sidebar } from "./components/layout/Sidebar";
import { Inspector } from "./components/layout/Inspector";
import { TasksView } from "./components/tasks/TasksView";
import { CalendarView } from "./components/calendar/CalendarView";
import { NotesView } from "./components/notes/NotesView";

function AppLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const currentPath = location.pathname.split("/")[1] || "tasks";
  const loading = useAppStore((state) => state.loading);

  // Setup data sync and listen to filesystem changes
  useGeraSync();

  if (loading) {
    return (
      <div className="app-container" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ color: "var(--text-tertiary)", fontSize: 16 }}>Loading workspace…</div>
      </div>
    );
  }

  return (
    <div className={`app-container ${currentPath !== "calendar" ? "no-inspector" : ""}`}>
      <Sidebar />
      <main className="main-content">
        {children}
      </main>
      <Inspector isVisible={currentPath === "calendar"} />
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
