import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

const apiBaseUrl = process.env.E2E_API_BASE_URL ?? 'http://localhost:8010'
const manager = { email: 'qltask', password: '123' }

type ApiEnvelope<T> = { data: T }
type Project = { id: number; name: string }
type Task = {
  id: number
  allowed_transitions: Array<{ code: string; note_required: boolean }>
}

async function login(page: Page) {
  await page.goto('/login')
  await page.getByLabel('Tên đăng nhập hoặc email').fill(manager.email)
  await page.getByLabel('Mật khẩu').fill(manager.password)
  const [loginResponse] = await Promise.all([
    page.waitForResponse((response) => response.url().endsWith('/api/v1/auth/login/') && response.request().method() === 'POST'),
    page.locator('form button').click(),
  ])
  expect(loginResponse.ok()).toBeTruthy()
  const payload = await loginResponse.json() as ApiEnvelope<{ access: string }>
  await expect(page).toHaveURL(/\/dashboard$/)
  return { Authorization: `Bearer ${payload.data.access}` }
}

async function createProject(request: APIRequestContext, headers: Record<string, string>, name: string) {
  const response = await request.post(`${apiBaseUrl}/api/v1/projects/`, {
    headers,
    data: {
      name,
      description: 'Dự án kiểm thử luồng lập kế hoạch',
      start_date: '2026-10-20',
      end_date: '2026-12-31',
    },
  })
  expect(response.status()).toBe(201)
  return (await response.json() as ApiEnvelope<Project>).data
}

async function createTask(
  request: APIRequestContext,
  headers: Record<string, string>,
  data: Record<string, unknown>,
) {
  const response = await request.post(`${apiBaseUrl}/api/v1/tasks/`, { headers, data })
  expect(response.status()).toBe(201)
  return (await response.json() as ApiEnvelope<Task>).data
}

test('luồng lập kế hoạch, checklist, task con và tiến độ có trọng số', async ({ page, request }) => {
  const suffix = Date.now()
  const progressProjectName = `E2E Tiến độ ${suffix}`
  const hierarchyProjectName = `E2E Cha con ${suffix}`
  const plannedTaskName = `E2E Có kế hoạch ${suffix}`
  const checklistFirst = `Phân tích ${suffix}`
  const checklistSecond = `Triển khai ${suffix}`
  let headers: Record<string, string> = {}
  const createdProjectIds: number[] = []

  try {
    headers = await login(page)
    const progressProject = await createProject(request, headers, progressProjectName)
    const hierarchyProject = await createProject(request, headers, hierarchyProjectName)
    createdProjectIds.push(progressProject.id, hierarchyProject.id)

    await page.goto('/tasks')
    await page.getByRole('button', { name: /Giao công việc/i }).click()

    const createDialog = page.getByRole('dialog')
    await createDialog.getByLabel('Tên công việc').fill(plannedTaskName)
    await createDialog.getByLabel('Mô tả').fill('Kiểm thử ngày bắt đầu, giờ ước lượng và checklist')
    await createDialog.getByLabel('Dự án').selectOption({ label: progressProjectName })
    await createDialog.getByLabel('Ngày bắt đầu', { exact: true }).fill('2026-10-22')
    await createDialog.getByLabel('Hạn hoàn thành', { exact: true }).fill('2026-11-30')
    await createDialog.getByLabel('Giờ ước lượng', { exact: true }).fill('2')
    await expect(createDialog.locator(':invalid')).toHaveCount(0)
    await createDialog.getByRole('button', { name: 'Tạo công việc' }).click()

    const plannedCard = page.getByRole('article').filter({ hasText: plannedTaskName })
    await expect(plannedCard).toBeVisible()
    await plannedCard.getByRole('button', { name: 'Chi tiết' }).click()
    const detailDialog = page.getByRole('dialog')
    await expect(detailDialog.getByText('22/10/2026')).toBeVisible()
    await expect(detailDialog.getByText('2.00 giờ')).toBeVisible()

    const taskListResponse = await request.get(
      `${apiBaseUrl}/api/v1/tasks/?project=${progressProject.id}&search=${encodeURIComponent(plannedTaskName)}`,
      { headers },
    )
    expect(taskListResponse.ok()).toBeTruthy()
    const taskList = await taskListResponse.json() as ApiEnvelope<{ results: Task[] }>
    const plannedTask = taskList.data.results.find((task) => task.id)
    expect(plannedTask).toBeTruthy()

    await createTask(request, headers, {
      title: `E2E Trọng số lớn ${suffix}`,
      description: 'Task 6 giờ đã đạt 100 phần trăm',
      project_id: progressProject.id,
      status: 'TODO',
      priority: 2,
      start_date: '2026-10-22',
      estimated_hours: '6',
      progress: 100,
      deadline: '2026-11-30',
    })

    const reportUrl = `${apiBaseUrl}/api/v1/reports/projects/${progressProject.id}/`
    await expect.poll(async () => {
      const response = await request.get(reportUrl, { headers })
      const payload = await response.json() as ApiEnvelope<{ progress: number }>
      return payload.data.progress
    }).toBe(75)

    await detailDialog.getByLabel('Mục mới').fill(checklistFirst)
    await detailDialog.getByRole('button', { name: 'Thêm', exact: true }).click()
    await expect(detailDialog.getByText(checklistFirst)).toBeVisible()
    await detailDialog.getByLabel('Mục mới').fill(checklistSecond)
    await detailDialog.getByRole('button', { name: 'Thêm', exact: true }).click()
    await expect(detailDialog.getByText(checklistSecond)).toBeVisible()

    const firstCheckbox = detailDialog.getByLabel(`Hoàn thành ${checklistFirst}`)
    await firstCheckbox.click()
    await expect(firstCheckbox).toBeChecked()
    await expect(detailDialog.getByText('50%')).toBeVisible()

    await expect.poll(async () => {
      const response = await request.get(reportUrl, { headers })
      const payload = await response.json() as ApiEnvelope<{ progress: number }>
      return payload.data.progress
    }).toBe(88)

    const parent = await createTask(request, headers, {
      title: `E2E Task cha ${suffix}`,
      description: 'Không được hoàn thành khi task con còn dở',
      project_id: hierarchyProject.id,
      status: 'TODO',
      priority: 2,
      estimated_hours: '4',
      progress: 0,
    })
    await createTask(request, headers, {
      title: `E2E Task con ${suffix}`,
      description: 'Task con chưa hoàn thành',
      project_id: hierarchyProject.id,
      status: 'TODO',
      priority: 2,
      parent: parent.id,
      estimated_hours: '4',
      progress: 0,
    })

    const parentResponse = await request.get(`${apiBaseUrl}/api/v1/tasks/${parent.id}/`, { headers })
    const parentDetail = (await parentResponse.json() as ApiEnvelope<Task>).data
    expect(parentDetail.allowed_transitions.map((transition) => transition.code)).not.toContain('COMPLETED')

    const blocked = await request.patch(`${apiBaseUrl}/api/v1/tasks/${parent.id}/status/`, {
      headers,
      data: { status: 'COMPLETED' },
    })
    expect(blocked.status()).toBe(400)

    await page.goto(`/tasks?project=${hierarchyProject.id}`)
    const parentCard = page.getByRole('article').filter({ hasText: `E2E Task cha ${suffix}` })
    const statusSelect = parentCard.getByLabel(`Trạng thái E2E Task cha ${suffix}`)
    await expect(statusSelect).toBeVisible()
    await expect(statusSelect.locator('option', { hasText: 'Đã hoàn thành' })).toHaveCount(0)

    await page.goto(`/projects/${progressProject.id}`)
    await expect(page.getByRole('progressbar', { name: 'Tiến độ dự án' })).toHaveAttribute('aria-valuenow', '88')
  } finally {
    for (const projectId of createdProjectIds.reverse()) {
      await request.delete(`${apiBaseUrl}/api/v1/projects/${projectId}/`, { headers })
    }
  }
})
