import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { ReportProgress } from './ReportProgress'

afterEach(cleanup)

it('shows missing estimates and the weight assumptions alongside report progress', () => {
  render(<ReportProgress value={40} label="Tiến độ tổng" missingEstimateCount={2} />)
  expect(screen.getByRole('progressbar', { name: 'Tiến độ tổng' })).toHaveAttribute('aria-valuenow', '40')
  expect(screen.getByText(/2 công việc tính tiến độ thiếu giờ ước lượng/)).toHaveTextContent('trọng số bằng nhau')
})
