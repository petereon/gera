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
import './NoteEditor.css';

export interface NoteEditorProps {
  filename: string;
  content: string;
  eventIds?: string[];
  projectIds?: string[];
  onSave?: (content: string) => void;
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
  autoSave = true,
  autoSaveDelay = 1000,
}: NoteEditorProps): JSX.Element {
  const editorRef = useRef<MDXEditorMethods>(null);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Tracks the last body content we wrote, so external reload can skip our own saves
  const lastSavedBodyRef = useRef<string>(content);

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
          // Clean up HTML entities that MDXEditor adds to checkboxes
          // MDXEditor adds &#x20; (space entity) after [ ] and [x] in task lists
          const cleanedContent = newContent
            .replace(/- \[ \] &#x20;/g, '- [ ] ')
            .replace(/- \[x\] &#x20;/g, '- [x] ');
          
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

          editorRef.current?.setMarkdown(body);
          // Update the ref so the next external change isn't falsely skipped
          lastSavedBodyRef.current = body;
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
    <div className="note-editor">
      <MDXEditor
        ref={editorRef}
        markdown={content}
        onChange={handleAutoSave}
        plugins={plugins}
      />
    </div>
  );
}
