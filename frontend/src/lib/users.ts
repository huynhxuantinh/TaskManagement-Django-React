import type { User } from '../types/api'

import { apiRequest } from './api'

export interface UpdateUserInput {
  full_name: string
  email: string
}

export function updateUser(userId: number, input: UpdateUserInput) {
  return apiRequest<User>(`/api/v1/users/${userId}/`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
}
