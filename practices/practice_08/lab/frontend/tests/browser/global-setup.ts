import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve, join } from 'node:path';
import { build } from 'vite';

export default async function setup() {
    const outDir = await mkdtemp(join(tmpdir(), 'animemap-ui-'));
    await build({
        configFile: false,
        logLevel: 'error',
        define: { 'process.env.NODE_ENV': '"development"' },
        build: {
            outDir,
            lib: {
                entry: resolve('tests/browser/fixtures/ui.tsx'),
                formats: ['iife'],
                name: 'AnimeMapUITest',
                fileName: () => 'fixture.js',
                cssFileName: 'fixture',
            },
        },
    });
    process.env.UI_FIXTURE_DIR = outDir;
    return async () => { await rm(outDir, { recursive: true }); };
}
