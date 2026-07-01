<script setup lang="tsx">
import { reactive, ref } from 'vue';
import { NPopconfirm, NSwitch, NTag } from 'naive-ui';
import { apiMethodRecord, statusTypeRecord } from '@/constants/business';
import { fetchGetApiList, fetchUpdateApiStatus } from '@/service/api';
import { useAppStore } from '@/store/modules/app';
import { defaultTransform, useNaivePaginatedTable } from '@/hooks/common/table';
import { $t } from '@/locales';
import ApiSearch from './modules/api-search.vue';

const appStore = useAppStore();

const defaultSearchParams: Api.SystemManage.ApiSearchParams = {
  current: 1,
  size: 10,
  statusType: null,
  apiPath: null,
  apiMethod: null,
  summary: null,
  tags: null,
  includeSystem: true
};

const searchParams: Api.SystemManage.ApiSearchParams = reactive({ ...defaultSearchParams });

const updatingStatusIds = ref<string[]>([]);

const { columns, columnChecks, data, getData, getDataByPage, loading, mobilePagination } = useNaivePaginatedTable({
  api: () => fetchGetApiList(searchParams),
  transform: response => defaultTransform(response),
  onPaginationParamsChange: params => {
    searchParams.current = params.page;
    searchParams.size = params.pageSize;
  },
  columns: () => [
    {
      key: 'index',
      title: $t('common.index'),
      align: 'center',
      width: 64,
      render: (_, index) => index + 1
    },
    {
      key: 'apiPath',
      title: $t('page.manage.api.path'),
      align: 'center',
      minWidth: 50
    },
    {
      key: 'apiMethod',
      title: $t('page.manage.api.method'),
      align: 'center',
      width: 100,
      render: row => {
        if (row.apiMethod === null) {
          return null;
        }

        const tagMap: Record<Api.SystemManage.methods, NaiveUI.ThemeColor> = {
          get: 'primary',
          post: 'warning',
          put: 'info',
          patch: 'success',
          delete: 'error'
        };

        const label = $t(apiMethodRecord[row.apiMethod]);

        return <NTag type={tagMap[row.apiMethod]}>{label}</NTag>;
      }
    },
    {
      key: 'summary',
      title: $t('page.manage.api.summary'),
      align: 'center',
      minWidth: 50
    },
    {
      key: 'tags',
      title: $t('page.manage.api.tags'),
      align: 'center',
      width: 300,
      render: row => {
        if (row.tags === null) {
          return null;
        }
        return row.tags.map((tag, index) => (
          <span>
            <NTag type="error">{tag}</NTag>
            {index < row.tags.length - 1 && <span style="margin-right: 4px;"> -&gt;</span>}
          </span>
        ));
      }
    },
    {
      key: 'statusType',
      title: $t('page.manage.api.statusType'),
      align: 'center',
      width: 100,
      render: row => {
        if (row.statusType === null) {
          return null;
        }
        const label = $t(statusTypeRecord[row.statusType]);
        const nextStatus: Api.Common.EnableStatus = row.statusType === '1' ? '2' : '1';
        const confirmText =
          nextStatus === '2' ? '禁用后，已关联该 API 的角色也无法访问该接口。' : '启用后，已关联该 API 的角色将恢复访问该接口。';

        return (
          <NPopconfirm onPositiveClick={() => handleUpdateStatus(row, nextStatus)}>
            {{
              default: () => confirmText,
              trigger: () => (
                <NSwitch
                  size="small"
                  value={row.statusType === '1'}
                  loading={updatingStatusIds.value.includes(row.id)}
                  checkedValue
                  uncheckedValue={false}
                >
                  {{
                    checked: () => label,
                    unchecked: () => $t(statusTypeRecord['2'])
                  }}
                </NSwitch>
              )
            }}
          </NPopconfirm>
        );
      }
    }
  ]
});

async function handleUpdateStatus(row: Api.SystemManage.Api, statusType: Api.Common.EnableStatus) {
  if (updatingStatusIds.value.includes(row.id)) return;

  updatingStatusIds.value = [...updatingStatusIds.value, row.id];
  const { error } = await fetchUpdateApiStatus({ id: row.id, statusType });
  updatingStatusIds.value = updatingStatusIds.value.filter(id => id !== row.id);

  if (error) return;

  window.$message?.success($t('common.updateSuccess'));
  await getData();
}

function resetSearchParams() {
  Object.assign(searchParams, {
    ...defaultSearchParams
  });
  getDataByPage(1);
}
</script>

<template>
  <div class="min-h-500px flex-col-stretch gap-16px overflow-hidden lt-sm:overflow-auto">
    <ApiSearch v-model:model="searchParams" @reset="resetSearchParams" @search="getData" />
    <NCard :title="$t('page.manage.api.title')" :bordered="false" size="small" class="card-wrapper sm:flex-1-hidden">
      <template #header-extra>
        <TableHeaderOperation v-model:columns="columnChecks" :loading="loading" table-id="api" @refresh="getData">
          <template #default>
            <span></span>
          </template>
        </TableHeaderOperation>
      </template>
      <NDataTable
        :columns="columns"
        :data="data"
        size="small"
        :flex-height="!appStore.isMobile"
        :scroll-x="962"
        :loading="loading"
        remote
        :row-key="row => row.id"
        :pagination="mobilePagination"
        class="sm:h-full"
      />
    </NCard>
  </div>
</template>

<style scoped></style>
