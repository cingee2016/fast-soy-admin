import { expect, test } from '@playwright/test';
import { API_BASE, authedContext, jsonOk } from '../utils/api';

type AuthTreeMeta = {
  hidden?: boolean;
  invalid?: boolean;
  reason?: string;
};

type AuthTreeNode = {
  key: string;
  label: string;
  isParent: boolean;
  resourceId: string | null;
  routeName?: string | null;
  disabled?: boolean;
  meta?: AuthTreeMeta;
  children?: AuthTreeNode[];
};

const OLD_MENU_TREE_FIELDS = ['id', 'pId', 'component', 'routePath', 'href', 'hideInMenu'];
const OLD_BUTTON_TREE_FIELDS = ['id', 'pId'];
const OLD_API_TREE_FIELDS = ['id', 'summary'];

function expectUnifiedNode(node: AuthTreeNode, oldFields: string[]) {
  expect(typeof node.key).toBe('string');
  expect(node.key.length).toBeGreaterThan(0);
  expect(typeof node.label).toBe('string');
  expect(typeof node.isParent).toBe('boolean');
  expect(node.resourceId === null || typeof node.resourceId === 'string').toBe(true);

  for (const field of oldFields) {
    expect(node).not.toHaveProperty(field);
  }

  if (node.isParent) {
    expect(node.resourceId).toBeNull();
  } else {
    expect(typeof node.resourceId).toBe('string');
  }

  if (node.children) {
    expect(node.children.length).toBeGreaterThan(0);
    node.children.forEach(child => expectUnifiedNode(child, oldFields));
  }
}

function flatten(nodes: AuthTreeNode[]): AuthTreeNode[] {
  return nodes.flatMap(node => [node, ...flatten(node.children || [])]);
}

function leafResourceIds(nodes: AuthTreeNode[]) {
  return flatten(nodes)
    .filter(node => !node.isParent && node.resourceId)
    .map(node => node.resourceId as string);
}

function findParentWithLeaves(nodes: AuthTreeNode[]) {
  return flatten(nodes).find(node => node.isParent && leafResourceIds(node.children || []).length > 0);
}

async function expectBizOk<T>(res: Parameters<typeof jsonOk<T>>[0]) {
  const body = await jsonOk<T>(res);
  expect(body.code).toBe('0000');
  return body.data;
}

test.describe('authorization trees', () => {
  test('menu and API trees expose the unified authorization node shape', async () => {
    const ctx = await authedContext('Soybean', '123456');

    const menuTree = await expectBizOk<AuthTreeNode[]>(
      await ctx.get(`${API_BASE}/system-manage/menus/tree?includeHidden=true`)
    );
    expect(menuTree.length).toBeGreaterThan(0);
    menuTree.forEach(node => expectUnifiedNode(node, OLD_MENU_TREE_FIELDS));

    const home = flatten(menuTree).find(node => node.routeName === 'home');
    expect(home).toMatchObject({
      label: '首页',
      isParent: false,
      meta: { hidden: false }
    });
    expect(typeof home?.resourceId).toBe('string');
    expect(home).not.toHaveProperty('children');

    const systemManage = flatten(menuTree).find(node => node.label === '系统管理');
    expect(systemManage).toMatchObject({ isParent: true, resourceId: null });
    expect(systemManage?.children?.length).toBeGreaterThan(0);

    const hiddenUserDetail = flatten(menuTree).find(node => node.routeName === 'manage_user-detail');
    expect(hiddenUserDetail).toMatchObject({
      isParent: false,
      meta: { hidden: true }
    });
    expect(typeof hiddenUserDetail?.resourceId).toBe('string');

    const apiTree = await expectBizOk<AuthTreeNode[]>(await ctx.get(`${API_BASE}/system-manage/apis/tree`));
    expect(apiTree.length).toBeGreaterThan(0);
    apiTree.forEach(node => expectUnifiedNode(node, OLD_API_TREE_FIELDS));
    expect(findParentWithLeaves(apiTree)).toBeTruthy();

    await ctx.dispose();
  });

  test('button tree uses the same parent and leaf contract', async () => {
    const ctx = await authedContext('Soybean', '123456');
    const suffix = Date.now().toString(36);
    const buttonLabel = `E2E按钮${suffix}`;

    await expectBizOk<{ createdId: string }>(
      await ctx.post(`${API_BASE}/system-manage/menus`, {
        data: {
          menuName: `E2E按钮菜单${suffix}`,
          menuType: '2',
          routeName: `e2e_button_${suffix}`,
          routePath: `/e2e/button-${suffix}`,
          component: 'view.home',
          hideInMenu: true,
          statusType: '2',
          byMenuButtons: [{ buttonCode: `E2E_BUTTON_${suffix}`, buttonDesc: buttonLabel }]
        }
      })
    );

    const buttonTree = await expectBizOk<AuthTreeNode[]>(await ctx.get(`${API_BASE}/system-manage/menus/buttons/tree`));
    expect(buttonTree.length).toBeGreaterThan(0);
    buttonTree.forEach(node => expectUnifiedNode(node, OLD_BUTTON_TREE_FIELDS));

    const buttonLeaf = flatten(buttonTree).find(node => node.label === buttonLabel);
    expect(buttonLeaf).toMatchObject({ isParent: false });
    expect(typeof buttonLeaf?.resourceId).toBe('string');

    await ctx.dispose();
  });

  test('role authorization payloads are leaf resource IDs even when a parent branch is selected', async () => {
    const ctx = await authedContext('Soybean', '123456');
    const suffix = Date.now().toString(36);

    const menuTree = await expectBizOk<AuthTreeNode[]>(
      await ctx.get(`${API_BASE}/system-manage/menus/tree?includeHidden=true`)
    );
    const home = flatten(menuTree).find(node => node.routeName === 'home');
    const menuParent =
      flatten(menuTree).find(node => node.routeName === 'manage_radar') || findParentWithLeaves(menuTree);
    const menuLeafIds = leafResourceIds(menuParent?.children || []);

    expect(typeof home?.resourceId).toBe('string');
    expect(menuParent?.isParent).toBe(true);
    expect(menuLeafIds.length).toBeGreaterThan(0);
    expect(menuParent?.resourceId).toBeNull();

    const createdRole = await expectBizOk<{ createdId: string }>(
      await ctx.post(`${API_BASE}/system-manage/roles`, {
        data: {
          roleName: `E2E角色${suffix}`,
          roleCode: `E2E_${suffix}`,
          roleDesc: 'authorization tree e2e',
          byRoleHomeId: home?.resourceId
        }
      })
    );

    const menuAuth = await expectBizOk<{ byRoleHomeId: string; byRoleMenuIds: string[] }>(
      await ctx.patch(`${API_BASE}/system-manage/roles/${createdRole.createdId}/menus`, {
        data: {
          byRoleHomeId: home?.resourceId,
          byRoleMenuIds: menuLeafIds
        }
      })
    );
    expect(new Set(menuAuth.byRoleMenuIds)).toEqual(new Set([...menuLeafIds, home?.resourceId as string]));

    const savedMenuAuth = await expectBizOk<{ byRoleHomeId: string; byRoleMenuIds: string[] }>(
      await ctx.get(`${API_BASE}/system-manage/roles/${createdRole.createdId}/menus`)
    );
    expect(new Set(savedMenuAuth.byRoleMenuIds)).toEqual(new Set([...menuLeafIds, home?.resourceId as string]));
    expect(savedMenuAuth.byRoleMenuIds).not.toContain(menuParent?.resourceId);

    const apiTree = await expectBizOk<AuthTreeNode[]>(await ctx.get(`${API_BASE}/system-manage/apis/tree`));
    const apiParent = findParentWithLeaves(apiTree);
    const apiLeafIds = leafResourceIds(apiParent?.children || []);
    expect(apiParent?.resourceId).toBeNull();
    expect(apiLeafIds.length).toBeGreaterThan(0);

    const apiAuth = await expectBizOk<{ byRoleApiIds: string[] }>(
      await ctx.patch(`${API_BASE}/system-manage/roles/${createdRole.createdId}/apis`, {
        data: { byRoleApiIds: apiLeafIds }
      })
    );
    expect(new Set(apiAuth.byRoleApiIds)).toEqual(new Set(apiLeafIds));

    await ctx.dispose();
  });
});
