<script setup lang="ts">
import { computed, h, ref, shallowRef, watch } from 'vue';
import type { RouteKey } from '@elegant-router/types';
import type { SelectOption } from 'naive-ui';
import { fetchGetMenuTree, fetchGetRoleMenu, fetchUpdateRoleMenu } from '@/service/api';
import { getRoutePath } from '@/router/elegant/transform';
import { $t } from '@/locales';
import {
  collectLeafIdSet,
  getCheckedKeysByResourceIds,
  getCheckedLeafIds,
  overrideAuthTreeNodeClickBehavior
} from './shared';

defineOptions({
  name: 'MenuAuthModal'
});

interface Props {
  /** the roleId */
  roleId: string;
  byRoleHomeId: string | null;
}

const props = defineProps<Props>();

type EnhancedMenuTree = Api.SystemManage.MenuTree & {
  invalid?: boolean;
  invalidReason?: string;
  originLabel?: string;
  parentPath?: string;
  checkboxDisabled?: boolean;
  children?: EnhancedMenuTree[];
};

type HomeSelectOption = SelectOption & {
  label: string;
  value: string;
  menuPath: string;
};

const visible = defineModel<boolean>('visible', {
  default: false
});

function closeModal() {
  visible.value = false;
}

const title = computed(() => $t('common.edit') + $t('page.manage.role.menuAuth'));

const byRoleHome = shallowRef<string>('');
const checks = shallowRef<string[]>([]);
const expandedKeys = ref<string[]>([]);
const tree = shallowRef<EnhancedMenuTree[]>([]);

function updateHome(val: string | null) {
  if (!val) return;
  byRoleHome.value = val;
  const [homeKey] = getCheckedKeysByResourceIds([val], tree.value);
  if (homeKey) {
    checks.value = Array.from(new Set([...checks.value, homeKey]));
  }
}

const pageSelectOptions = computed<HomeSelectOption[]>(() => {
  const opts: HomeSelectOption[] = [];

  function walk(nodes: EnhancedMenuTree[]) {
    nodes.forEach(node => {
      const children = node.children || [];
      if (children.length) {
        walk(children);
        return;
      }

      if (!node.disabled && !node.isParent && node.resourceId) {
        const label = `${node.originLabel || node.label}${node.meta?.hidden ? '（隐藏）' : ''}`;

        opts.push({
          label,
          value: node.resourceId,
          menuPath: `${node.parentPath || label}${node.meta?.hidden ? '（隐藏）' : ''}`
        });
      }
    });
  }

  walk(tree.value);

  return opts;
});

function renderHomeOptionLabel(option: SelectOption) {
  const homeOption = option as HomeSelectOption;

  return h(
    'div',
    {
      class: 'min-w-0 truncate',
      title: homeOption.menuPath
    },
    homeOption.menuPath || homeOption.label
  );
}

function filterHomeOption(pattern: string, option: SelectOption) {
  const homeOption = option as HomeSelectOption;
  const keyword = pattern.toLowerCase();

  return (
    homeOption.label.toLowerCase().includes(keyword) ||
    homeOption.menuPath.toLowerCase().includes(keyword)
  );
}

const invalidMenus = computed(() => {
  const result: EnhancedMenuTree[] = [];

  function walk(nodes: EnhancedMenuTree[]) {
    nodes.forEach(node => {
      if (node.invalid) {
        result.push(node);
      }
      walk(node.children || []);
    });
  }

  walk(tree.value);

  return result;
});

const selectableLeafIds = computed(() => collectLeafIdSet(tree.value));

function isMenuRegistered(node: Api.SystemManage.MenuTree) {
  return Boolean(node.routeName && getRoutePath(node.routeName as RouteKey));
}

function enhanceMenuTree(nodes: Api.SystemManage.MenuTree[], parentPath = ''): EnhancedMenuTree[] {
  return nodes.map(node => {
    const originLabel = node.label;
    const currentPath = parentPath ? `${parentPath} / ${originLabel}` : originLabel;
    const children = enhanceMenuTree(node.children || [], currentPath);
    const isLeaf = !children.length && !node.isParent;
    const invalid = isLeaf && !isMenuRegistered(node);
    const checkboxDisabled = invalid || (children.length > 0 && children.every(child => child.checkboxDisabled));

    const enhancedNode: EnhancedMenuTree = {
      ...node,
      originLabel,
      parentPath: currentPath,
      label: `${originLabel}${node.meta?.hidden ? '（隐藏）' : ''}${invalid ? '（异常）' : ''}`,
      disabled: invalid,
      checkboxDisabled,
      invalid,
      invalidReason: invalid ? '前端路由未注册' : undefined
    };

    if (children.length) {
      enhancedNode.children = children;
    }

    return enhancedNode;
  });
}

async function getMenuTree() {
  const { error, data } = await fetchGetMenuTree({ includeHidden: true });

  if (!error) {
    return enhanceMenuTree(data);
  }

  return [];
}

function ensureHomeChecked() {
  if (!byRoleHome.value) return;
  const [homeKey] = getCheckedKeysByResourceIds([byRoleHome.value], tree.value);
  if (!homeKey || checks.value.includes(homeKey)) return;
  checks.value = Array.from(new Set([...checks.value, homeKey]));
}

async function getChecks() {
  // request

  const { error, data } = await fetchGetRoleMenu({ id: props.roleId });
  if (!error) {
    return data;
  }

  return null;
}

async function handleSubmit() {
  // console.log(checks.value, props.roleId);
  // request
  if (!byRoleHome.value || !selectableLeafIds.value.has(byRoleHome.value)) {
    window.$message?.error?.('首页菜单未匹配到前端路由，请重新选择');
    return;
  }

  const { error } = await fetchUpdateRoleMenu({
    id: props.roleId,
    byRoleHomeId: byRoleHome.value,
    byRoleMenuIds: getCheckedLeafIds(checks.value, tree.value, byRoleHome.value ? [byRoleHome.value] : [])
  });
  if (error) return;
  window.$message?.success?.($t('common.modifySuccess'));

  closeModal();
}

function init() {
  Promise.all([getChecks(), getMenuTree()]).then(([authData, menuTree]) => {
    tree.value = menuTree;
    checks.value = getCheckedKeysByResourceIds(authData?.byRoleMenuIds || [], menuTree);
    byRoleHome.value = authData?.byRoleHomeId || props.byRoleHomeId || '';
    ensureHomeChecked();
  });
}

watch(visible, val => {
  if (val) {
    init();
  }
});

watch(checks, ensureHomeChecked);
</script>

<template>
  <NModal v-model:show="visible" :title="title" preset="card" class="w-480px">
    <div class="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-12px pb-12px">
      <div class="shrink-0">{{ $t('page.manage.menu.home') }}</div>
      <NSelect
        :value="byRoleHome"
        :options="pageSelectOptions"
        :filter="filterHomeOption"
        :render-label="renderHomeOptionLabel"
        width-mode="trigger"
        size="small"
        class="min-w-0 w-full"
        filterable
        @update:value="updateHome"
      />
    </div>
    <NAlert v-if="invalidMenus.length" type="warning" :show-icon="false" class="mb-12px">
      发现 {{ invalidMenus.length }} 个菜单未匹配到前端路由，已禁用。请检查 routeName。
    </NAlert>
    <NTree
      v-model:checked-keys="checks"
      v-model:expanded-keys="expandedKeys"
      :data="tree"
      :override-default-node-click-behavior="overrideAuthTreeNodeClickBehavior"
      key-field="key"
      cascade
      checkable
      expand-on-click
      virtual-scroll
      block-line
      class="h-280px"
    />
    <template #footer>
      <NSpace justify="end">
        <NButton size="small" class="mt-16px" @click="closeModal">
          {{ $t('common.cancel') }}
        </NButton>
        <NButton type="primary" size="small" class="mt-16px" @click="handleSubmit">
          {{ $t('common.confirm') }}
        </NButton>
      </NSpace>
    </template>
  </NModal>
</template>

<style scoped></style>
