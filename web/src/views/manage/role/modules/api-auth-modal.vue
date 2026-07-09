<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue';
import { fetchGetApiTree, fetchGetRoleApi, fetchUpdateRoleApi } from '@/service/api';
import { $t } from '@/locales';
import {
  enhanceAuthTreeNodes,
  getCheckedKeysByResourceIds,
  getCheckedLeafIds,
  overrideAuthTreeNodeClickBehavior
} from './shared';

defineOptions({
  name: 'ApiAuthModal'
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

const title = computed(() => $t('common.edit') + $t('page.manage.role.apiAuth'));

const tree = shallowRef<Api.SystemManage.ApiTree[]>([]);

async function getTree() {
  const { error, data } = await fetchGetApiTree();
  if (!error) {
    return enhanceAuthTreeNodes(data);
  }

  return [];
}

const byRoleApiIds = shallowRef<string[]>([]);

async function getChecks() {
  const { error, data } = await fetchGetRoleApi({ id: props.roleId });
  if (!error) {
    return data.byRoleApiIds || [];
  }

  return [];
}

async function handleSubmit() {
  // console.log(byRoleApiIds.value, props.roleId);
  // request
  const { error } = await fetchUpdateRoleApi({
    id: props.roleId,
    byRoleApiIds: getCheckedLeafIds(byRoleApiIds.value, tree.value)
  });
  if (error) return;
  window.$message?.success?.($t('common.modifySuccess'));

  closeModal();
}

function init() {
  Promise.all([getChecks(), getTree()]).then(([resourceIds, apiTree]) => {
    tree.value = apiTree;
    byRoleApiIds.value = getCheckedKeysByResourceIds(resourceIds, apiTree);
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
      v-model:checked-keys="byRoleApiIds"
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
