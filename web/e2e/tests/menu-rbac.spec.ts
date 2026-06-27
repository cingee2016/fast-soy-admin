import { expect, test } from '@playwright/test';
import { loginAs } from '../utils/page';

test('super admin sees system management menu', async ({ page }) => {
  await loginAs(page, 'Soybean', '123456');
  // 系统管理 / 用户管理 这类菜单仅超管/管理员可见
  await expect(page.getByRole('menuitem').filter({ hasText: /系统管理|System Manage/ })).toBeVisible({
    timeout: 5_000
  });
});

test('common user does not see system management menu', async ({ page }) => {
  await loginAs(page, 'User', '123456');
  await expect(page.getByRole('menuitem').filter({ hasText: /系统管理|System Manage/ })).toHaveCount(0);
});
