import { describe, expect, it } from 'vitest'

import { buildStatusChangePayload } from '../features/core/statusChange'
import { buildTaskListParams } from './taskFilters'

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

describe('buildTaskListParams', () => {
  it('includes assignee, status and ordering filters', () => {
    const params = buildTaskListParams({
      search: '',
      project: '3',
      assignee: '8',
      status: 'IN_PROGRESS',
      priority: '',
      deadlineFrom: '',
      deadlineTo: '',
      deadlinePreset: '',
      ordering: '-priority',
    })

    expect(params.get('project')).toBe('3')
    expect(params.get('assignee')).toBe('8')
    expect(params.get('status')).toBe('IN_PROGRESS')
    expect(params.get('ordering')).toBe('-priority')
  })
})
