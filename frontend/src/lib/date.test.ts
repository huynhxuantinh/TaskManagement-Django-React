import { describe, expect, it } from 'vitest'
import { formatDate } from './date'

describe('formatDate', () => {
  it('handles missing and invalid dates without throwing', () => {
    expect(formatDate(null)).toBe('Chưa có ngày')
    expect(formatDate('')).toBe('Chưa có ngày')
    expect(formatDate('invalid')).toBe('Ngày không hợp lệ')
    expect(formatDate('2026-11-16')).toBe('16/11/2026')
  })
})
