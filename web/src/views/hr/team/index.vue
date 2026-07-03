<script setup lang="tsx">
import { onMounted, reactive, ref } from 'vue';
import { NButton, NPopconfirm, NTag } from 'naive-ui';
import { employeeStatusOptions, employeeStatusRecord, employeeStatusTagType } from '@/constants/business';
import {
  fetchGetTagList,
  fetchRegularizeTeamEmployee,
  fetchTeamEmployees,
  fetchTeamStats,
  fetchUpdateSubordinateTags
} from '@/service/api';
import { useAppStore } from '@/store/modules/app';
import { defaultTransform, useNaivePaginatedTable } from '@/hooks/common/table';
import { useAuth } from '@/hooks/business/auth';
import { $t } from '@/locales';
import TeamTagDialog from './modules/team-tag-dialog.vue';

const appStore = useAppStore();
const { hasAuth } = useAuth();

const stats = ref<Api.HrPersonal.TeamStats | null>(null);

const searchParams = reactive<Api.HrManage.EmployeeSearchParams>({
  current: 1,
  size: 10,
  name: null,
  status: null
});

const { columns, columnChecks, data, loading, getData, mobilePagination } = useNaivePaginatedTable({
  api: () => fetchTeamEmployees(searchParams),
  transform: response => defaultTransform(response),
  onPaginationParamsChange: params => {
    searchParams.current = params.page;
    searchParams.size = params.pageSize;
  },
  columns: () => [
    { key: 'index', title: $t('common.index'), width: 64, align: 'center', render: (_, index) => index + 1 },
    { key: 'name', title: $t('page.hr.employee.name'), align: 'center', minWidth: 100 },
    { key: 'employeeNo', title: $t('page.hr.employee.employeeNo'), align: 'center', minWidth: 100 },
    { key: 'position', title: $t('page.hr.employee.position'), minWidth: 100 },
    { key: 'email', title: $t('page.hr.employee.email'), minWidth: 160 },
    {
      key: 'tagNames',
      title: $t('page.hr.employee.tags'),
      minWidth: 150,
      render: row => (row.tagNames || []).map((s: string) => <NTag size="small" class="mr-4px">{s}</NTag>)
    },
    {
      key: 'status',
      title: $t('page.hr.common.status'),
      align: 'center',
      width: 90,
      render: row => {
        if (!row.status) return null;
        return <NTag type={employeeStatusTagType[row.status]}>{$t(employeeStatusRecord[row.status])}</NTag>;
      }
    },
    {
      key: 'operate',
      title: $t('common.operate'),
      align: 'center',
      width: 180,
      render: row => (
        <div class="flex-center gap-8px">
          {row.status === 'probation' && hasAuth('B_HR_TEAM_REGULARIZE') && (
            <NPopconfirm onPositiveClick={() => handleRegularize(row.id)}>
              {{
                default: () => $t('page.hr.employee.transition.confirm'),
                trigger: () => (
                  <NButton type="info" ghost size="small">
                    {$t('page.hr.employee.transition.toActive')}
                  </NButton>
                )
              }}
            </NPopconfirm>
          )}
          {hasAuth('B_HR_TEAM_TAG_EDIT') && (
            <NButton type="warning" ghost size="small" onClick={() => openTagDialog(row)}>
              {$t('page.hr.team.editTags')}
            </NButton>
          )}
        </div>
      )
    }
  ]
});

async function handleRegularize(id: string) {
  const { error } = await fetchRegularizeTeamEmployee(id);
  if (error) return;
  window.$message?.success($t('page.hr.employee.transition.success'));
  await Promise.all([getData(), loadStats()]);
}

const tagDialogVisible = ref(false);
const tagDialogTarget = ref<Api.HrManage.Employee | null>(null);
function openTagDialog(row: Api.HrManage.Employee) {
  tagDialogTarget.value = row;
  tagDialogVisible.value = true;
}
async function handleTagSubmit(tagIds: string[]) {
  if (!tagDialogTarget.value) return;
  const { error } = await fetchUpdateSubordinateTags(tagDialogTarget.value.id, tagIds);
  if (error) return;
  window.$message?.success($t('common.updateSuccess'));
  tagDialogVisible.value = false;
  await getData();
}

const tagOptions = ref<{ label: string; value: string }[]>([]);
async function loadTagOptions() {
  const { data: tagData } = await fetchGetTagList({ current: 1, size: 999 });
  tagOptions.value = (tagData?.records ?? []).map(t => ({ label: t.name, value: t.id }));
}

async function loadStats() {
  const { data: s } = await fetchTeamStats();
  stats.value = s ?? null;
}

onMounted(async () => {
  await Promise.all([loadStats(), loadTagOptions()]);
});
</script>

<template>
  <div class="flex-col-stretch gap-16px overflow-hidden lt-sm:overflow-auto">
    <NCard v-if="stats" :bordered="false" size="small" class="card-wrapper">
      <NDescriptions :column="3" size="small" label-placement="left">
        <NDescriptionsItem :label="$t('page.hr.team.department')">{{ stats.department.name }}</NDescriptionsItem>
        <NDescriptionsItem :label="$t('page.hr.team.total')">{{ stats.total }}</NDescriptionsItem>
        <NDescriptionsItem :label="$t('page.hr.team.statusBreakdown')">
          <NSpace>
            <NTag v-for="opt in employeeStatusOptions" :key="opt.value" :type="employeeStatusTagType[opt.value]">
              {{ $t(opt.label) }}: {{ stats.statusCounts[opt.value] ?? 0 }}
            </NTag>
          </NSpace>
        </NDescriptionsItem>
      </NDescriptions>
    </NCard>

    <NCard :title="$t('page.hr.team.title')" :bordered="false" size="small" class="card-wrapper sm:flex-1-hidden">
      <template #header-extra>
        <TableHeaderOperation v-model:columns="columnChecks" :loading="loading" @refresh="getData" />
      </template>
      <NDataTable
        :columns="columns"
        :data="data"
        size="small"
        :flex-height="!appStore.isMobile"
        :scroll-x="1000"
        :loading="loading"
        remote
        :row-key="row => row.id"
        :pagination="mobilePagination"
        class="sm:h-full"
      />
      <TeamTagDialog
        v-model:visible="tagDialogVisible"
        :target="tagDialogTarget"
        :tag-options="tagOptions"
        @submitted="handleTagSubmit"
      />
    </NCard>
  </div>
</template>
