import { create } from 'zustand';
import { EventEntity, NoteEntity, TaskEntity } from '../api';

export interface AppStore {
  // Navigation
  activeView: 'tasks' | 'calendar' | 'notes';
  setActiveView: (view: 'tasks' | 'calendar' | 'notes') => void;
  
  // Data
  events: EventEntity[];
  notes: NoteEntity[];
  tasks: TaskEntity[];
  loading: boolean;
  setEvents: (events: EventEntity[]) => void;
  setNotes: (notes: NoteEntity[]) => void;
  setTasks: (tasks: TaskEntity[]) => void;
  setLoading: (loading: boolean) => void;
  
  // Selections
  selectedEvent: EventEntity | null;
  selectedNote: NoteEntity | null;
  setSelectedEvent: (event: EventEntity | null) => void;
  setSelectedNote: (note: NoteEntity | null) => void;
  
  // Search filters
  tasksSearch: string;
  notesSearch: string;
  setTasksSearch: (search: string) => void;
  setNotesSearch: (search: string) => void;

  // Cross-reference navigation
  focusLine: number | null;
  setFocusLine: (line: number | null) => void;

  // Return-to navigation (e.g. open note from calendar, return on close)
  returnView: string | null;
  setReturnView: (view: string | null) => void;
}

export const useAppStore = create<AppStore>((set) => ({
  // Navigation
  activeView: 'calendar',
  setActiveView: (view) => set({ activeView: view }),
  
  // Data
  events: [],
  notes: [],
  tasks: [],
  loading: true,
  setEvents: (events) => set({ events }),
  setNotes: (notes) => set({ notes }),
  setTasks: (tasks) => set({ tasks }),
  setLoading: (loading) => set({ loading }),
  
  // Selections
  selectedEvent: null,
  selectedNote: null,
  setSelectedEvent: (selectedEvent) => set({ selectedEvent }),
  setSelectedNote: (selectedNote) => set({ selectedNote }),
  
  // Search filters
  tasksSearch: '',
  notesSearch: '',
  setTasksSearch: (tasksSearch) => set({ tasksSearch }),
  setNotesSearch: (notesSearch) => set({ notesSearch }),

  // Cross-reference navigation
  focusLine: null,
  setFocusLine: (focusLine) => set({ focusLine }),

  // Return-to navigation
  returnView: null,
  setReturnView: (returnView) => set({ returnView }),
}));
