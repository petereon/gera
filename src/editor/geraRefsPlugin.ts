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
  type MdastImportVisitor,
  type LexicalExportVisitor,
} from '@mdxeditor/editor';
import { $createTextNode, ElementNode, type LexicalNode } from 'lexical';
import type * as Mdast from 'mdast';
import { $createGeraRefNode, GeraRefNode, $isGeraRefNode, type GeraRefKind } from './GeraRefNode';

/* ------------------------------------------------------------------ */
/* Patterns                                                             */
/* ------------------------------------------------------------------ */

/** Factory so each call gets fresh regex state (no shared .lastIndex). */
function makePatterns() {
  return {
    BEFORE_REF: /@before\[(\d+[YMWDhm])\]:([\w][\w:.\-]*)/g,
    DATETIME_REF: /@(\d{4}-\d{1,2}-\d{1,2}T\d{2}:\d{2})/g,
    EVENT_REF: /@(?!before\[)([a-zA-Z][\w\-]*)/g,
    PROJECT_TAG: /#([a-zA-Z][\w\-]*)/g,
  };
}

function containsGeraRef(text: string): boolean {
  const p = makePatterns();
  return (
    p.BEFORE_REF.test(text) ||
    p.DATETIME_REF.test(text) ||
    p.EVENT_REF.test(text) ||
    p.PROJECT_TAG.test(text)
  );
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

  while ((m = p.BEFORE_REF.exec(text)) !== null) {
    matches.push({ start: m.index, end: m.index + m[0].length, kind: 'before', value: m[0], offset: m[1], target: m[2] });
  }
  while ((m = p.DATETIME_REF.exec(text)) !== null) {
    matches.push({ start: m.index, end: m.index + m[0].length, kind: 'datetime', value: m[0], datetime: m[1] });
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
    const segments = parseSegments(mdastNode.value);
    const parent = lexicalParent as ElementNode;
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
/* Plugin                                                               */
/* ------------------------------------------------------------------ */

export const geraRefsPlugin = realmPlugin({
  init(realm) {
    realm.pubIn({
      [addLexicalNode$]: GeraRefNode,
      [addImportVisitor$]: GeraRefImportVisitor,
      [addExportVisitor$]: GeraRefExportVisitor,
    });
  },
});
