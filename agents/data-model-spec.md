# Entities

Whenever tasks inherit something, it gets merged into whatever is already defined on task, it's not overridden.

## Events
Brought in form the calendar or defined standalone as YAML. We leave user to fuck himself up by changing IDs, who cares.
```yaml
events:
  - id: some-id
    source: google-calendar
    from: 2026-3-5T18:00
    to: 2026-3-5T18:30
    name: Talk with the manager
    description: Ouch oof
    location: The Shire
    participants: [jozko.mrkvicka@gmail.com, ferko.pazitka@hotmail.com]
```

## Task
Defined in markdown as markdown tasks
```md
- [ ] Walk the dog
```

If it has an associated event(s):

```md
- [ ] Prepare presentation @event-1
```
Or if it needs to be done 2 days before the event. 

```md
- [ ] Prepare presentation @before[2d]:event-1
```

Supported units in descending orders Y, M, W, D, h, m (Year, Month, Week, Day, hour, minute) - they are all case sensitive

If it has multiple events the time of the earlier one is assumed to be the deadline.

If it has associated time:

```md
- [ ] Buy flowers for wife @2026-3-3T18:00
```

Before syntax is also possible for time.

Logic here is that deadline for the task is either standalone or is the same as the event.

If it has associated projects:
```md
- [ ] Attach the handles #project-id
```




## Note
Markdown note with yaml preamble containing the following if the note has associated events
```yaml
event_ids:
  - event-1
  - event-2
project_ids:
  - project-1
  - project-2
```

Level one header `# Header` is used as a title of the note in the UI when the note is "minimized". If no title, first few words.

The note can contain tasks.

If note has associated events or projects the task in the note automatically inherits them without needing to be specified on the task level.

## Project
Can contain YAML preable containing events
```yaml
event_ids:
  - event-1
  - event-2
```
Project is a markdown file. It can contain arbitrary body and then it's essentially just a way to structure notes and tasks around a body of work instead of an event. It cannot have a deadline (that's what events are for). Its ID is the name of the file. It can contain markdown tasks similar to notes and if it does the tasks automatically inherit the project, and associated events.