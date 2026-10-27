import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiRequest } from './api'
import { updateUser } from './users'

vi.mock('./api', () => ({ apiRequest: vi.fn() }))

describe('users api', () => {
  beforeEach(() => vi.mocked(apiRequest).mockReset())

  it('updates editable account fields through the user detail endpoint', async () => {
    vi.mocked(apiRequest).mockResolvedValue({ id: 7 })

    await updateUser(7, { full_name: 'Nguyen Van A', email: 'a@example.com' })

    expect(apiRequest).toHaveBeenCalledWith('/api/v1/users/7/', {
      method: 'PATCH',
      body: JSON.stringify({ full_name: 'Nguyen Van A', email: 'a@example.com' }),
    })
  })
})
