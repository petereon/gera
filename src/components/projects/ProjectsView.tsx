import { useAppStore } from '../../stores/useAppStore';
import { SearchInput } from '../shared/SearchInput';
import { EmptyState } from '../shared/EmptyState';

interface ProjectsViewProps {}

export function ProjectsView({}: ProjectsViewProps) {
  const projectsSearch = useAppStore((state) => state.projectsSearch);
  const setProjectsSearch = useAppStore((state) => state.setProjectsSearch);

  return (
    <div className="projects-view">
      <div className="projects-header">
        <div className="section-label">PROJECTS</div>
        <SearchInput
          value={projectsSearch}
          onChange={setProjectsSearch}
          placeholder="Search by event or name..."
          className="projects-search"
        />
      </div>
      <div className="projects-grid">
        <EmptyState message="No projects yet" />
      </div>
    </div>
  );
}
