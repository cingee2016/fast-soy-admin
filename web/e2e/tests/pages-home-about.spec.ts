import { test } from '@playwright/test';
import { expectPageOpens, loginAs } from '../utils/page';

test.describe('Home', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'Soybean', '123456');
  });

  test('首页 渲染', async ({ page }) => {
    await expectPageOpens(page, '/home');
  });
});
