import { expect, test, type Page } from '@playwright/test'

const accounts = {
  Admin: { email: 'admin', password: '123' },
  Manager: { email: 'qltask', password: '123' },
  Employee: { email: 'user', password: '123' },
} as const
const apiBaseUrl = process.env.E2E_API_BASE_URL ?? 'http://localhost:8010'

async function login(page: Page, role: keyof typeof accounts) {
  await page.goto('/login')
  await page.getByLabel('Tên đăng nhập hoặc email').fill(accounts[role].email)
  await page.getByLabel('Mật khẩu').fill(accounts[role].password)
  await page.locator('form button').click()
  await expect(page).toHaveURL(/\/dashboard$/)
}

test('Admin quản lý được dự án và thành viên', async ({ page }) => {
  const projectName = `E2E Admin ${Date.now()}`
  await login(page, 'Admin')
  await page.goto('/projects')
  await page.getByRole('button', { name: /Tạo dự án/i }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Tên dự án').fill(projectName)
  await dialog.getByLabel('Mô tả').fill('Dự án kiểm thử tự động')
  await dialog.getByLabel('Ngày bắt đầu').fill('2026-10-19')
  await dialog.getByLabel('Ngày kết thúc').fill('2026-10-31')
  await dialog.getByRole('button', { name: 'Tạo dự án' }).click()
  await page.getByRole('link', { name: new RegExp(projectName) }).click()
  await expect(page.getByRole('button', { name: `Sửa dự án ${projectName}` })).toBeVisible()
  await expect(page.getByLabel('Thêm bằng email')).toBeVisible()
  page.once('dialog', (confirmation) => confirmation.accept())
  await page.getByRole('button', { name: `Xóa dự án ${projectName}` }).click()
  await expect(page).toHaveURL(/\/projects$/)
})

test('Manager giao và chỉnh sửa công việc trong dự án mình quản lý', async ({ page }) => {
  const taskName = `E2E Task ${Date.now()}`
  await login(page, 'Manager')
  await page.goto('/tasks')
  await page.getByRole('button', { name: /Giao công việc/i }).click()
  const createDialog = page.getByRole('dialog')
  await createDialog.getByLabel('Tên công việc').fill(taskName)
  await createDialog.getByLabel('Mô tả').fill('Công việc kiểm thử tự động')
  await createDialog.getByRole('button', { name: 'Tạo công việc' }).click()
  const taskCard = page.getByRole('article').filter({ hasText: taskName })
  await expect(taskCard).toBeVisible()
  await taskCard.getByRole('button', { name: 'Sửa' }).click()
  await page.getByRole('dialog').getByLabel('Tên công việc').fill(`${taskName} updated`)
  await page.getByRole('dialog').getByRole('button', { name: 'Lưu thay đổi' }).click()
  const updatedCard = page.getByRole('article').filter({ hasText: `${taskName} updated` })
  await expect(updatedCard).toBeVisible()
  page.once('dialog', (confirmation) => confirmation.accept())
  await updatedCard.getByRole('button', { name: 'Xóa' }).click()
  await expect(updatedCard).toHaveCount(0)
})

test('Employee chỉ cập nhật trạng thái và API vẫn chặn tạo dự án', async ({ page, request }) => {
  await login(page, 'Employee')
  await page.goto('/tasks')
  await expect(page.getByRole('button', { name: /Giao công việc/i })).toHaveCount(0)
  await expect(page.locator('select[aria-label^="Trạng thái"]').first()).toBeVisible()

  const loginResponse = await request.post(`${apiBaseUrl}/api/v1/auth/login/`, { data: accounts.Employee })
  const payload = await loginResponse.json()
  const forbidden = await request.post(`${apiBaseUrl}/api/v1/projects/`, {
    headers: { Authorization: `Bearer ${payload.data.access}` },
    data: { name: 'Không được tạo', description: '', start_date: '2026-10-19', end_date: '2026-10-20' },
  })
  expect(forbidden.status()).toBe(403)
})
