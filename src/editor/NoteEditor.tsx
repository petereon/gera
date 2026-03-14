/**
 * NoteEditor component — MDXEditor-based rich-text editor with Gera reference support.
 *
 * Features:
 * - Edit markdown with full formatting support
 * - Parse and render Gera references (@event-id, #project-id, etc.)
 * - Debounced autosave to backend
 * - Preserve YAML frontmatter
 * - Support for task lists (checkboxes)
 * - Reload editor content on external / backend saves (R5)
 */

import { useCallback, useEffect, useRef } from 'react';
import { listen } from '@tauri-apps/api/event';
import {
  MDXEditor,
  MDXEditorMethods,
  headingsPlugin,
  listsPlugin,
  linkPlugin,
  quotePlugin,
  thematicBreakPlugin,
  markdownShortcutPlugin,
  codeBlockPlugin,
  codeMirrorPlugin,
  toolbarPlugin,
  UndoRedo,
  BoldItalicUnderlineToggles,
  BlockTypeSelect,
  CodeToggle,
  CreateLink,
  InsertCodeBlock,
  InsertThematicBreak,
  InsertTable,
  ListsToggle,
  Separator,
  tablePlugin,
} from '@mdxeditor/editor';
import '@mdxeditor/editor/style.css';
import { getNoteContent, updateNoteContent } from '../api';
import { parseFrontmatter } from '../utils/frontmatter';
import { geraRefsPlugin } from './geraRefsPlugin';
import { useAppStore } from '../stores/useAppStore';
import './NoteEditor.css';

/**
 * Mirror the Python backend's `_sanitize_content`:
 *   1. Replace all &#x20; HTML entities with a plain space.
 *   2. Strip trailing horizontal whitespace from every line.
 *
 * Keeping frontend and backend in sync prevents the external-reload guard
 * (`body === lastSavedBodyRef.current`) from failing on every autosave,
 * which would cause `setMarkdown` to be called and reset the cursor.
 */
function sanitizeContent(content: string): string {
  return content
    .replace(/&#x20;/g, ' ')
    .replace(/[ \t]+$/gm, '');
}

export interface NoteEditorProps {
  filename: string;
  content: string;
  eventIds?: string[];
  projectIds?: string[];
  onSave?: (content: string) => void;
  onClose?: () => void;
  autoSave?: boolean;
  autoSaveDelay?: number;
}

/**
 * Rich-text editor for Gera notes with support for Gera-specific syntax.
 *
 * The editor:
 * 1. Updates the backend via `updateNoteContent` API
 * 2. Debounces saves with configurable delay (default 1000ms)
 * 3. Preserves YAML frontmatter at the top of notes
 * 4. Parses and renders @event-id, @datetime, @before[...]:id, #project-id references
 */
export function NoteEditor({
  filename,
  content,
  eventIds = [],
  projectIds = [],
  onSave,
  onClose: _onClose,
  autoSave = true,
  autoSaveDelay = 1000,
}: NoteEditorProps): JSX.Element {
  const editorRef = useRef<MDXEditorMethods>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Tracks the last body content we wrote, so external reload can skip our own saves
  const lastSavedBodyRef = useRef<string>(content);

  const focusLine = useAppStore((state) => state.focusLine);
  const setFocusLine = useAppStore((state) => state.setFocusLine);

  // Auto-focus the editor content area when the note opens.
  useEffect(() => {
    const t = setTimeout(() => editorRef.current?.focus(), 80);
    return () => clearTimeout(t);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Preserve scroll position when a task-list checkbox is toggled.
  // Lexical scrolls its selection into view after the state update, which resets
  // the viewport to the top if the internal selection lands at position 0.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
      const onMouseDown = (e: MouseEvent) => {
      const target = e.target as Element;
      const isCheckbox =
        target.closest('li[role="checkbox"]') != null ||
        (target instanceof HTMLInputElement && target.type === 'checkbox');
      if (!isCheckbox) return;
      const scroll = el.querySelector<HTMLElement>('.mdxeditor-root-contenteditable');
      if (!scroll) return;
      const savedTop = scroll.scrollTop;
      requestAnimationFrame(() => {
        requestAnimationFrame(() => { scroll.scrollTop = savedTop; });
      });
    };
    el.addEventListener('mousedown', onMouseDown);
    return () => el.removeEventListener('mousedown', onMouseDown);
  }, []);

  // Scroll to target task when navigating via cross-reference
  useEffect(() => {
    if (focusLine === null) return;

    let attempts = 0;
    const MAX_ATTEMPTS = 10;
    const INTERVAL_MS = 120;

    const tryScroll = () => {
      const container = document.querySelector('.mdxeditor-root-contenteditable');
      if (!container) {
        if (++attempts < MAX_ATTEMPTS) { timerId = window.setTimeout(tryScroll, INTERVAL_MS); }
        else { setFocusLine(null); }
        return;
      }
      // MDXEditor (Lexical) renders task-list items as <li role="checkbox">
      const taskItems = container.querySelectorAll<HTMLElement>('li[role="checkbox"]');
      const target = taskItems[focusLine] ?? null;
      if (!target) {
        if (++attempts < MAX_ATTEMPTS) { timerId = window.setTimeout(tryScroll, INTERVAL_MS); }
        else { setFocusLine(null); }
        return;
      }
      target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      target.classList.add('task-line-highlight');
      setTimeout(() => target.classList.remove('task-line-highlight'), 2500);
      setFocusLine(null);
    };

    // Start first attempt after a short delay so MDXEditor has time to mount
    let timerId = window.setTimeout(tryScroll, 200);
    return () => window.clearTimeout(timerId);
  }, [focusLine, setFocusLine]);

  // Debounced save handler
  const handleAutoSave = useCallback(
    (newContent: string) => {
      if (!autoSave) return;

      // Cancel pending save
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }

      // Schedule new save
      saveTimeoutRef.current = setTimeout(async () => {
        try {
          // Mirror the backend's _sanitize_content so lastSavedBodyRef exactly
          // matches what the backend writes to disk (prevents false guard failures).
          const cleanedContent = sanitizeContent(newContent);

          // Reconstruct frontmatter if we have event_ids or project_ids
          let fullContent = cleanedContent;
          if (eventIds.length > 0 || projectIds.length > 0) {
            const frontmatterLines: string[] = ['---'];
            if (eventIds.length > 0) {
              frontmatterLines.push('event_ids:');
              eventIds.forEach(id => frontmatterLines.push(`  - ${id}`));
            }
            if (projectIds.length > 0) {
              frontmatterLines.push('project_ids:');
              projectIds.forEach(id => frontmatterLines.push(`  - ${id}`));
            }
            frontmatterLines.push('---', '');
            fullContent = frontmatterLines.join('\n') + cleanedContent;
          }
          
          lastSavedBodyRef.current = cleanedContent;
          await updateNoteContent(filename, fullContent);
          onSave?.(fullContent);
        } catch (err) {
          console.error('Failed to save note:', err);
        }
      }, autoSaveDelay);
    },
    [filename, autoSave, autoSaveDelay, onSave, eventIds, projectIds]
  );

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

  // R5: Reload editor when the note is modified externally (file watcher / other views)
  useEffect(() => {
    const unlisten = listen<{ changes: { entity: string; ids: string[] | null }[] }>(
      'gera://data-changed',
      async () => {
        try {
          const result = await getNoteContent(filename);
          const { body } = parseFrontmatter(result.raw_content);

          // Skip if this matches what we last saved ourselves (avoid save↔reload loop)
          if (body === lastSavedBodyRef.current) return;

          // Skip if the editor already has this content
          const current = editorRef.current?.getMarkdown() ?? '';
          if (body === current) return;

          const scrollEl = document.querySelector<HTMLElement>('.mdxeditor-root-contenteditable');
          const savedScrollTop = scrollEl?.scrollTop ?? 0;
          editorRef.current?.setMarkdown(body);
          // Update the ref so the next external change isn't falsely skipped
          lastSavedBodyRef.current = body;
          // Restore scroll — setMarkdown replaces all Lexical nodes which resets
          // the viewport to the top. Use a rAF so the DOM has settled first.
          requestAnimationFrame(() => {
            if (scrollEl) scrollEl.scrollTop = savedScrollTop;
          });
        } catch (err) {
          console.error('Failed to reload note on external change:', err);
        }
      }
    );
    return () => {
      unlisten.then((fn) => fn());
    };
  }, [filename]);

  // Build MDXEditor plugins with Gera support
  const plugins = [
    // Gera reference chip rendering (@event-id, #project-id, etc.)
    geraRefsPlugin(),
    // Toolbar with all formatting controls
    toolbarPlugin({
      toolbarContents: () => (
        <>
          <UndoRedo />
          <Separator />
          <BoldItalicUnderlineToggles />
          <Separator />
          <BlockTypeSelect />
          <Separator />
          <CodeToggle />
          <Separator />
          <CreateLink />
          <Separator />
          <ListsToggle />
          <Separator />
          <InsertCodeBlock />
          <Separator />
          <InsertThematicBreak />
          <Separator />
          <InsertTable />
        </>
      ),
    }),
    headingsPlugin(),
    listsPlugin(),
    linkPlugin(),
    quotePlugin(),
    thematicBreakPlugin(),
    codeBlockPlugin({
      defaultCodeBlockLanguage: 'python',
    }),
    codeMirrorPlugin({
      codeBlockLanguages: {
        python: 'Python',
        javascript: 'JavaScript',
        typescript: 'TypeScript',
        bash: 'Bash',
        json: 'JSON',
        yaml: 'YAML',
      },
    }),
    tablePlugin(),
    markdownShortcutPlugin(),
  ];

  return (
    <div className="note-editor" ref={containerRef}>
      <MDXEditor
        ref={editorRef}
        markdown={content}
        onChange={handleAutoSave}
        plugins={plugins}
      />
    </div>
  );
}
