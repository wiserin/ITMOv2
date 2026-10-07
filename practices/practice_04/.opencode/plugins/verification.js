export default (async ({ project }) => {
  const isProdFile = (path) => {
    if (!path) return false;
    if (path.startsWith('.opencode/')) return false;
    if (path === 'reflection.md') return false;
    if (path.endsWith('~') || path.endsWith('.swp') || path.endsWith('.tmp')) return false;
    return path.endsWith('.py');
  };

  async function runVerify($) {
    try {
      const result = await $.bash({
        command: 'scripts/verify.sh',
        timeout: 120000,
        workdir: project.directory,
      });
      const ok = result.code === 0;
      const tail = (result.stdout || result.stderr || '').split('\n').slice(-5).join('\n');
      return { ok, code: result.code, tail };
    } catch (err) {
      return { ok: false, code: -1, tail: String(err?.message || err) };
    }
  }

  return {
    async 'tool.execute.after'(input, output, context) {
      const $ = context && context.$ ? context.$ : null;
      if (!$) return;
      const toolName = input?.tool?.name || input?.name || '';

      const editTools = new Set(['apply_patch', 'edit', 'write']);
      if (!editTools.has(toolName)) return;

      const fromOutput = ([]).concat(output?.paths || output?.files || []);
      let paths = fromOutput;
      if ((!paths || paths.length === 0) && toolName === 'apply_patch') {
        const patchText = input?.args?.patchText || input?.patchText || '';
        const matches = Array.from(patchText.matchAll(/^\*\*\* (Add|Update|Delete) File: (.+)$/gm));
        paths = matches.map(m => m[2]);
      }
      const touchedProd = paths.some(isProdFile);
      if (!touchedProd) return;

      if (input?.meta?.source === 'verification-plugin') return;

      const res = await runVerify($);
      const header = '\n[automatic verification]\n' + (res.ok
        ? `PASS: make test succeeded\n`
        : `FAIL: make test exited with code ${res.code}\n${res.tail}\n`);
      output.stdout = (output.stdout || '') + header;
    }
  }
});
