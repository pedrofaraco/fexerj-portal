import { execSync } from 'node:child_process'
import { dirname, join } from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const frontendDir = dirname(fileURLToPath(import.meta.url))

function gitCommitShort() {
  const fromEnv = process.env.BUILD_COMMIT?.trim()
  if (fromEnv) return fromEnv

  try {
    return execSync('git rev-parse --short HEAD', {
      encoding: 'utf8',
      cwd: frontendDir,
    }).trim()
  } catch {
    return 'unknown'
  }
}

/**
 * Short hash of the Git tree for `frontend/` at HEAD — same on UAT and prod when
 * that folder matches, even if branch tips (commit SHAs) differ.
 */
function frontendTreeSnapshotShort() {
  const fromEnv = process.env.BUILD_FRONTEND_SNAPSHOT?.trim()
  if (fromEnv) return fromEnv

  const repoRoot = join(frontendDir, '..')
  try {
    return execSync('git rev-parse --short HEAD:frontend', {
      encoding: 'utf8',
      cwd: repoRoot,
    }).trim()
  } catch {
    return 'unknown'
  }
}

/** Injects git SHA + ISO time so the UI can show which bundle is running. */
function injectBuildMeta() {
  return {
    name: 'inject-build-meta',
    config(config) {
      const buildTime = new Date().toISOString()
      config.define = {
        ...config.define,
        __BUILD_COMMIT__: JSON.stringify(gitCommitShort()),
        __FRONTEND_SNAPSHOT__: JSON.stringify(frontendTreeSnapshotShort()),
        __BUILD_TIME__: JSON.stringify(buildTime),
      }
    },
  }
}

export default defineConfig({
  plugins: [injectBuildMeta(), react(), tailwindcss()],
  server: {
    proxy: {
      '/health': 'http://localhost:8000',
      '/me': 'http://localhost:8000',
      '/run': 'http://localhost:8000',
      '/validate': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
    coverage: {
      provider: 'v8',
      reporter: ['text'],
      thresholds: {
        lines: 80,
        statements: 80,
        branches: 80,
        functions: 80,
      },
    },
  },
})
