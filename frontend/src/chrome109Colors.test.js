/**
 * Guards the Chrome 109 colour rule stated in CLAUDE.md.
 *
 * Minimum supported browser is Chrome 109 on Windows 7 — a real FEXERJ
 * operator, not a hypothetical one. Tailwind v4 emits `oklch()` and
 * `color-mix()` for its colour utilities, and Chrome 109 ignores declarations
 * it cannot parse: the element keeps the inherited or default colour, so text
 * goes invisible or unstyled while the layout still looks right.
 *
 * `build.target: chrome109` does not help — it lowers syntax, not colour
 * functions. And nobody on the team can see the breakage: the only Chrome 109
 * machine belongs to the operator who cannot work around it. Hence a test.
 *
 * All colour must come from the named classes in `index.css` (`.t-fg`,
 * `.t-body`, `.btn-primary`, …), which are plain hex. Tailwind's spacing and
 * layout utilities (`flex`, `gap-4`, `px-4`, `text-sm`) are safe and stay
 * allowed — only the palette is off limits.
 */
import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

const SRC = path.join(import.meta.dirname, '.')

// Tailwind's default palette, plus the keywords that also resolve to a colour.
const PALETTE = [
  'slate', 'gray', 'zinc', 'neutral', 'stone',
  'red', 'orange', 'amber', 'yellow', 'lime', 'green', 'emerald', 'teal',
  'cyan', 'sky', 'blue', 'indigo', 'violet', 'purple', 'fuchsia', 'pink', 'rose',
  'white', 'black',
].join('|')

// Every utility prefix that takes a colour. `text-` and `border-` also have
// non-colour forms (`text-sm`, `border-2`), which the palette list excludes.
const PREFIX = [
  'text', 'bg', 'border', 'ring', 'divide', 'fill', 'stroke', 'placeholder',
  'shadow', 'outline', 'accent', 'caret', 'decoration', 'from', 'via', 'to',
].join('|')

// Optional variant prefix (hover:, sm:, dark:) and optional shade (-700, /50).
const COLOUR_UTILITY = new RegExp(
  String.raw`(?<![\w-])(?:[a-z-]+:)*(?:${PREFIX})-(?:${PALETTE})(?:-\d{2,3})?(?:/\d{1,3})?(?![\w-])`,
  'g',
)

/** Every shipped source file: tests never reach the browser. */
function sourceFiles(dir = SRC) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) return entry.name === 'test' ? [] : sourceFiles(full)
    if (!/\.jsx?$/.test(entry.name)) return []
    if (/\.test\.jsx?$/.test(entry.name)) return []
    return [full]
  })
}

describe('Chrome 109 colour rule', () => {
  it('finds no Tailwind colour utility in the shipped sources', () => {
    const offenders = []
    for (const file of sourceFiles()) {
      const lines = fs.readFileSync(file, 'utf8').split('\n')
      lines.forEach((line, i) => {
        for (const match of line.matchAll(COLOUR_UTILITY)) {
          offenders.push(`${path.relative(SRC, file)}:${i + 1}: ${match[0]}`)
        }
      })
    }

    expect(
      offenders,
      'Tailwind colour utilities emit oklch()/color-mix(), which Chrome 109 ignores — ' +
        'the text renders invisible for the FEXERJ operator on Windows 7. Use a named ' +
        'class from index.css instead (.t-fg, .t-body, .t-muted, .btn-primary, …). ' +
        'If a comment merely names one of these utilities, reword it: this check reads ' +
        'the whole file, so the token must not appear at all.',
    ).toEqual([])
  })

  it('scans the files that actually ship, and only those', () => {
    // A guard that silently scans nothing passes forever. Pin both ends: the
    // real components are in, tests are out.
    const scanned = sourceFiles().map(f => path.relative(SRC, f))
    expect(scanned).toContain('pages/RunPage.jsx')
    expect(scanned).toContain('components/PeriodSummary.jsx')
    expect(scanned).toContain('ResultsPage.jsx')
    expect(scanned.some(f => f.includes('.test.'))).toBe(false)
    expect(scanned.some(f => f.startsWith('test/'))).toBe(false)
  })

  it('recognizes a colour utility when it sees one', () => {
    // Without this, a regex that matches nothing would keep the suite green.
    for (const violation of [
      '<p className="text-gray-700">',
      '<div className="bg-blue-600 px-4">',
      '<span className="hover:text-red-500">',
      '<div className="border-slate-200">',
      '<p className="bg-white">',
    ]) {
      expect(violation.match(COLOUR_UTILITY), violation).not.toBeNull()
    }
  })

  it('leaves the layout and spacing utilities alone', () => {
    for (const allowed of [
      '<div className="flex flex-col gap-6 px-4 py-3">',
      '<p className="text-sm font-medium t-body">',
      '<table className="w-full mt-3">',
      '<th className="text-left t-muted">',
      '<div className="results-outline-card border-t">',
      '<button className="btn-primary w-full sm:w-auto">',
    ]) {
      expect(allowed.match(COLOUR_UTILITY), allowed).toBeNull()
    }
  })
})
