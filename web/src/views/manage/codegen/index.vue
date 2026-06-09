<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import type { DataTableColumns } from 'naive-ui';

type FieldType = 'text' | 'number' | 'enum' | 'relation';

interface FieldConfig {
  name: string;
  label: string;
  type: FieldType;
  note?: string;
}

interface ModelConfig {
  name: string;
  title: string;
  table: string;
  route: string;
  selected: boolean;
  tree: boolean;
  softDelete: boolean;
  dataScopeEnabled: boolean;
  userField: string;
  scopeField: string;
  contains: string[];
  exact: string[];
  listFields: string[];
  searchFields: string[];
  listOrder: string[];
  fields: FieldConfig[];
}

const moduleName = ref('hr');
const moduleCn = ref('HR管理');
const commandKind = ref<'crud' | 'gen' | 'gen-web'>('crud');
const buttonAuth = ref(true);
const activeModelName = ref('Employee');

const commandKindOptions = [
  { label: '前后端 CRUD', value: 'crud' },
  { label: '仅后端', value: 'gen' },
  { label: '仅前端', value: 'gen-web' }
];

const fieldTypeOptions: { label: string; value: FieldType }[] = [
  { label: '文本', value: 'text' },
  { label: '数字', value: 'number' },
  { label: '枚举', value: 'enum' },
  { label: '关系', value: 'relation' }
];

const hrModelDefaults: ModelConfig[] = [
  {
    name: 'Department',
    title: '部门管理',
    table: 'biz_department',
    route: '/hr/department',
    selected: true,
    tree: true,
    softDelete: true,
    dataScopeEnabled: false,
    userField: 'manager_id',
    scopeField: 'id',
    contains: ['name', 'code'],
    exact: ['status'],
    listFields: ['name', 'code', 'manager_id', 'status'],
    searchFields: ['name', 'code', 'status'],
    listOrder: ['order', 'id'],
    fields: [
      { name: 'name', label: '部门名称', type: 'text' },
      { name: 'code', label: '部门编码', type: 'text' },
      { name: 'manager_id', label: '部门主管', type: 'number' },
      { name: 'status', label: '状态', type: 'enum', note: 'StatusType' }
    ]
  },
  {
    name: 'Employee',
    title: '员工管理',
    table: 'biz_employee',
    route: '/hr/employee',
    selected: true,
    tree: false,
    softDelete: true,
    dataScopeEnabled: true,
    userField: 'user_id',
    scopeField: 'department_id',
    contains: ['name', 'employee_no', 'email', 'phone'],
    exact: ['status', 'department_id', 'user_id'],
    listFields: ['name', 'employee_no', 'email', 'position', 'department_id', 'status'],
    searchFields: ['name', 'department_id', 'status'],
    listOrder: ['-created_at', 'id'],
    fields: [
      { name: 'name', label: '员工姓名', type: 'text' },
      { name: 'employee_no', label: '工号', type: 'text' },
      { name: 'email', label: '邮箱', type: 'text' },
      { name: 'phone', label: '电话', type: 'text' },
      { name: 'position', label: '职位', type: 'text' },
      { name: 'user_id', label: '关联系统用户', type: 'relation' },
      { name: 'department_id', label: '所属部门', type: 'relation' },
      { name: 'status', label: '员工状态', type: 'enum', note: 'EmployeeStatus' }
    ]
  },
  {
    name: 'Tag',
    title: '标签管理',
    table: 'biz_tag',
    route: '/hr/tag',
    selected: true,
    tree: false,
    softDelete: false,
    dataScopeEnabled: false,
    userField: 'id',
    scopeField: 'id',
    contains: ['name'],
    exact: ['category'],
    listFields: ['name', 'category', 'description'],
    searchFields: ['name', 'category'],
    listOrder: ['id'],
    fields: [
      { name: 'name', label: '标签名称', type: 'text' },
      { name: 'category', label: '标签分类', type: 'text', note: '字典 tag_category' },
      { name: 'description', label: '标签描述', type: 'text' }
    ]
  }
];

function cloneModel(model: ModelConfig): ModelConfig {
  return {
    ...model,
    contains: [...model.contains],
    exact: [...model.exact],
    listFields: [...model.listFields],
    searchFields: [...model.searchFields],
    listOrder: [...model.listOrder],
    fields: model.fields.map(field => ({ ...field }))
  };
}

const models = reactive<ModelConfig[]>(hrModelDefaults.map(model => cloneModel(model)));
const fieldDraft = reactive<FieldConfig>({ name: '', label: '', type: 'text', note: '' });

const sampleRows: Record<string, Record<string, string>[]> = {
  Department: [
    { id: 'D001', name: '技术部', code: 'TECH', manager_id: '周航', status: '启用' },
    { id: 'D002', name: '人事部', code: 'PERSONNEL', manager_id: '韩梅', status: '启用' }
  ],
  Employee: [
    {
      id: 'E001',
      name: '周航',
      employee_no: 'EMP9001',
      email: 'zhouhang@example.com',
      phone: '13800000001',
      position: '技术主管',
      user_id: 'zhouhang',
      department_id: '技术部',
      status: '在职'
    },
    {
      id: 'E002',
      name: '李沐',
      employee_no: 'EMP9002',
      email: 'limu@example.com',
      phone: '13800000002',
      position: '前端工程师',
      user_id: 'limu',
      department_id: '技术部',
      status: '入职中'
    }
  ],
  Tag: [
    { id: 'T001', name: '远程协作', category: '工作方式', description: '适应远程与混合办公节奏' },
    { id: 'T002', name: '新人导师', category: '团队角色', description: '愿意承担新人带教与融入支持' }
  ]
};

const selectedModels = computed(() => models.filter(model => model.selected));

const activeModel = computed(() => {
  return (
    selectedModels.value.find(model => model.name === activeModelName.value) ?? selectedModels.value[0] ?? models[0]
  );
});

const routePreview = computed(() => selectedModels.value.map(model => `${model.title} ${model.route}`).join(' / '));

const previewColumns = computed<DataTableColumns<Record<string, string>>>(() => {
  const model = activeModel.value;
  const cols: DataTableColumns<Record<string, string>> = [
    { key: 'index', title: '序号', width: 64, align: 'center', render: (_, index) => index + 1 }
  ];

  for (const fieldName of model.listFields) {
    const field = model.fields.find(item => item.name === fieldName);
    cols.push({
      key: fieldName,
      title: field?.label ?? fieldName,
      minWidth: fieldName === 'description' ? 180 : 120,
      ellipsis: { tooltip: true }
    });
  }

  cols.push({ key: 'operate', title: '操作', width: 120, align: 'center', render: () => '编辑 / 删除' });
  return cols;
});

const previewData = computed(() => sampleRows[activeModel.value.name] ?? []);

const selectedFieldSummary = computed(() => {
  const totalFields = selectedModels.value.reduce((total, model) => total + model.fields.length, 0);
  const searchFields = selectedModels.value.reduce((total, model) => total + model.searchFields.length, 0);
  const scoped = selectedModels.value.filter(model => model.dataScopeEnabled).length;
  return { totalFields, searchFields, scoped };
});

function fieldOptions(model: ModelConfig) {
  return model.fields.map(field => ({
    label: `${field.label} (${field.name})`,
    value: field.name
  }));
}

function scopeFieldOptions(model: ModelConfig) {
  const options = [
    { label: '主键 (id)', value: 'id' },
    { label: '创建人 (created_by)', value: 'created_by' },
    ...model.fields
      .filter(field => ['number', 'relation'].includes(field.type) || field.name.endsWith('_id'))
      .map(field => ({
        label: `${field.label} (${field.name})`,
        value: field.name
      }))
  ];
  const seen = new Set<string>();
  return options.filter(option => {
    if (seen.has(option.value)) return false;
    seen.add(option.value);
    return true;
  });
}

function optionFromMap(flag: string, getter: (model: ModelConfig) => string[]) {
  const specs = selectedModels.value
    .map(model => {
      const values = getter(model);
      return values.length ? `${model.name}:${values.join(',')}` : '';
    })
    .filter(Boolean);
  return specs.length ? `${flag} ${specs.join(';')}` : '';
}

function optionFromModels(flag: string, predicate: (model: ModelConfig) => boolean) {
  const values = selectedModels.value.filter(predicate).map(model => model.name);
  return values.length ? `${flag} ${values.join(',')}` : '';
}

function quote(value: string) {
  return `"${value.replaceAll('"', '\\"')}"`;
}

const cliArgs = computed(() => {
  const args = [
    '--yes',
    selectedModels.value.length ? `--models ${selectedModels.value.map(model => model.name).join(',')}` : '',
    optionFromMap('--contains', model => model.contains),
    optionFromMap('--exact', model => model.exact),
    optionFromMap('--list-fields', model => model.listFields),
    optionFromMap('--search-fields', model => model.searchFields),
    optionFromMap('--list-order', model => model.listOrder),
    optionFromModels('--soft-delete', model => model.softDelete),
    optionFromModels('--tree', model => model.tree),
    buttonAuth.value ? '--button-auth' : '',
    ...selectedModels.value
      .filter(model => model.dataScopeEnabled)
      .map(model => `--data-scope ${model.name}:${model.userField},${model.scopeField}`)
  ];

  return args.filter(Boolean).join(' ');
});

const command = computed(() => {
  if (commandKind.value === 'gen') {
    return `just cli-gen ${moduleName.value} ${quote(cliArgs.value)}`;
  }
  if (commandKind.value === 'gen-web') {
    return `just cli-gen-web ${moduleName.value} ${quote(moduleCn.value)} ${quote(cliArgs.value)}`;
  }
  return `just cli-crud ${moduleName.value} ${quote(moduleCn.value)} ${quote(cliArgs.value)}`;
});

const undoCommand = 'just cli-undo "--dry-run"\njust cli-undo';

async function copyText(value: string, label: string) {
  await navigator.clipboard.writeText(value);
  window.$message?.success(`${label}已复制`);
}

function loadHrExample() {
  moduleName.value = 'hr';
  moduleCn.value = 'HR管理';
  commandKind.value = 'crud';
  buttonAuth.value = true;
  activeModelName.value = 'Employee';
  models.splice(0, models.length, ...hrModelDefaults.map(model => cloneModel(model)));
  window.$message?.success('已载入 HR 管理示例');
}

function syncActiveModel(name: string) {
  activeModelName.value = name;
}

function toKebab(value: string) {
  return value
    .replace(/([a-z0-9])([A-Z])/g, '$1-$2')
    .replace(/[_\s]+/g, '-')
    .toLowerCase();
}

function toSnake(value: string) {
  return value
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .replace(/[-\s]+/g, '_')
    .toLowerCase();
}

function nextModelName() {
  let index = models.length + 1;
  let name = `CustomModel${index}`;
  while (models.some(model => model.name === name)) {
    index += 1;
    name = `CustomModel${index}`;
  }
  return name;
}

function addModel() {
  const name = nextModelName();
  const model: ModelConfig = {
    name,
    title: '自定义模型',
    table: `biz_${moduleName.value}_${toSnake(name)}`,
    route: `/${moduleName.value}/${toKebab(name)}`,
    selected: true,
    tree: false,
    softDelete: false,
    dataScopeEnabled: false,
    userField: 'created_by',
    scopeField: 'id',
    contains: ['name'],
    exact: ['status'],
    listFields: ['name', 'status'],
    searchFields: ['name', 'status'],
    listOrder: ['id'],
    fields: [
      { name: 'name', label: '名称', type: 'text' },
      { name: 'status', label: '状态', type: 'enum', note: 'StatusType' }
    ]
  };
  models.push(model);
  activeModelName.value = name;
}

function removeActiveModel() {
  if (models.length <= 1) {
    window.$message?.warning('至少保留一个模型');
    return;
  }
  const index = Math.max(
    0,
    models.findIndex(model => model.name === activeModelName.value)
  );
  models.splice(index, 1);
  activeModelName.value = models[Math.min(index, models.length - 1)].name;
}

function updateModelName(model: ModelConfig, value: string) {
  const previous = model.name;
  model.name = value.trim() || previous;
  if (activeModelName.value === previous) {
    activeModelName.value = model.name;
  }
}

function pruneFieldSelections(model: ModelConfig) {
  const available = new Set(model.fields.map(field => field.name));
  for (const key of ['contains', 'exact', 'listFields', 'searchFields'] as const) {
    model[key] = model[key].filter(fieldName => available.has(fieldName));
  }
  const scopeValues = scopeFieldOptions(model).map(option => option.value);
  if (!scopeValues.includes(model.userField)) model.userField = scopeValues[0] ?? 'id';
  if (!scopeValues.includes(model.scopeField)) model.scopeField = scopeValues[0] ?? 'id';
}

function addField(model: ModelConfig) {
  const name = fieldDraft.name.trim();
  if (!name) {
    window.$message?.warning('先填写字段名');
    return;
  }
  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name)) {
    window.$message?.warning('字段名只能包含字母、数字和下划线，且不能以数字开头');
    return;
  }
  if (model.fields.some(field => field.name === name)) {
    window.$message?.warning('字段已存在');
    return;
  }

  const label = fieldDraft.label.trim() || name;
  const field = { name, label, type: fieldDraft.type, note: fieldDraft.note?.trim() || undefined };
  model.fields.push(field);
  model.listFields.push(name);
  model.searchFields.push(name);
  if (field.type === 'text') {
    model.contains.push(name);
  } else {
    model.exact.push(name);
  }
  fieldDraft.name = '';
  fieldDraft.label = '';
  fieldDraft.type = 'text';
  fieldDraft.note = '';
}

function removeField(model: ModelConfig, fieldName: string) {
  model.fields = model.fields.filter(field => field.name !== fieldName);
  pruneFieldSelections(model);
}
</script>

<template>
  <div class="min-h-500px flex-col-stretch gap-16px overflow-auto codegen-page">
    <NCard :bordered="false" size="small" class="card-wrapper">
      <div class="flex flex-wrap items-start justify-between gap-16px">
        <div class="max-w-760px">
          <div class="mb-8px flex flex-wrap items-center gap-8px">
            <NTag type="primary" size="small">CLI</NTag>
            <NTag type="success" size="small">Git 安全撤销</NTag>
            <NTag type="info" size="small">HR 示例</NTag>
          </div>
          <h2 class="m-0 text-20px font-semibold">代码生成配置台</h2>
          <p class="m-0 mt-8px text-13px text-gray-500">
            选择模型、字段和数据权限范围，生成一条可复制执行的 CLI 命令；页面只规划命令，不直接改文件。
          </p>
        </div>
        <NSpace>
          <NButton secondary @click="loadHrExample">
            <template #icon><icon-ic-round-workspaces class="text-icon" /></template>
            HR 示例
          </NButton>
          <NButton type="primary" ghost @click="copyText(command, '生成命令')">
            <template #icon><icon-ic-round-content-copy class="text-icon" /></template>
            复制命令
          </NButton>
        </NSpace>
      </div>
    </NCard>

    <NGrid responsive="screen" item-responsive :x-gap="16" :y-gap="16">
      <NGridItem span="24 l:9">
        <NCard title="生成目标" :bordered="false" size="small" class="card-wrapper h-full">
          <NSpace vertical :size="14">
            <NForm label-placement="top">
              <NGrid responsive="screen" item-responsive :x-gap="12">
                <NFormItemGi span="24 m:12" label="模块名">
                  <NInput v-model:value="moduleName" placeholder="例如 hr" />
                </NFormItemGi>
                <NFormItemGi span="24 m:12" label="模块中文名">
                  <NInput v-model:value="moduleCn" placeholder="例如 HR管理" />
                </NFormItemGi>
              </NGrid>
              <NFormItem label="生成范围">
                <NRadioGroup v-model:value="commandKind">
                  <NRadioButton v-for="item in commandKindOptions" :key="item.value" :value="item.value">
                    {{ item.label }}
                  </NRadioButton>
                </NRadioGroup>
              </NFormItem>
              <NFormItem label="按钮权限">
                <NSwitch v-model:value="buttonAuth">
                  <template #checked>生成 create/edit/delete 按钮</template>
                  <template #unchecked>不生成按钮权限</template>
                </NSwitch>
              </NFormItem>
            </NForm>
            <NAlert type="info" :show-icon="false">当前预览路由：{{ routePreview || '请选择至少一个模型' }}</NAlert>
            <div class="summary-strip">
              <div>
                <span class="summary-value">{{ selectedModels.length }}</span>
                <span class="summary-label">模型</span>
              </div>
              <div>
                <span class="summary-value">{{ selectedFieldSummary.totalFields }}</span>
                <span class="summary-label">字段</span>
              </div>
              <div>
                <span class="summary-value">{{ selectedFieldSummary.searchFields }}</span>
                <span class="summary-label">搜索项</span>
              </div>
              <div>
                <span class="summary-value">{{ selectedFieldSummary.scoped }}</span>
                <span class="summary-label">数据范围</span>
              </div>
            </div>
          </NSpace>
        </NCard>
      </NGridItem>

      <NGridItem span="24 l:15">
        <NCard title="命令输出" :bordered="false" size="small" class="card-wrapper h-full">
          <NSpace vertical :size="12">
            <div class="command-box">
              <pre class="command-text">{{ command }}</pre>
            </div>
            <NSpace>
              <NButton type="primary" @click="copyText(command, '生成命令')">
                <template #icon><icon-ic-round-content-copy class="text-icon" /></template>
                复制生成命令
              </NButton>
              <NButton secondary @click="copyText(undoCommand, '撤销命令')">
                <template #icon><icon-ic-round-undo class="text-icon" /></template>
                复制撤销命令
              </NButton>
            </NSpace>
            <NAlert type="warning">
              CLI 生成前会检查 Git 工作区，要求当前代码已提交且没有未跟踪文件。撤销会先备份到
              <NText code>codegen_backups/</NText>
              ，再使用 git restore / git clean 退回生成结果。
            </NAlert>
          </NSpace>
        </NCard>
      </NGridItem>
    </NGrid>

    <NCard title="模型与字段配置" :bordered="false" size="small" class="card-wrapper">
      <template #header-extra>
        <NSpace>
          <NButton size="small" secondary @click="addModel">
            <template #icon><icon-ic-round-plus class="text-icon" /></template>
            新增模型
          </NButton>
          <NButton size="small" tertiary @click="removeActiveModel">
            <template #icon><icon-ic-round-delete class="text-icon" /></template>
            删除当前
          </NButton>
        </NSpace>
      </template>
      <NTabs v-model:value="activeModelName" type="line" animated @update:value="syncActiveModel(String($event))">
        <NTabPane v-for="model in models" :key="model.name" :name="model.name" :tab="model.title">
          <NGrid responsive="screen" item-responsive :x-gap="16" :y-gap="12">
            <NGridItem span="24 l:7">
              <NSpace vertical :size="12">
                <div class="model-heading">
                  <div>
                    <div class="text-15px font-medium">{{ model.name }}</div>
                    <div class="text-12px text-gray-500">{{ model.table }}</div>
                  </div>
                  <NSwitch v-model:value="model.selected">
                    <template #checked>生成</template>
                    <template #unchecked>跳过</template>
                  </NSwitch>
                </div>
                <NForm label-placement="top" size="small">
                  <NGrid responsive="screen" item-responsive :x-gap="12">
                    <NFormItemGi span="24 m:12" label="Model 类名">
                      <NInput
                        :value="model.name"
                        placeholder="Employee"
                        @update:value="value => updateModelName(model, value)"
                      />
                    </NFormItemGi>
                    <NFormItemGi span="24 m:12" label="页面标题">
                      <NInput v-model:value="model.title" placeholder="员工管理" />
                    </NFormItemGi>
                    <NFormItemGi span="24 m:12" label="表名">
                      <NInput v-model:value="model.table" placeholder="biz_hr_employee" />
                    </NFormItemGi>
                    <NFormItemGi span="24 m:12" label="路由">
                      <NInput v-model:value="model.route" placeholder="/hr/employee" />
                    </NFormItemGi>
                  </NGrid>
                </NForm>
                <NCheckbox v-model:checked="model.tree">TreeMixin / tree endpoint</NCheckbox>
                <NCheckbox v-model:checked="model.softDelete">SoftDeleteMixin / soft delete</NCheckbox>
                <NCheckbox v-model:checked="model.dataScopeEnabled">启用 data_scope</NCheckbox>
                <NGrid v-if="model.dataScopeEnabled" responsive="screen" item-responsive :x-gap="12">
                  <NFormItemGi span="24 m:12" label="用户字段">
                    <NSelect v-model:value="model.userField" :options="scopeFieldOptions(model)" />
                  </NFormItemGi>
                  <NFormItemGi span="24 m:12" label="范围字段">
                    <NSelect v-model:value="model.scopeField" :options="scopeFieldOptions(model)" />
                  </NFormItemGi>
                </NGrid>
              </NSpace>
            </NGridItem>
            <NGridItem span="24 l:17">
              <NGrid responsive="screen" item-responsive :x-gap="12" :y-gap="12">
                <NGridItem span="24">
                  <div class="field-panel field-list-panel">
                    <div class="field-title">字段清单</div>
                    <div class="field-tags">
                      <NTag
                        v-for="field in model.fields"
                        :key="field.name"
                        closable
                        @close="removeField(model, field.name)"
                      >
                        {{ field.label }} ({{ field.name }})
                      </NTag>
                    </div>
                    <NForm label-placement="top" size="small" class="mt-12px">
                      <NGrid responsive="screen" item-responsive :x-gap="12">
                        <NFormItemGi span="24 m:6" label="字段名">
                          <NInput v-model:value="fieldDraft.name" placeholder="department_id" />
                        </NFormItemGi>
                        <NFormItemGi span="24 m:6" label="显示名">
                          <NInput v-model:value="fieldDraft.label" placeholder="所属部门" />
                        </NFormItemGi>
                        <NFormItemGi span="24 m:5" label="类型">
                          <NSelect v-model:value="fieldDraft.type" :options="fieldTypeOptions" />
                        </NFormItemGi>
                        <NFormItemGi span="24 m:5" label="备注">
                          <NInput v-model:value="fieldDraft.note" placeholder="StatusType / 字典名" />
                        </NFormItemGi>
                        <NFormItemGi span="24 m:2" label=" ">
                          <NButton block type="primary" ghost @click="addField(model)">
                            <template #icon><icon-ic-round-plus class="text-icon" /></template>
                          </NButton>
                        </NFormItemGi>
                      </NGrid>
                    </NForm>
                  </div>
                </NGridItem>
                <NGridItem span="24 m:12">
                  <div class="field-panel">
                    <div class="field-title">模糊查询 contains</div>
                    <NCheckboxGroup v-model:value="model.contains">
                      <NSpace>
                        <NCheckbox v-for="field in fieldOptions(model)" :key="field.value" :value="field.value">
                          {{ field.label }}
                        </NCheckbox>
                      </NSpace>
                    </NCheckboxGroup>
                  </div>
                </NGridItem>
                <NGridItem span="24 m:12">
                  <div class="field-panel">
                    <div class="field-title">精确查询 exact</div>
                    <NCheckboxGroup v-model:value="model.exact">
                      <NSpace>
                        <NCheckbox v-for="field in fieldOptions(model)" :key="field.value" :value="field.value">
                          {{ field.label }}
                        </NCheckbox>
                      </NSpace>
                    </NCheckboxGroup>
                  </div>
                </NGridItem>
                <NGridItem span="24 m:12">
                  <div class="field-panel">
                    <div class="field-title">列表字段</div>
                    <NCheckboxGroup v-model:value="model.listFields">
                      <NSpace>
                        <NCheckbox v-for="field in fieldOptions(model)" :key="field.value" :value="field.value">
                          {{ field.label }}
                        </NCheckbox>
                      </NSpace>
                    </NCheckboxGroup>
                  </div>
                </NGridItem>
                <NGridItem span="24 m:12">
                  <div class="field-panel">
                    <div class="field-title">搜索表单字段</div>
                    <NCheckboxGroup v-model:value="model.searchFields">
                      <NSpace>
                        <NCheckbox v-for="field in fieldOptions(model)" :key="field.value" :value="field.value">
                          {{ field.label }}
                        </NCheckbox>
                      </NSpace>
                    </NCheckboxGroup>
                  </div>
                </NGridItem>
              </NGrid>
            </NGridItem>
          </NGrid>
        </NTabPane>
      </NTabs>
    </NCard>

    <NCard title="CRUD 页面预览" :bordered="false" size="small" class="card-wrapper sm:flex-1-hidden">
      <template #header-extra>
        <NTag type="info">{{ activeModel.title }}</NTag>
      </template>
      <NSpace vertical :size="12">
        <div class="preview-search">
          <NTag v-for="fieldName in activeModel.searchFields" :key="fieldName" round>
            {{ activeModel.fields.find(field => field.name === fieldName)?.label ?? fieldName }}
          </NTag>
          <NButton size="small" secondary>
            <template #icon><icon-ic-round-refresh class="text-icon" /></template>
            重置
          </NButton>
          <NButton size="small" type="primary" ghost>
            <template #icon><icon-ic-round-search class="text-icon" /></template>
            搜索
          </NButton>
        </div>
        <NDataTable
          :columns="previewColumns"
          :data="previewData"
          size="small"
          :scroll-x="900"
          :pagination="{ pageSize: 5 }"
        />
      </NSpace>
    </NCard>
  </div>
</template>

<style scoped>
.codegen-page {
  --codegen-border: rgba(100, 116, 139, 0.18);

  padding-bottom: 56px;
}

.command-box {
  min-height: 92px;
  padding: 12px;
  overflow: auto;
  border: 1px solid var(--codegen-border);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.04);
}

.command-text {
  margin: 0;
  color: rgb(30, 41, 59);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
}

.summary-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.summary-strip > div {
  min-height: 64px;
  padding: 10px;
  border: 1px solid var(--codegen-border);
  border-radius: 8px;
  background: rgba(20, 184, 166, 0.06);
}

.summary-value {
  display: block;
  font-size: 20px;
  font-weight: 650;
  line-height: 1.2;
}

.summary-label {
  display: block;
  margin-top: 4px;
  color: rgb(100, 116, 139);
  font-size: 12px;
}

.model-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--codegen-border);
}

.field-panel {
  min-height: 130px;
  padding: 12px;
  border: 1px solid var(--codegen-border);
  border-radius: 8px;
}

.field-list-panel {
  min-height: 0;
}

.field-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.field-title {
  margin-bottom: 10px;
  color: rgb(71, 85, 105);
  font-size: 13px;
  font-weight: 600;
}

.preview-search {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  padding: 10px;
  border: 1px solid var(--codegen-border);
  border-radius: 8px;
}

@media (max-width: 640px) {
  .summary-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
