<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue';
import { fetchGetMenuButtonTree, fetchGetRoleButton, fetchUpdateRoleButton } from '@/service/api';
import { $t } from '@/locales';
import {
  enhanceAuthTreeNodes,
  getCheckedKeysByResourceIds,
  getCheckedLeafIds,
  overrideAuthTreeNodeClickBehavior
} from './shared';

defineOptions({
  name: 'ButtonAuthModal'
});

interface Props {
  /** the roleId */
  roleId: string;
}

const props = defineProps<Props>();

const visible = defineModel<boolean>('visible', {
  default: false
});

function closeModal() {
  visible.value = false;
}

const title = computed(() => $t('common.edit') + $t('page.manage.role.buttonAuth'));

// type ButtonConfig = {
//   id: number;
//   label: string;
//   code: string;
// };

// const tree = shallowRef<ButtonConfig[]>([]);
const tree = shallowRef<Api.SystemManage.ButtonTree[]>([]);

async function getButtonTree() {
  const { error, data } = await fetchGetMenuButtonTree();
  if (!error) {
    return enhanceAuthTreeNodes(data);
  }

  return [];
}

const byRoleButtonIds = shallowRef<string[]>([]);

async function getChecks() {
  const { error, data } = await fetchGetRoleButton({ id: props.roleId });
  if (!error) {
    return data.byRoleButtonIds || [];
  }

  return [];
}

async function handleSubmit() {
  // console.log(checks.value, props.roleId);
  // request

  const { error } = await fetchUpdateRoleButton({
    id: props.roleId,
    byRoleButtonIds: getCheckedLeafIds(byRoleButtonIds.value, tree.value)
  });
  if (error) return;
  window.$message?.success?.($t('common.modifySuccess'));

  closeModal();
}

function init() {
  Promise.all([getChecks(), getButtonTree()]).then(([resourceIds, buttonTree]) => {
    tree.value = buttonTree;
    byRoleButtonIds.value = getCheckedKeysByResourceIds(resourceIds, buttonTree);
  });
}

watch(visible, val => {
  if (val) {
    init();
  }
});
</script>

<template>
  <NModal v-model:show="visible" :title="title" preset="card" class="w-480px">
    <NTree
      v-model:checked-keys="byRoleButtonIds"
      :data="tree"
      key-field="key"
      :override-default-node-click-behavior="overrideAuthTreeNodeClickBehavior"
      default-expand-all
      block-line
      cascade
      checkable
      expand-on-click
      virtual-scroll
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
