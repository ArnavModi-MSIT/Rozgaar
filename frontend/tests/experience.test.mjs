import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

// Use the existing TypeScript compiler and Node test runner; no test-only dependencies.
async function loadSource(relativePath) {
  const source = await readFile(new URL(relativePath, import.meta.url), 'utf8');
  let { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, jsx: ts.JsxEmit.ReactJSX },
  });
  outputText = outputText.replace(/from ["'](react(?:\/jsx-runtime)?)["']/g,
    (_, name) => `from ${JSON.stringify(import.meta.resolve(name))}`);
  return import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
}

const { exceedsExperienceLimit } = await loadSource('../src/experience.ts');
const { default: Sidebar } = await loadSource('../src/components/Sidebar.tsx');

test('up to one year keeps one year and unknowns, excludes larger required/preferred bounds', () => {
  for (const years of [-1, 0, 0.5, 1]) {
    assert.equal(exceedsExperienceLimit({ experience_years: years }, 1), false);
  }
  for (const years of [1.5, 2, 5]) {
    assert.equal(exceedsExperienceLimit({ experience_years: years }, 1), true);
    assert.equal(exceedsExperienceLimit({ experience_years: -1, preferred_experience_years: years }, 1), true);
  }
  assert.equal(exceedsExperienceLimit({ experience_years: 0, preferred_experience_years: 1 }, 1), false);
});

test('changing the limit updates the same exclusion predicate', () => {
  const job = { experience_years: 2, preferred_experience_years: -1 };
  assert.equal(exceedsExperienceLimit(job, 1), true);
  assert.equal(exceedsExperienceLimit(job, 2), false);
  assert.equal(exceedsExperienceLimit({ experience_years: -1 }, 0), false);
});

function sidebar(count) {
  return renderToStaticMarkup(createElement(Sidebar, {
    exportOnly: true,
    filters: { locationText: '', showRemote: false, showNcr: false, showIndia: false,
      hideHighExperience: true, maxExperienceYears: 1 },
    resume: { loaded: false, skills: [], saved_resume: null },
    counts: { highExperience: count, belowThreshold: 0 }, minMatch: 20,
    onFilterChange() {}, onBulkDismiss() {},
  }));
}

test('career export mode exposes the adjustable limit and bulk remove control', () => {
  const html = sidebar(4);
  assert.match(html, /Maximum experience/);
  assert.match(html, /Up to 1 year/);
  assert.match(html, /Remove 4 asking for more than 1 year/);
  assert.match(html, /including those hidden by filters/);
});

test('zero matching jobs leaves a visible disabled remove control', () => {
  assert.match(sidebar(0), /<button[^>]*disabled=""[^>]*>Remove 0 asking for more than 1 year/);
});
