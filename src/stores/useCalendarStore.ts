import { create } from 'zustand';

export interface CalendarStore {
  currentWeekStart: Date;
  setCurrentWeekStart: (date: Date) => void;
  goToPreviousWeek: () => void;
  goToNextWeek: () => void;
  goToToday: () => void;
}

export const useCalendarStore = create<CalendarStore>((set) => {
  // Calculate Monday of current week
  const getMonday = (date: Date) => {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(d.setDate(diff));
  };

  const today = new Date();
  const currentWeekStart = getMonday(today);

  return {
    currentWeekStart,
    setCurrentWeekStart: (date) => set({ currentWeekStart: date }),
    goToPreviousWeek: () =>
      set((state) => {
        const prev = new Date(state.currentWeekStart);
        prev.setDate(prev.getDate() - 7);
        return { currentWeekStart: prev };
      }),
    goToNextWeek: () =>
      set((state) => {
        const next = new Date(state.currentWeekStart);
        next.setDate(next.getDate() + 7);
        return { currentWeekStart: next };
      }),
    goToToday: () => set({ currentWeekStart: getMonday(today) }),
  };
});
