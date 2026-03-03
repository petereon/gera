# Note Editor — MDXEditor Integration Plan

## Overview

Replace the read-only `NoteReader` (which renders via Python backend + `dangerouslySetInnerHTML`) with a rich-text editor powered by [MDXEditor](https://mdxeditor.dev/) (Lexical-based). The editor works directly with markdown — no HTML conversion layer needed.

### Key Goals
- Rich-text editing with native markdown round-trip (MDXEditor handles this internally via Lexical ↔ mdast)
- Support Gera-specific inline syntax (`@event-id`, `@2026-03-03T18:00`, `@before[2d]:event-id`, `#project-id`) as styled inline chips
- YAML frontmatter preservation (MDXEditor has a built-in `frontmatterPlugin`)
- Task list checkboxes that work reliably (MDXEditor + Lexical handle this natively)
- Debounced autosave to disk via existing `update_note` backend command
- Reload from disk on external file changes

### Architecture

```
MDXEditor (Lexical) ──onChange──▶ markdown string ──▶ API: update_note_content ──▶ disk
     ▲                                                        │
     └── setMarkdown(ref) ◀── getNoteContent ◀── gera://data-changed
```

MDXEditor owns the markdown ↔ rich-text conversion internally. We never touch HTML. The backend `update_note_content` command accepts the full markdown (with frontmatter) and writes it to disk.

---

## Syntax Reference

Gera inline syntax that must be preserved and rendered as styled chips:

| Pattern | Example | CSS Class |
|---|---|---|
| `@before[OFFSET]:TARGET` | `@before[2d]:design-review` | `gera-ref--before` |
| `@DATETIME` | `@2026-03-01T09:00` | `gera-ref--datetime` |
| `@EVENT-ID` | `@design-review` | `gera-ref--event` |
| `#PROJECT-ID` | `#dashboard-redesign` | `gera-ref--project` |

Regex patterns (from `renderer.py`, applied in this order):
1. `@before\[(\d+[YMWDhm])\]:([\w][\w:.\-]*)` — before-reference
2. `@(\d{4}-\d{1,2}-\d{1,2}T\d{2}:\d{2})` — datetime
3. `@(?!before\[)([a-zA-Z][\w\-]*)` — event reference
4. `#([a-zA-Z][\w\-]*)` — project tag

---

## Steps

### Step 1: Install MDXEditor, remove old deps

**Files:** `package.json`

```bash
bun add @mdxeditor/editor
bun remove turndown marked @types/turndown
```

Remove `src/utils/markdown.ts` if it still exists (from the old editor attempt). Remove the `EditorToolbar.tsx` and `NoteEditor.tsx` files if they exist.

### Step 2: Add `update_note_content` backend command

**Files:** `src-tauri/src-python/gera/app.py`, `src/api.ts`

The backend command may have been removed during the cleanup. Re-add if missing:

**Python (`app.py`):**
```python
class UpdateNoteContentRequest(BaseModel):
    filename: str
    content: str

@commands.command()
async def update_note_content(body: UpdateNoteContentRequest) -> None:
    get_repo().update_note(body.filename, body.content)
```

**TypeScript (`api.ts`):**
```typescript
export async function updateNoteContent(
  filename: string,
  content: string
): Promise<void> {
  return pyInvoke<void>("update_note_content", { filename, content });
}
```

### Step 3: Create the remark plugin for Gera references

**Files:** `src/editor/remarkGeraRefs.ts`

A [remark](https://github.com/remarkjs/remark) plugin that runs during markdown → mdast parsing. It walks text nodes looking for the four Gera patterns and converts matches into custom mdast nodes (`geraBeforeRef`, `geraDatetimeRef`, `geraEventRef`, `geraProjectRef`).

MDXEditor uses remark/rehype under the hood. We register our plugin via `realmPlugin` to add it to the import pipeline.

**Approach:**
- Use `unist-util-visit` + `findAndReplace` from `mdast-util-find-and-replace` to locate patterns in text nodes
- Replace matches with custom inline mdast nodes of type `geraRef` with a `refKind` field
- The custom node carries data: `{ kind, value, offset?, target? }`

```typescript
import { findAndReplace } from 'mdast-util-find-and-replace'
import type { Plugin } from 'unified'
import type { Root } from 'mdast'

// Regex patterns (same priority order as renderer.py)
const BEFORE_REF = /@before\[(\d+[YMWDhm])\]:([\w][\w:.\-]*)/g
const DATETIME_REF = /@(\d{4}-\d{1,2}-\d{1,2}T\d{2}:\d{2})/g
const EVENT_REF = /@(?!before\[)([a-zA-Z][\w-]*)/g
const PROJECT_TAG = /#([a-zA-Z][\w-]*)/g

export const remarkGeraRefs: Plugin<[], Root> = () => (tree) => {
  // Apply in order: most specific first
  findAndReplace(tree, [
    [BEFORE_REF, (_match, offset, target) => ({
      type: 'geraRef',
      data: { hName: 'gera-ref', hProperties: { kind: 'before', offset, target } },
      value: `@before[${offset}]:${target}`,
      children: [{ type: 'text', value: `@before[${offset}]:${target}` }],
    })],
    [DATETIME_REF, (_match, datetime) => ({
      type: 'geraRef',
      data: { hName: 'gera-ref', hProperties: { kind: 'datetime', datetime } },
      value: `@${datetime}`,
      children: [{ type: 'text', value: `@${datetime}` }],
    })],
    [EVENT_REF, (_match, eventId) => ({
      type: 'geraRef',
      data: { hName: 'gera-ref', hProperties: { kind: 'event', event: eventId } },
      value: `@${eventId}`,
      children: [{ type: 'text', value: `@${eventId}` }],
    })],
    [PROJECT_TAG, (_match, projectId) => ({
      type: 'geraRef',
      data: { hName: 'gera-ref', hProperties: { kind: 'project', project: projectId } },
      value: `#${projectId}`,
      children: [{ type: 'text', value: `#${projectId}` }],
    })],
  ])
}
```

### Step 4: Create Lexical decorator node for Gera references

**Files:** `src/editor/GeraRefNode.ts`

A Lexical `DecoratorNode` that renders the Gera references as styled inline chips in the editor. It is non-editable (atomic) — the user can delete it but cannot type inside it.

```typescript
import { DecoratorNode, type LexicalNode, type NodeKey } from 'lexical'

export type GeraRefKind = 'before' | 'datetime' | 'event' | 'project'

export class GeraRefNode extends DecoratorNode<JSX.Element> {
  __kind: GeraRefKind
  __rawText: string  // e.g. "@before[2d]:design-review"
  __attrs: Record<string, string>  // offset, target, datetime, event, project

  static getType(): string { return 'gera-ref' }
  static clone(node: GeraRefNode): GeraRefNode { ... }

  // Renders as an inline <span> with the appropriate gera-ref CSS class
  createDOM(): HTMLElement { ... }
  decorate(): JSX.Element { ... }  // Returns <GeraRefChip kind={...} text={...} />

  // For markdown export: returns the raw text verbatim
  exportJSON(): SerializedGeraRefNode { ... }
  static importJSON(json: SerializedGeraRefNode): GeraRefNode { ... }

  isInline(): boolean { return true }
  isKeyboardSelectable(): boolean { return true }
}
```

### Step 5: Create import/export visitors for MDXEditor

**Files:** `src/editor/geraRefVisitors.ts`

MDXEditor uses visitor patterns to convert between mdast ↔ Lexical nodes.

**Import visitor** (mdast → Lexical): When the remark plugin produces a `geraRef` mdast node, this visitor creates a `GeraRefNode` in the Lexical tree.

**Export visitor** (Lexical → mdast): When serializing back to markdown, this visitor converts `GeraRefNode` back to a simple text node containing the raw syntax (e.g. `@design-review`).

```typescript
import type { MdastImportVisitor, LexicalExportVisitor } from '@mdxeditor/editor'

export const MdastGeraRefVisitor: MdastImportVisitor<GeraRefMdastNode> = {
  testNode: (node) => node.type === 'geraRef',
  visitNode({ mdastNode, actions }) {
    actions.addAndStepInto(
      $createGeraRefNode(mdastNode.data.hProperties.kind, mdastNode.value, mdastNode.data.hProperties)
    )
  }
}

export const LexicalGeraRefVisitor: LexicalExportVisitor<GeraRefNode, ...> = {
  testLexicalNode: (node) => node instanceof GeraRefNode,
  visitLexicalNode({ lexicalNode, actions }) {
    // Export as plain text node — preserves the original @ / # syntax in markdown
    actions.addAndStepInto('text', { value: lexicalNode.__rawText })
  }
}
```

### Step 6: Create the MDXEditor Gera plugin

**Files:** `src/editor/geraRefsPlugin.ts`

Bundle everything into a single MDXEditor plugin using `realmPlugin`:

```typescript
import { realmPlugin, addImportVisitor$, addExportVisitor$, addLexicalNode$ } from '@mdxeditor/editor'

export const geraRefsPlugin = realmPlugin({
  init(realm) {
    realm.pubIn({
      [addImportVisitor$]: MdastGeraRefVisitor,
      [addExportVisitor$]: LexicalGeraRefVisitor,
      [addLexicalNode$]: GeraRefNode,
    })
  }
})
```

The remark plugin (`remarkGeraRefs`) is registered separately via MDXEditor's `markdown` processing options (passed to the core plugin or via `remarkPlugins` config).

### Step 7: Create the `GeraRefChip` React component

**Files:** `src/editor/GeraRefChip.tsx`

Small presentational component rendered by `GeraRefNode.decorate()`. Uses the existing `.gera-ref` CSS classes from `components.css`.

```tsx
interface GeraRefChipProps {
  kind: GeraRefKind
  text: string  // display text like "@design-review"
}

export function GeraRefChip({ kind, text }: GeraRefChipProps) {
  return (
    <span className={`gera-ref gera-ref--${kind}`} contentEditable={false}>
      {text}
    </span>
  )
}
```

### Step 8: Create the `NoteEditor` component

**Files:** `src/components/notes/NoteEditor.tsx`

The main component that wraps MDXEditor with Gera-specific configuration.

```tsx
import { MDXEditor, type MDXEditorMethods } from '@mdxeditor/editor'
import '@mdxeditor/editor/style.css'

// Standard plugins
import {
  headingsPlugin, listsPlugin, quotePlugin, thematicBreakPlugin,
  markdownShortcutPlugin, frontmatterPlugin, tablePlugin,
  codeBlockPlugin, toolbarPlugin, listsPlugin,
  BoldItalicUnderlineToggles, BlockTypeSelect, ListsToggle,
  CreateLink, InsertTable, InsertThematicBreak,
  UndoRedo, Separator,
} from '@mdxeditor/editor'

// Gera custom plugin
import { geraRefsPlugin } from '../../editor/geraRefsPlugin'
import { remarkGeraRefs } from '../../editor/remarkGeraRefs'

interface NoteEditorProps {
  note: NoteEntity
  rawContent: string
  onClose: () => void
  onSave: (filename: string, content: string) => Promise<void>
}

export function NoteEditor({ note, rawContent, onClose, onSave }: NoteEditorProps) {
  const editorRef = useRef<MDXEditorMethods>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null)
  const lastSavedRef = useRef(rawContent)

  // Update editor when rawContent changes from external source
  useEffect(() => {
    if (rawContent !== lastSavedRef.current) {
      editorRef.current?.setMarkdown(rawContent)
      lastSavedRef.current = rawContent
    }
  }, [rawContent])

  const handleChange = useCallback((markdown: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      lastSavedRef.current = markdown
      await onSave(note.filename, markdown)
    }, 1000)
  }, [note.filename, onSave])

  return (
    <div className="note-editor">
      <div className="note-editor-header">
        <h2>{note.title}</h2>
        <button onClick={onClose}>×</button>
      </div>
      <MDXEditor
        ref={editorRef}
        markdown={rawContent}
        onChange={handleChange}
        plugins={[
          headingsPlugin(),
          listsPlugin(),      // includes task lists
          quotePlugin(),
          thematicBreakPlugin(),
          markdownShortcutPlugin(),
          frontmatterPlugin(),
          tablePlugin(),
          codeBlockPlugin({ defaultCodeBlockLanguage: '' }),
          geraRefsPlugin(),   // Gera @/# references
          toolbarPlugin({
            toolbarContents: () => (
              <>
                <UndoRedo />
                <Separator />
                <BoldItalicUnderlineToggles />
                <Separator />
                <BlockTypeSelect />
                <Separator />
                <ListsToggle />
                <Separator />
                <CreateLink />
                <InsertTable />
                <InsertThematicBreak />
              </>
            ),
          }),
        ]}
        // Register the remark plugin for Gera ref parsing
        remarkPlugins={[remarkGeraRefs]}
      />
    </div>
  )
}
```

### Step 9: Wire `NoteEditor` into `NotesView`

**Files:** `src/components/notes/NotesView.tsx`

Replace `NoteReader` with `NoteEditor` when a note is selected. Load raw content, pass it to the editor, handle save and external-change reloads.

```tsx
// When note is selected:
<NoteEditor
  note={selectedNote}
  rawContent={rawContent}
  onClose={() => setSelectedNote(null)}
  onSave={updateNoteContent}
/>
```

Add a `gera://data-changed` listener that reloads `rawContent` when the note file changes externally (but skip reloads triggered by our own saves — compare against `lastSavedRef`).

### Step 10: Style the editor

**Files:** `src/styles/views.css`

- MDXEditor ships its own CSS (`@mdxeditor/editor/style.css`). Customize via CSS variables / overrides to match Gera's design system.
- The `.gera-ref` chip styles already exist in `components.css` — they'll work automatically with the `GeraRefChip` component.
- Add `.note-editor` container styles (flex layout, overflow, toolbar positioning).
- Override MDXEditor's toolbar to match Gera's existing UI aesthetic (white panel, rounded corners, shadow).

### Step 11: Clean up old code

**Files to remove (if they exist):**
- `src/utils/markdown.ts` — old Turndown/marked conversion utilities
- `src/components/notes/EditorToolbar.tsx` — old custom toolbar

**Dependencies to remove:**
- `turndown`, `@types/turndown`, `marked` from `package.json`

**Files to keep:**
- `src/MarkdownPreview.tsx` — still used by other views (Inspector, etc.)
- `src/components/notes/NoteReader.tsx` — can be removed after NoteEditor is stable, or kept as a fallback

---

## File Structure (new files)

```
src/
  editor/
    remarkGeraRefs.ts      # remark plugin: text → geraRef mdast nodes
    GeraRefNode.ts          # Lexical DecoratorNode for inline ref chips  
    GeraRefChip.tsx         # React component rendered by the decorator node
    geraRefVisitors.ts      # mdast ↔ Lexical import/export visitors
    geraRefsPlugin.ts       # MDXEditor realmPlugin bundling everything
  components/
    notes/
      NoteEditor.tsx        # MDXEditor wrapper with Gera config
```

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| MDXEditor reformats markdown on save (extra blank lines, reordered lists) | MDXEditor's `toMarkdownOptions` config controls formatting. Test with real notes and tune options (`bullet: '-'`, `listItemIndent: 'one'`, etc.) |
| Remark plugin conflicts with GFM task list parsing | Test order-of-operations. Our plugin should run after GFM so task list items are already parsed and we only transform remaining text nodes |
| `#project-id` conflicts with markdown headings | The regex requires `#` followed by a letter (not space), so `# Heading` won't match. In Lexical context, headings are already separate nodes — only text nodes inside paragraphs/list items are scanned |
| Frontmatter gets mangled | MDXEditor's `frontmatterPlugin` handles YAML frontmatter natively — it's passed through as-is, not part of the editable content |
| Bundle size increase | MDXEditor is ~80KB gzipped. Acceptable for a desktop app. Can lazy-import if needed |
| Race condition: save + file watcher reload | Track last-saved content in a ref. When `rawContent` changes from disk, compare against `lastSavedRef` — skip `setMarkdown` if identical |

---

## Open Requirements

### ✅ R1: Minimal list / checkbox indentation

Lists (`<ul>`, `<ol>`) and task list checkboxes are currently indented too deeply inside the editor. They should have near-zero left indent — just enough to keep the bullet/checkbox visible.

Implemented in `src/styles/views.css` — overrides scoped to `.mdxeditor .mdxeditor-root-contenteditable`:

```css
ul, ol       → padding-left: 18px
li           → margin: 1px 0
ul[data-lexical-list-type="check"]        → padding-left: 4px  (task lists even tighter)
ul[data-lexical-list-type="check"] > li  → padding-left: 4px
```

### ✅ R2: Markdown table support

MDXEditor supports tables via its `tablePlugin`. Add it to the plugin list and optionally add `InsertTable` to the toolbar. This enables rendering and editing of standard GFM pipe tables (`| col1 | col2 |`).

### R3: Editable / deletable Gera reference chips

Currently the `GeraRefNode` is fully atomic (non-editable). Users should be able to:

- **Delete** a chip by selecting it and pressing Backspace/Delete, or by placing the cursor adjacent and backspacing into it.
- **Modify** a chip by clicking on it or pressing Enter while selected, which should "unwrap" it back into its raw text form (`@event-id`, `#project-id`, etc.) so the user can edit the text directly. When the user finishes editing (blur / moves cursor away), the text should be re-parsed and re-chipified if it still matches a Gera pattern.

Implementation approach: on chip activation (click/Enter), replace the `GeraRefNode` with a plain `TextNode` containing the raw syntax. Rely on the existing import pipeline to re-chipify matching text on the next markdown round-trip (or trigger a local re-parse of the parent paragraph).

### R4: Event chips should display human-readable names

Event reference chips (e.g. `@retro-sprint-13`) currently display the raw ID with the `@` prefix. Instead they should display the **event title** (e.g. "Retro Sprint 13"). The `@` prefix should not be shown in the chip text — the chip's color / style already distinguishes it as an event reference.

This requires looking up the event entity from the store. The `GeraRefChip` component should:
1. Accept the raw event ID
2. Look up `useAppStore.events` to find the matching `EventEntity` by ID
3. Display `event.title` if found, otherwise fall back to the raw ID (without `@`)

Similarly, project chips should display the project title if available.

Datetime and before-reference chips should keep their current formatted display.

### ✅ R5: Reload editor content on external / backend saves

When the note file is modified externally (e.g. task checkbox toggled from the Tasks view, file watcher detecting on-disk changes), the editor must pick up the new content. Currently the `gera://data-changed` event triggers a re-fetch of the notes list, but the open editor does not refresh.

The fix should:
1. Listen for `gera://data-changed` events whose payload includes the current note's entity/file.
2. Re-fetch the note's raw content from the backend (`getNoteContent`).
3. Compare the fetched content against the editor's current markdown (via `editorRef.current.getMarkdown()`). If they differ **and** the change did not originate from the editor's own autosave, call `editorRef.current.setMarkdown(newContent)` to update the editor in place.
4. Preserve cursor position / scroll where feasible (Lexical typically does this on `setMarkdown` if the structure is similar).
5. Guard against save ↔ reload loops: track the last content string written by autosave in a ref and skip `setMarkdown` when the fetched content matches it.

---

## Dependency Notes

- `@mdxeditor/editor` (v3.x) — main editor component
- `mdast-util-find-and-replace` — used by the remark plugin (may ship with MDXEditor's remark stack, check before adding separately)
- Remove: `turndown`, `@types/turndown`, `marked`