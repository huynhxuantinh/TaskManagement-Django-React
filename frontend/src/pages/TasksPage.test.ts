import { describe, expect, it } from 'vitest'

import { buildStatusChangePayload } from '../features/core/statusChange'

describe('buildStatusChangePayload', () => {
  it('omits an optional blank note', () => {
    expect(buildStatusChangePayload('IN_PROGRESS', '   ')).toEqual({ status: 'IN_PROGRESS' })
  })

  it('trims and includes a supplied note', () => {
    expect(buildStatusChangePayload('ON_HOLD', '  Chờ phản hồi  ')).toEqual({
      status: 'ON_HOLD',
      note: 'Chờ phản hồi',
    })
  })
})
