import { expect, test, type Page } from '@playwright/test'

async function login(page: Page, role: 'Admin' | 'Manager' | 'Employee') {
  const labels = { Admin: 'Quản trị viên', Manager: 'Quản lý', Employee: 'Nhân viên' } as const
  await page.goto('/login')
  await page.getByRole('button', { name: labels[role], exact: true }).click()
  await page.locator('form button').click()
  await expect(page).toHaveURL(/\/dashboard$/)
}

test('Admin xem báo cáo và quản trị người dùng', async ({ page }) => {
  await login(page, 'Admin')
  await page.goto('/reports')
  await expect(page.getByRole('heading', { name: 'Báo cáo vận hành' })).toBeVisible()
  await expect(page.getByText('Khối lượng đội ngũ')).toBeVisible()
  await page.goto('/admin')
  await expect(page.getByRole('heading', { name: 'Quản trị người dùng' })).toBeVisible()
  await expect(page.getByLabel(/Vai trò Nguyễn Quản lý/)).toHaveValue('MANAGER')
})

test('Employee đọc thông báo và lưu tùy chọn cá nhân', async ({ page }) => {
  await login(page, 'Employee')
  await page.goto('/notifications')
  const readButton = page.getByRole('button', { name: 'Đánh dấu đã đọc' }).first()
  await expect(readButton).toBeVisible()
  await readButton.click()
  await page.goto('/profile')
  const firstSwitch = page.getByRole('switch').first()
  const before = await firstSwitch.getAttribute('aria-checked')
  await firstSwitch.click()
  await page.getByRole('button', { name: 'Lưu tùy chọn' }).click()
  await page.reload()
  await expect(page.getByRole('switch').first()).toHaveAttribute('aria-checked', before === 'true' ? 'false' : 'true')
})

test('Employee tải avatar hợp lệ', async ({ page }) => {
  await login(page, 'Employee')
  await page.goto('/profile')
  const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64')
  await page.locator('input[type="file"]').setInputFiles({ name: 'avatar.png', mimeType: 'image/png', buffer: png })
  await expect(page.getByAltText(/Ảnh đại diện/)).toBeVisible()
})
