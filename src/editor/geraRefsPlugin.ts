/**
 * MDXEditor RealmPlugin for Gera inline references.
 *
 * Integrates @event-id, @2026-03-01T09:00, @before[2d]:event-id and #project-id
 * into the MDXEditor pipeline without needing a separate remark step:
 *
 * Import (markdown → Lexical):
 *   The MdastImportVisitor intercepts plain `text` mdast nodes that contain
 *   Gera patterns, splits them into TextNode + GeraRefNode siblings and
 *   appends them all to the lexical parent (paragraph).
 *
 * Export (Lexical → markdown):
 *   The LexicalExportVisitor converts GeraRefNode back to a plain mdast text
 *   node containing the original raw syntax so the file stays clean.
 */

import {
  realmPlugin,
  addLexicalNode$,
  addImportVisitor$,
  addExportVisitor$,
  addComposerChild$,
  activeEditor$,
  type MdastImportVisitor,
  type LexicalExportVisitor,
} from '@mdxeditor/editor';
import {
  $createTextNode,
  $getNodeByKey,
  $getSelection,
  $isNodeSelection,
  $isRangeSelection,
  $isTextNode,
  COMMAND_PRIORITY_CRITICAL,
  ElementNode,
  KEY_BACKSPACE_COMMAND,
  TextNode,
  type LexicalNode,
} from 'lexical';
import { $isListItemNode } from '@lexical/list';
import type * as Mdast from 'mdast';
import { $createGeraRefNode, GeraRefNode, $isGeraRefNode, type GeraRefKind } from './GeraRefNode';
import { GeraRefTypeahead } from './GeraRefTypeahead';

/* ------------------------------------------------------------------ */
/* Patterns                                                             */
/* ------------------------------------------------------------------ */

/** Factory so each call gets fresh regex state (no shared .lastIndex). */
function makePatterns() {
  return {
    RELATIVE_REF: /@(before|after)\[(\d+[YMWDhm])\]:([\w][\w:.\-]*)/g,
    DATETIME_REF: /@(\d{4}-\d{1,2}-\d{1,2}(?:[T ]\d{2}:\d{2}))/g,
    EVENT_REF: /@(?!before\[|after\[)([a-zA-Z][\w\-]*)/g,
    PROJECT_TAG: /#([a-zA-Z][\w\-]*)/g,
  };
}

function containsGeraRef(text: string): boolean {
  const p = makePatterns();
  return (
    p.RELATIVE_REF.test(text) ||
    p.DATETIME_REF.test(text) ||
    p.EVENT_REF.test(text) ||
    p.PROJECT_TAG.test(text)
  );
}

/** Check whether a Lexical node is inside a checkbox list item (task line). */
function isInsideCheckboxItem(node: LexicalNode): boolean {
  const parent = node.getParent();
  if ($isListItemNode(parent) && parent.getChecked() !== undefined) return true;
  // Could be nested (e.g. inside an inline formatting node)
  if (parent) return isInsideCheckboxItem(parent);
  return false;
}

/* ------------------------------------------------------------------ */
/* Text segmentation                                                    */
/* ------------------------------------------------------------------ */

type TextSegment = { type: 'text'; value: string };
type RefSegment = {
  type: 'ref';
  kind: GeraRefKind;
  value: string;
  offset?: string;
  target?: string;
  datetime?: string;
  event?: string;
  project?: string;
};
type Segment = TextSegment | RefSegment;

interface MatchInfo {
  start: number;
  end: number;
  kind: GeraRefKind;
  value: string;
  offset?: string;
  target?: string;
  datetime?: string;
  event?: string;
  project?: string;
}

/** Split a text string into alternating text / ref segments. */
function parseSegments(text: string): Segment[] {
  const p = makePatterns();
  const matches: MatchInfo[] = [];
  let m: RegExpExecArray | null;

  while ((m = p.RELATIVE_REF.exec(text)) !== null) {
    matches.push({
      start: m.index, end: m.index + m[0].length,
      kind: 'before', value: m[0], offset: m[2], target: m[3],
    });
  }
  while ((m = p.DATETIME_REF.exec(text)) !== null) {
    const canonicalDatetime = m[1].replace(' ', 'T');
    matches.push({
      start: m.index, end: m.index + m[0].length,
      kind: 'datetime', value: `@${canonicalDatetime}`, datetime: canonicalDatetime,
    });
  }
  while ((m = p.EVENT_REF.exec(text)) !== null) {
    matches.push({ start: m.index, end: m.index + m[0].length, kind: 'event', value: m[0], event: m[1] });
  }
  while ((m = p.PROJECT_TAG.exec(text)) !== null) {
    matches.push({ start: m.index, end: m.index + m[0].length, kind: 'project', value: m[0], project: m[1] });
  }

  if (matches.length === 0) return [{ type: 'text', value: text }];

  // Sort by position; skip overlapping matches (keep earliest)
  matches.sort((a, b) => a.start - b.start);
  const deduped: MatchInfo[] = [];
  let cursor = 0;
  for (const mi of matches) {
    if (mi.start < cursor) continue;
    deduped.push(mi);
    cursor = mi.end;
  }

  const segments: Segment[] = [];
  let pos = 0;
  for (const mi of deduped) {
    if (mi.start > pos) {
      segments.push({ type: 'text', value: text.slice(pos, mi.start) });
    }
    segments.push({ type: 'ref', kind: mi.kind, value: mi.value, offset: mi.offset, target: mi.target, datetime: mi.datetime, event: mi.event, project: mi.project });
    pos = mi.end;
  }
  if (pos < text.length) {
    segments.push({ type: 'text', value: text.slice(pos) });
  }

  return segments;
}

/* ------------------------------------------------------------------ */
/* Import visitor: mdast text → Lexical nodes                          */
/* ------------------------------------------------------------------ */

const GeraRefImportVisitor: MdastImportVisitor<Mdast.Text> = {
  /** Match plain text nodes that contain at least one Gera pattern. */
  testNode: (node: Mdast.Nodes): node is Mdast.Text =>
    node.type === 'text' && containsGeraRef((node as Mdast.Text).value),
  /** Higher than the default text visitor (0) so ours runs first. */
  priority: 1000,
  visitNode({ mdastNode, lexicalParent }) {
    // Only create chips inside checkbox list items (task lines)
    const parent = lexicalParent as ElementNode;
    const isCheckbox = $isListItemNode(parent) && parent.getChecked() !== undefined;
    if (!isCheckbox) {
      // Just emit plain text — no chips
      parent.append($createTextNode(mdastNode.value));
      return;
    }
    const segments = parseSegments(mdastNode.value);
    for (const seg of segments) {
      if (seg.type === 'text') {
        parent.append($createTextNode(seg.value));
      } else {
        parent.append(
          $createGeraRefNode(
            seg.kind,
            seg.value,
            seg.offset,
            seg.target,
            seg.datetime,
            seg.event,
            seg.project,
          ),
        );
      }
    }
  },
};

/* ------------------------------------------------------------------ */
/* Export visitor: Lexical GeraRefNode → mdast text                    */
/* ------------------------------------------------------------------ */

const GeraRefExportVisitor: LexicalExportVisitor<GeraRefNode, Mdast.Text> = {
  testLexicalNode: (node: LexicalNode): node is GeraRefNode => $isGeraRefNode(node),
  visitLexicalNode({ lexicalNode, actions }) {
    // Emit the original raw syntax so the markdown file stays clean
    actions.addAndStepInto('text', { value: lexicalNode.__value }, false);
  },
};

/* ------------------------------------------------------------------ */
/* Backspace helper                                                     */
/* ------------------------------------------------------------------ */

import type { RangeSelection } from 'lexical';

/**
 * Given a collapsed RangeSelection, walk leftward from the cursor to find
 * the GeraRefNode immediately before it. Handles:
 *   - text anchor where only whitespace sits between cursor and prev chip
 *   - empty text nodes between cursor text node and the chip
 *   - element anchor (cursor after last child / between children)
 */
function findChipBeforeCursor(selection: RangeSelection): GeraRefNode | null {
  const anchor = selection.anchor;

  if (anchor.type === 'text') {
    const textNode = anchor.getNode();
    const textBefore = textNode.getTextContent().slice(0, anchor.offset);

    // Only look for a chip if the text between start-of-node and cursor is
    // empty or pure whitespace (the trailing separator space we insert).
    if (textBefore.trim().length === 0) {
      let sibling: LexicalNode | null = textNode.getPreviousSibling();
      while (sibling) {
        if ($isGeraRefNode(sibling)) return sibling;
        // Skip empty / whitespace-only text nodes
        if ($isTextNode(sibling) && sibling.getTextContent().trim().length === 0) {
          sibling = sibling.getPreviousSibling();
          continue;
        }
        break;
      }
    }
  }

  if (anchor.type === 'element') {
    const parent = anchor.getNode() as ElementNode;
    if (anchor.offset > 0) {
      const child = parent.getChildAtIndex(anchor.offset - 1);
      if ($isGeraRefNode(child)) return child;
    }
  }

  return null;
}

/* ------------------------------------------------------------------ */
/* Plugin                                                               */
/* ------------------------------------------------------------------ */

export const geraRefsPlugin = realmPlugin({
  init(realm) {
    realm.pubIn({
      [addLexicalNode$]: GeraRefNode,
      [addImportVisitor$]: GeraRefImportVisitor,
      [addExportVisitor$]: GeraRefExportVisitor,
      [addComposerChild$]: GeraRefTypeahead,
    });

    /* ---- runtime hooks (backspace, re-chip, cursor tracking) ---- */

    let unregisterBackspace: (() => void) | null = null;
    let unregisterTransform: (() => void) | null = null;
    let unregisterSelectionWatcher: (() => void) | null = null;
    let lastSelectionTextNodeKey: string | null = null;

    realm.sub(activeEditor$, (editor) => {
      unregisterBackspace?.();
      unregisterTransform?.();
      unregisterSelectionWatcher?.();
      unregisterBackspace = null;
      unregisterTransform = null;
      unregisterSelectionWatcher = null;
      lastSelectionTextNodeKey = null;
      if (!editor) return;

      /* -- Step 0: backspace removes chip ----------------------------- */
      unregisterBackspace = editor.registerCommand(
        KEY_BACKSPACE_COMMAND,
        (event: KeyboardEvent) => {
          const selection = $getSelection();
          if (!selection) return false;

          // Collapsed cursor — find and remove the chip immediately before cursor
          if ($isRangeSelection(selection) && selection.isCollapsed()) {
            const chip = findChipBeforeCursor(selection);
            if (chip) {
              event.preventDefault();
              // Also remove any whitespace-only text nodes between chip and cursor
              const anchor = selection.anchor;
              if (anchor.type === 'text') {
                const textNode = anchor.getNode();
                const textBefore = textNode.getTextContent().slice(0, anchor.offset);
                if (textBefore.trim().length === 0) {
                  // Remove the whitespace prefix or the whole node if it's all whitespace
                  const textAfter = textNode.getTextContent().slice(anchor.offset);
                  if (textAfter.length > 0) {
                    textNode.setTextContent(textAfter);
                    textNode.select(0, 0);
                  } else {
                    textNode.remove();
                  }
                }
              }
              chip.remove();
              return true;
            }
          }

          // Node-selection of the chip itself (arrow-key selected, or clicked)
          if ($isNodeSelection(selection)) {
            const nodes = selection.getNodes();
            if (nodes.length === 1 && $isGeraRefNode(nodes[0])) {
              event.preventDefault();
              const chip = nodes[0];
              const next = chip.getNextSibling();
              const prev = chip.getPreviousSibling();
              chip.remove();
              // Place cursor sensibly after removal
              if (next && $isTextNode(next)) {
                next.select(0, 0);
              } else if (prev && $isTextNode(prev)) {
                prev.selectEnd();
              }
              return true;
            }
          }

          return false;
        },
        COMMAND_PRIORITY_CRITICAL,
      );

      /* -- Step 1: re-chip transform --------------------------------- */
      unregisterTransform = editor.registerNodeTransform(TextNode, (node) => {
        const text = node.getTextContent();
        if (!containsGeraRef(text)) return;

        // Only transform text inside checkbox list items (task lines)
        if (!isInsideCheckboxItem(node)) return;

        // Skip if cursor is currently inside this node (don't interrupt typing)
        const key = node.getKey();
        const selection = $getSelection();
        if ($isRangeSelection(selection)) {
          const { anchor, focus } = selection;
          if (anchor.key === key || focus.key === key) return;
        }

        const segments = parseSegments(text);
        if (segments.length === 1 && segments[0].type === 'text') return;

        const [first, ...rest] = segments;
        let prevNode: LexicalNode;

        if (first.type === 'text') {
          node.setTextContent(first.value);
          prevNode = node;
        } else {
          const refNode = $createGeraRefNode(
            first.kind, first.value, first.offset, first.target,
            first.datetime, first.event, first.project,
          );
          node.replace(refNode);
          prevNode = refNode;
        }

        for (const seg of rest) {
          const newNode: LexicalNode =
            seg.type === 'text'
              ? $createTextNode(seg.value)
              : $createGeraRefNode(
                  seg.kind, seg.value, seg.offset, seg.target,
                  seg.datetime, seg.event, seg.project,
                );
          prevNode.insertAfter(newNode);
          prevNode = newNode;
        }
      });

      /* -- Selection watcher: mark previous text node dirty ---------- */
      // Node transforms only run on dirty nodes. Moving the cursor away
      // doesn't dirty the old text node, so we watch selection changes and
      // mark the previous text node dirty to trigger the re-chip transform.
      unregisterSelectionWatcher = editor.registerUpdateListener(({ editorState }) => {
        let currentKey: string | null = null;

        editorState.read(() => {
          const sel = $getSelection();
          if ($isRangeSelection(sel) && sel.isCollapsed()) {
            const anchorNode = sel.anchor.getNode();
            if ($isTextNode(anchorNode)) {
              currentKey = anchorNode.getKey();
            }
          }
        });

        const previousKey = lastSelectionTextNodeKey;
        lastSelectionTextNodeKey = currentKey;

        if (!previousKey || previousKey === currentKey) return;

        editor.update(() => {
          const prevNode = $getNodeByKey(previousKey);
          if ($isTextNode(prevNode)) {
            prevNode.markDirty();
          }
        });
      });
    });
  },
});
