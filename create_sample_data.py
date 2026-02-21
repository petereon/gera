#!/usr/bin/env python3
"""Create sample entities in ~/Documents/Gera for development/testing."""

import pathlib

ROOT = pathlib.Path.home() / "Documents" / "Gera"
NOTES = ROOT / "notes"
PROJECTS = ROOT / "projects"

# Ensure dirs exist
NOTES.mkdir(parents=True, exist_ok=True)
PROJECTS.mkdir(parents=True, exist_ok=True)

# ── events.yaml ───────────────────────────────────────────────────────────

(ROOT / "events.yaml").write_text("""\
events:
  - id: weekly-standup
    source: google-calendar
    from: 2026-02-20T09:00
    to: 2026-02-20T09:30
    name: Weekly Standup
    description: Team sync - blockers, progress, plans for the week.
    participants:
      - anna.kovac@company.com
      - martin.novak@company.com
      - lucia.horvat@company.com

  - id: design-review
    source: google-calendar
    from: 2026-02-20T14:00
    to: 2026-02-20T15:00
    name: Design Review
    description: Review new dashboard wireframes and finalize component library choices.
    participants:
      - anna.kovac@company.com
      - peter.design@company.com

  - id: client-call-acme
    source: google-calendar
    from: 2026-02-21T10:00
    to: 2026-02-21T11:00
    name: ACME Corp - Kick-off Call
    description: Initial project kick-off with ACME Corp. Scope, timeline, deliverables.
    participants:
      - john.doe@acmecorp.com
      - sarah.miller@acmecorp.com
      - martin.novak@company.com

  - id: sprint-planning
    source: google-calendar
    from: 2026-02-23T10:00
    to: 2026-02-23T11:30
    name: Sprint Planning
    description: Plan Sprint 14 - prioritize backlog, assign story points.
    participants:
      - anna.kovac@company.com
      - martin.novak@company.com
      - lucia.horvat@company.com
      - tomas.kralik@company.com

  - id: one-on-one-martin
    source: local
    from: 2026-02-24T16:00
    to: 2026-02-24T16:30
    name: 1:1 with Martin
    description: Career growth check-in, feedback on Q4 performance.
    participants:
      - martin.novak@company.com

  - id: lunch-with-investors
    source: local
    from: 2026-02-25T12:00
    to: 2026-02-25T13:30
    name: Lunch with Investors
    description: Casual lunch with Horizon Ventures - discuss Series A progress.
    participants:
      - elena.rich@horizonvc.com
      - david.park@horizonvc.com

  - id: retro-sprint-13
    source: google-calendar
    from: 2026-02-26T15:00
    to: 2026-02-26T16:00
    name: Sprint 13 Retrospective
    description: What went well, what did not, action items for improvement.
    participants:
      - anna.kovac@company.com
      - martin.novak@company.com
      - lucia.horvat@company.com
      - tomas.kralik@company.com

  - id: quarterly-review
    source: google-calendar
    from: 2026-02-27T09:00
    to: 2026-02-27T10:30
    name: Q1 Quarterly Review
    description: Present Q1 OKR progress to leadership. Prepare slides!
    participants:
      - ceo@company.com
      - cto@company.com
      - anna.kovac@company.com
""")
print("  events.yaml")

# ── tasks.md ──────────────────────────────────────────────────────────────

(ROOT / "tasks.md").write_text("""\
# Tasks

- [ ] Prepare Q1 slides @before[2d]:quarterly-review
- [ ] Book restaurant for investor lunch @before[3d]:lunch-with-investors
- [x] Send agenda for weekly standup @weekly-standup
- [ ] Review Martin's self-assessment @before[1d]:one-on-one-martin
- [ ] Buy birthday gift for Sarah @2026-02-28T18:00
- [ ] Update project README #dashboard-redesign
- [ ] Write blog post draft #dashboard-redesign
- [ ] Clean up Jira backlog @before[1d]:sprint-planning
- [ ] Respond to ACME contract email @before[1d]:client-call-acme
- [x] Fix CI pipeline for staging
- [ ] Schedule dentist appointment @2026-03-05T10:00
""")
print("  tasks.md")

# ── notes ─────────────────────────────────────────────────────────────────

(NOTES / "standup-notes.md").write_text("""\
---
event_ids:
  - weekly-standup
---
# Weekly Standup Notes

## What I did
- Finished the new dashboard layout component
- Reviewed PRs from Martin and Lucia
- Deployed hotfix for the login timeout bug

## Blockers
- Waiting on API spec from backend team for the notifications endpoint
- Design assets for mobile view not ready yet

## Plan for next week
- [ ] Start integrating notification service @design-review
- [ ] Write unit tests for dashboard components
- [ ] Pair with Martin on the data export feature
""")
print("  notes/standup-notes.md")

(NOTES / "design-review-prep.md").write_text("""\
---
event_ids:
  - design-review
project_ids:
  - dashboard-redesign
---
# Design Review Preparation

## Agenda
1. Walk through new wireframes (Figma link in Slack)
2. Component library decision: Radix vs Headless UI
3. Color system revamp - accessibility audit results
4. Timeline for v2 prototype

## Key Decisions Needed
- Do we go with **Radix Primitives** or **Headless UI**?
  - Radix: better docs, more components
  - Headless: lighter bundle, more flexible
- Color palette: keep current brand blue or shift to the proposed teal?

## Notes
- Peter wants to present the motion design system
- Anna will share accessibility audit from last sprint
- [ ] Follow up with Peter on animation specs @before[1d]:design-review
""")
print("  notes/design-review-prep.md")

(NOTES / "acme-kickoff-agenda.md").write_text("""\
---
event_ids:
  - client-call-acme
---
# ACME Corp Kick-off Agenda

## Introductions
- Our team: Martin (tech lead), me (PM)
- Their team: John Doe (CTO), Sarah Miller (Product)

## Scope Discussion
The project involves building a **custom analytics dashboard** for ACME's
internal operations team. Key modules:

1. Real-time KPI tracking
2. Custom report builder
3. Email digest system
4. Role-based access control

## Timeline Proposal
| Phase        | Duration | Deliverable            |
|-------------|----------|------------------------|
| Discovery   | 2 weeks  | Requirements doc       |
| Design      | 3 weeks  | Wireframes + prototype |
| Development | 8 weeks  | MVP                    |
| QA & Launch | 2 weeks  | Production deploy      |

## Open Questions
- [ ] Confirm their SSO provider (Okta?)
- [ ] Get access to their staging API
- [ ] NDA status - legal review pending
""")
print("  notes/acme-kickoff-agenda.md")

(NOTES / "sprint-14-planning.md").write_text("""\
---
event_ids:
  - sprint-planning
project_ids:
  - dashboard-redesign
---
# Sprint 14 Planning

## Capacity
- Anna: 8 pts (out Friday)
- Martin: 10 pts
- Lucia: 10 pts
- Tomas: 6 pts (onboarding new intern)

## Proposed Stories

### Must Have
- [ ] Dashboard chart component (5 pts) #dashboard-redesign
- [ ] API integration for notifications (3 pts)
- [ ] Fix pagination bug on user list (2 pts)

### Nice to Have
- [ ] Dark mode toggle (3 pts) #dashboard-redesign
- [ ] Export to CSV feature (5 pts)
- [ ] Onboarding tooltip flow (2 pts)

## Risks
- Backend API for notifications *might* not be ready by mid-sprint
- Tomas spending ~40% time mentoring the intern
""")
print("  notes/sprint-14-planning.md")

(NOTES / "investor-lunch-prep.md").write_text("""\
---
event_ids:
  - lunch-with-investors
---
# Investor Lunch Prep

## Key Talking Points
- **ARR growth**: $1.2M -> $2.1M (75% YoY)
- **New enterprise clients**: ACME Corp, Zenith Labs, BrightPath
- **Team growth**: 8 -> 14 people in 6 months
- **Product**: v2 dashboard launching Q2

## What They Want to Hear
- Path to profitability (current burn rate: 18 months runway)
- Enterprise pipeline and deal sizes
- Technical moat / competitive advantage

## Restaurant
Reserving at **Osteria Moderna** - private dining room, 12:00.

- [ ] Confirm reservation @before[2d]:lunch-with-investors
- [ ] Print one-pager for the meeting
- [ ] Prepare demo on iPad
""")
print("  notes/investor-lunch-prep.md")

(NOTES / "random-ideas.md").write_text("""\
# Random Ideas & Thoughts

Just a scratchpad for things that pop into my head.

## Product Ideas
- What if we added a **Slack integration** that creates events from messages?
- AI-powered meeting summary - record, transcribe, extract action items
- Mobile companion app (React Native?) for quick capture on the go

## Books to Read
- "The Hard Thing About Hard Things" - Ben Horowitz
- "Inspired" - Marty Cagan
- "Staff Engineer" - Will Larson

## Personal
- Try that new coffee place on 5th street
- Look into standing desk converters
- [ ] Renew gym membership @2026-03-01T09:00
""")
print("  notes/random-ideas.md")

(NOTES / "retro-sprint-13-notes.md").write_text("""\
---
event_ids:
  - retro-sprint-13
---
# Sprint 13 Retro

## What Went Well
- Shipped the new onboarding flow on time
- Zero P0 bugs in production this sprint
- Great collaboration between frontend and design

## What Could Be Better
- Too many context switches mid-sprint
- Standups running over 15 minutes
- PR review turnaround still slow (avg 1.5 days)

## Action Items
- [ ] Implement "no meeting Wednesday" policy
- [ ] Set up automated PR reminder bot in Slack
- [ ] Create sprint scope change request template
- [ ] Timebox standups strictly to 15 min @weekly-standup
""")
print("  notes/retro-sprint-13-notes.md")

# ── projects ──────────────────────────────────────────────────────────────

(PROJECTS / "dashboard-redesign.md").write_text("""\
---
event_ids:
  - design-review
  - sprint-planning
---
# Dashboard Redesign

## Overview
Complete redesign of the main analytics dashboard. Moving from the legacy
jQuery-based charts to a modern React component library with real-time
data streaming.

## Goals
- Improve load time from 4.2s to under 1s
- Add responsive layouts for tablet/mobile
- Implement dark mode
- Accessibility audit compliance (WCAG 2.1 AA)

## Tech Stack
- **Frontend**: React 18 + TypeScript
- **Charts**: Recharts (replacing Chart.js)
- **State**: Zustand
- **Styling**: Tailwind CSS + Radix Primitives

## Milestones
| Milestone         | Target Date | Status      |
|-------------------|-------------|-------------|
| Wireframes        | Feb 15      | Done        |
| Component Library | Feb 28      | In Progress |
| Data Integration  | Mar 15      | Not Started |
| QA & Polish       | Mar 30      | Not Started |
| Launch            | Apr 7       | Not Started |

## Tasks
- [x] Set up new React project scaffolding
- [x] Design token system (colors, spacing, typography)
- [ ] Chart component library (bar, line, pie, area)
- [ ] Real-time WebSocket data layer
- [ ] Dashboard layout grid system
- [ ] Filter/date range picker component
- [ ] Export to PDF/PNG
- [ ] Dark mode theme implementation
- [ ] Performance benchmarking
""")
print("  projects/dashboard-redesign.md")

(PROJECTS / "acme-analytics.md").write_text("""\
---
event_ids:
  - client-call-acme
---
# ACME Analytics Platform

## Client
**ACME Corp** - Enterprise manufacturing company, 500+ employees.

## Project Summary
Custom analytics dashboard for ACME's operations team. They need
real-time visibility into production metrics, quality control data,
and supply chain KPIs.

## Requirements (Draft)
1. Real-time KPI widgets (production output, defect rate, downtime)
2. Custom report builder with drag-and-drop
3. Scheduled email digests (daily/weekly)
4. Role-based access (operators, managers, executives)
5. SSO integration (likely Okta)
6. Data export (CSV, Excel, PDF)

## Revenue
- **Contract value**: $180K
- **Timeline**: 15 weeks
- **Payment**: 30/40/30 milestone-based

## Team
- PM: Me
- Tech Lead: Martin
- Frontend: Lucia
- Backend: Tomas (after onboarding)
- Design: Peter (part-time)

## Tasks
- [ ] Finalize SOW and get signatures
- [ ] Set up dedicated Slack channel with ACME team
- [ ] Provision staging environment
- [ ] Schedule weekly check-in cadence
- [ ] Create Jira project and initial epics
""")
print("  projects/acme-analytics.md")

(PROJECTS / "mobile-app.md").write_text("""\
# Mobile Companion App

## Vision
A lightweight mobile app for quick capture and meeting prep on the go.
Not a full replacement for the desktop app - focused on two use cases:

1. **Quick capture**: Jot down notes/tasks from your phone
2. **Meeting prep**: Review notes and agenda before walking into a meeting

## Research
- React Native vs Flutter vs native
  - Leaning React Native for code sharing with web app
- Offline-first with local SQLite + sync
- Push notifications for upcoming meetings

## Status
This is a **future project** - parking ideas here for now.
No active development planned until Q3 2026.

## Ideas
- Voice-to-text quick capture
- Widget for iOS/Android home screen
- Share sheet integration (share links/text into Gera)
- Calendar widget showing next 3 meetings with linked notes
""")
print("  projects/mobile-app.md")

print("\nDone! All sample entities created.")
