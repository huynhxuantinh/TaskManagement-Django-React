import { readdirSync, readFileSync } from 'node:fs'
import { join, relative } from 'node:path'

import { expect, it } from 'vitest'

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name)
    if (entry.isDirectory()) return sourceFiles(path)
    return entry.name.endsWith('.tsx') ? [path] : []
  })
}

it('does not truncate page-size-100 collections to their first page', () => {
  const sourceRoot = join(process.cwd(), 'src')
  const truncated = sourceFiles(sourceRoot)
    .filter((path) => {
      const source = readFileSync(path, 'utf8')
      return source.includes('page_size=100') && source.includes('useApiResource<Paginated')
    })
    .map((path) => relative(sourceRoot, path))

  expect(truncated).toEqual([])
})
