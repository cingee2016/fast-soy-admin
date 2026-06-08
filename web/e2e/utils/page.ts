import type { Page } from '@playwright/test';
import { expect } from '@playwright/test';

const LOGIN_TIMEOUT_MS = 15_000;
const LOGIN_ATTEMPTS = 2;

export async function loginAs(page: Page, userName: string, password: string) {
  for (let attempt = 0; attempt < LOGIN_ATTEMPTS; attempt += 1) {
    await page.goto('/login');
    await page.locator('input').nth(0).fill(userName);
    await page.locator('input[type="password"]').fill(password);
    await page.getByRole('button', { name: '确认', exact: true }).click();

    if (await waitForLoggedIn(page, userName)) {
      return;
    }
  }

  throw new Error(`login timed out for ${userName}`);
}

export async function quickLoginSuper(page: Page) {
  for (let attempt = 0; attempt < LOGIN_ATTEMPTS; attempt += 1) {
    await page.goto('/login');
    await page.getByRole('button', { name: '超级管理员', exact: true }).click();

    if (await waitForLoggedIn(page, 'Soybean')) {
      return;
    }
  }

  throw new Error('quick login timed out for Soybean');
}

async function waitForLoggedIn(page: Page, userName: string): Promise<boolean> {
  try {
    await page.waitForFunction(
      name => {
        const isAwayFromLogin = !window.location.pathname.startsWith('/login');
        const hasUserButton = Array.from(document.querySelectorAll('button')).some(button =>
          button.textContent?.includes(name)
        );

        return isAwayFromLogin || hasUserButton;
      },
      userName,
      { timeout: LOGIN_TIMEOUT_MS }
    );

    if (new URL(page.url()).pathname.startsWith('/login')) {
      await page.goto('/home');
    }

    return true;
  } catch {
    return false;
  }
}

/**
 * 打开内部页面并校验 URL 稳定（未被守卫重定向到 403/404/500/login），
 * 同时校验页面整体未渲染明显错误内容。
 */
export async function expectPageOpens(page: Page, path: string) {
  await page.goto(path);
  await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {});
  await expect(page).toHaveURL(new RegExp(path.replace(/\//g, '\\/').replace(/:[^/]+/g, '[^/?#]+')));
  const url = page.url();
  expect(url).not.toMatch(/\/(403|404|500)(\?|$|#)/);
  expect(url).not.toMatch(/\/login(\/|\?|$|#)/);
}
