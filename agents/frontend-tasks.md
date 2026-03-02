# Frontend Redesign Tasks

## Sidebar Restructure
- [x] Convert staging area into thin vertical sidebar
- [x] Stack blocks top-to-bottom: Tasks, Calendar, Projects, Notes
- [x] Implement block selection to change middle pane content

## Tasks Block
- [x] Display list of upcoming events with associated tasks
- [x] Display upcoming standalone tasks
- [x] Implement search bar for Tasks
  - [x] Search by event
  - [x] Search by project
  - [x] Search by time-range
  - [x] Plain-text search
- [x] Integrate floating tasks element into tasks view

## Calendar Block
- [ ] Implement week view with events
- [ ] Make calendar clickable to display in middle pane

## Projects Block
- [ ] Implement tile view of existing projects
- [ ] Make project tiles clickable
- [x] Implement search bar for Projects
  - [ ] Search by event
  - [x] Plain-text search
- [ ] Filter projects by search results

## Notes Block
- [x] Implement tile view of existing notes
- [x] Make note tiles clickable
- [x] Implement search bar for Notes
  - [ ] Search by event
  - [ ] Search by project
  - [ ] Search by time-range
  - [x] Plain-text search
- [x] Filter notes by search results

## Context Inspector Refactor
- [x] Show inspector only for calendar view
- [ ] Display ordered list of tasks associated with event
- [ ] Display tile view of notes associated with event
- [x] Hide inspector for other views (Tasks, Projects, Notes)

## Middle Pane Management
- [x] Implement dynamic middle pane content switching based on sidebar selection
- [x] Handle state management for selected view
