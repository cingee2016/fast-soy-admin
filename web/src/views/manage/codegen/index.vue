<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import type { DataTableColumns, SelectOption } from 'naive-ui';

type FieldType = 'text' | 'number' | 'enum' | 'relation' | 'date' | 'boolean';

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

type SavedModelConfigMap = Record<string, ModelConfig>;

const CODEGEN_CONFIG_STORAGE_KEY = 'fast-soy-admin:codegen:model-config:v1';
const moduleName = ref('hr');
const moduleCn = ref('HR管理');
const commandKind = ref<'crud' | 'gen' | 'gen-web'>('crud');
const buttonAuth = ref(true);
const activeModelName = ref('Employee');
const currentStep = ref(1);
const savedConfigTick = ref(0);
const modelBaselineByTable = new Map<string, string>();
const modelBaselineByName = new Map<string, string>();

const commandKindOptions = [
  { label: '前后端 CRUD', value: 'crud' },
  { label: '仅后端', value: 'gen' },
  { label: '仅前端', value: 'gen-web' }
];

const fieldTypeOptions: { label: string; value: FieldType }[] = [
  { label: '文本', value: 'text' },
  { label: '数字', value: 'number' },
  { label: '枚举', value: 'enum' },
  { label: '关系', value: 'relation' },
  { label: '日期', value: 'date' },
  { label: '布尔', value: 'boolean' }
];

const guideSteps = [
  { title: '选择起点', description: '示例或 Model' },
  { title: '确认配置', description: '模块与字段' },
  { title: '预览页面', description: '搜索与表格' },
  { title: '复制命令', description: '执行与撤销' }
];

const guideTips = [
  '先载入 HR 示例，或粘贴 models.py 中的 Model 代码。',
  '确认模块名、生成范围、字段、搜索条件和数据权限。',
  '检查生成后的 CRUD 搜索区和列表列是否符合预期。',
  '复制命令到终端执行；需要回退时先复制撤销命令。'
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
    listFields: ['name', 'employee_no', 'position', 'department_id', 'hire_date', 'status'],
    searchFields: ['name', 'department_id', 'status', 'hire_date'],
    listOrder: ['-created_at', 'id'],
    fields: [
      { name: 'name', label: '员工姓名', type: 'text' },
      { name: 'employee_no', label: '工号', type: 'text' },
      { name: 'email', label: '邮箱', type: 'text' },
      { name: 'phone', label: '电话', type: 'text' },
      { name: 'position', label: '职位', type: 'text' },
      { name: 'hire_date', label: '入职日期', type: 'date' },
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
      { name: 'category', label: '标签分类', type: 'enum', note: '字典 tag_category' },
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

function tableConfigKey(table: string) {
  return table.trim();
}

function serializeModelConfig(model: ModelConfig) {
  return JSON.stringify(cloneModel(model));
}

function readSavedModelConfigs(): SavedModelConfigMap {
  try {
    const raw = window.localStorage.getItem(CODEGEN_CONFIG_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function writeSavedModelConfigs(configs: SavedModelConfigMap) {
  if (Object.keys(configs).length) {
    window.localStorage.setItem(CODEGEN_CONFIG_STORAGE_KEY, JSON.stringify(configs));
  } else {
    window.localStorage.removeItem(CODEGEN_CONFIG_STORAGE_KEY);
  }
  savedConfigTick.value += 1;
}

function rememberModelBaseline(model: ModelConfig) {
  const serialized = serializeModelConfig(model);
  const tableKey = tableConfigKey(model.table);
  if (tableKey) {
    modelBaselineByTable.set(tableKey, serialized);
  }
  modelBaselineByName.set(model.name, serialized);
}

function findModelBaseline(model: ModelConfig) {
  const tableKey = tableConfigKey(model.table);
  return (tableKey ? modelBaselineByTable.get(tableKey) : undefined) ?? modelBaselineByName.get(model.name);
}

function mergeSavedModelConfig(base: ModelConfig, saved: ModelConfig) {
  const savedFields = new Map(saved.fields.map(field => [field.name, field]));
  const baseFieldNames = new Set(base.fields.map(field => field.name));
  const fields = [
    ...base.fields.map(field => ({ ...field, ...savedFields.get(field.name) })),
    ...saved.fields.filter(field => !baseFieldNames.has(field.name)).map(field => ({ ...field }))
  ];

  const merged: ModelConfig = {
    ...base,
    name: saved.name || base.name,
    title: saved.title || base.title,
    table: saved.table || base.table,
    route: saved.route || base.route,
    selected: saved.selected,
    tree: saved.tree,
    softDelete: saved.softDelete,
    dataScopeEnabled: saved.dataScopeEnabled,
    userField: saved.userField,
    scopeField: saved.scopeField,
    contains: [...saved.contains],
    exact: [...saved.exact],
    listFields: [...saved.listFields],
    searchFields: [...saved.searchFields],
    listOrder: [...saved.listOrder],
    fields
  };

  pruneFieldSelections(merged);
  return merged;
}

function hydrateModels(sourceModels: ModelConfig[]) {
  const savedConfigs = readSavedModelConfigs();

  return sourceModels.map(model => {
    const baseline = cloneModel(model);
    const tableKey = tableConfigKey(baseline.table);
    rememberModelBaseline(baseline);

    return tableKey && savedConfigs[tableKey] ? mergeSavedModelConfig(baseline, savedConfigs[tableKey]) : baseline;
  });
}

const models = reactive<ModelConfig[]>(hydrateModels(hrModelDefaults));
const fieldDraft = reactive<FieldConfig>({ name: '', label: '', type: 'text', note: '' });
const modelSource = ref('');
const previewTextValues = reactive<Record<string, string | null>>({});
const previewNumberValues = reactive<Record<string, number | null>>({});
const previewDateValues = reactive<Record<string, [number, number] | null>>({});
const previewSelectValues = reactive<Record<string, string | number | null>>({});

const modelSourcePlaceholder = `class Employee(BaseModel, AuditMixin, SoftDeleteMixin):
    """员工"""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=50, description="员工姓名")
    employee_no = fields.CharField(max_length=20, unique=True, description="工号")
    status = fields.CharEnumField(enum_type=EmployeeStatus, description="员工状态")
    user_id: int | None
    user = fields.ForeignKeyField("app_system.User", null=True, description="关联系统用户")
    department_id: int
    department = fields.ForeignKeyField("app_system.Department", description="所属部门")

    class Meta:
        table = "biz_employee"`;

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
      hire_date: '2024-03-12',
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
      hire_date: '2025-07-01',
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

const activeModelConfigChanged = computed(() => {
  return savedConfigTick.value >= 0 && Boolean(activeModel.value && isModelConfigChanged(activeModel.value));
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

const previewModelOptions = computed(() => {
  const source = selectedModels.value.length ? selectedModels.value : models;

  return source.map(model => ({
    label: `${model.title} (${model.name})`,
    value: model.name
  }));
});

const previewSearchControls = computed(() => {
  return activeModel.value.searchFields
    .map(fieldName => activeModel.value.fields.find(field => field.name === fieldName))
    .filter((field): field is FieldConfig => Boolean(field))
    .map(field => ({
      field,
      key: `${activeModel.value.name}:${field.name}`,
      options: previewSelectOptions(field)
    }));
});

const selectedFieldSummary = computed(() => {
  const totalFields = selectedModels.value.reduce((total, model) => total + model.fields.length, 0);
  const searchFields = selectedModels.value.reduce((total, model) => total + model.searchFields.length, 0);
  const scoped = selectedModels.value.filter(model => model.dataScopeEnabled).length;
  return { totalFields, searchFields, scoped };
});

const currentStepTip = computed(() => guideTips[currentStep.value - 1] ?? guideTips[0]);

function goStep(step: number) {
  currentStep.value = Math.min(Math.max(step, 1), guideSteps.length);
}

function nextStep() {
  goStep(currentStep.value + 1);
}

function prevStep() {
  goStep(currentStep.value - 1);
}

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

function previewSelectOptions(field: FieldConfig): SelectOption[] {
  if (field.type === 'boolean') {
    return [
      { label: '是', value: 'true' },
      { label: '否', value: 'false' }
    ];
  }

  if (field.type === 'relation') {
    if (field.name.includes('department') || field.name.includes('dept')) {
      return [
        { label: '技术部', value: 'tech' },
        { label: '人事部', value: 'personnel' },
        { label: '财务部', value: 'finance' }
      ];
    }
    if (field.name.includes('user') || field.name.includes('manager') || field.name.includes('owner')) {
      return [
        { label: '周航', value: 'zhouhang' },
        { label: '李沐', value: 'limu' },
        { label: '韩梅', value: 'hanmei' }
      ];
    }
    return [
      { label: '示例对象 A', value: 'sample-a' },
      { label: '示例对象 B', value: 'sample-b' }
    ];
  }

  if (field.type === 'enum') {
    const hint = `${field.name} ${field.note ?? ''}`.toLowerCase();
    if (hint.includes('status')) {
      return [
        { label: '启用', value: 'enabled' },
        { label: '停用', value: 'disabled' },
        { label: '在职', value: 'active' },
        { label: '入职中', value: 'onboarding' }
      ];
    }
    if (hint.includes('category')) {
      return [
        { label: '工作方式', value: 'work-style' },
        { label: '团队角色', value: 'team-role' }
      ];
    }
    return [
      { label: `${field.label}一`, value: 'option-a' },
      { label: `${field.label}二`, value: 'option-b' }
    ];
  }

  return [];
}

function resetPreviewSearch() {
  previewSearchControls.value.forEach(control => {
    if (control.field.type === 'text') {
      previewTextValues[control.key] = null;
    } else if (control.field.type === 'number') {
      previewNumberValues[control.key] = null;
    } else if (control.field.type === 'date') {
      previewDateValues[control.key] = null;
    } else {
      previewSelectValues[control.key] = null;
    }
  });
}

function isModelConfigChanged(model: ModelConfig) {
  const baseline = findModelBaseline(model);
  return !baseline || baseline !== serializeModelConfig(model);
}

function persistChangedModelConfigs() {
  const savedConfigs = readSavedModelConfigs();
  let changed = false;

  for (const model of models) {
    const tableKey = tableConfigKey(model.table);
    if (!tableKey) continue;

    const serialized = serializeModelConfig(model);
    const baseline = findModelBaseline(model);

    if (baseline && baseline === serialized) {
      if (savedConfigs[tableKey]) {
        Reflect.deleteProperty(savedConfigs, tableKey);
        changed = true;
      }
      continue;
    }

    if (JSON.stringify(savedConfigs[tableKey] ?? null) !== serialized) {
      savedConfigs[tableKey] = cloneModel(model);
      changed = true;
    }
  }

  if (changed) {
    writeSavedModelConfigs(savedConfigs);
  }
}

function removeSavedConfigsByTable(tables: string[]) {
  const savedConfigs = readSavedModelConfigs();
  let changed = false;

  for (const table of tables) {
    const tableKey = tableConfigKey(table);
    if (tableKey && savedConfigs[tableKey]) {
      Reflect.deleteProperty(savedConfigs, tableKey);
      changed = true;
    }
  }

  if (changed) {
    writeSavedModelConfigs(savedConfigs);
  }
}

function replaceModelConfig(index: number, model: ModelConfig) {
  models.splice(index, 1, cloneModel(model));
  activeModelName.value = model.name;
}

function resetActiveModelConfig() {
  const index = models.findIndex(model => model === activeModel.value);
  const model = activeModel.value;
  const baseline = findModelBaseline(model);

  if (index < 0 || !baseline) {
    window.$message?.warning('当前模型没有可重置的初始配置');
    return;
  }

  const baselineModel = JSON.parse(baseline) as ModelConfig;
  removeSavedConfigsByTable([model.table, baselineModel.table]);
  replaceModelConfig(index, baselineModel);
  resetPreviewSearch();
  window.$message?.success(`已重置 ${baselineModel.table} 的配置`);
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
  replaceModels(hrModelDefaults, 'Employee');
  goStep(2);
  window.$message?.success('已载入 HR 管理示例');
}

function replaceModels(sourceModels: ModelConfig[], activeName?: string) {
  const hydrated = hydrateModels(sourceModels);
  models.splice(0, models.length, ...hydrated);
  activeModelName.value = hydrated.find(model => model.name === activeName)?.name ?? hydrated[0]?.name ?? '';
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
  const hydrated = hydrateModels([model])[0];
  models.push(hydrated);
  activeModelName.value = hydrated.name;
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

function firstDocLine(value: string) {
  return value
    .split(/\r?\n/)
    .map(line => line.trim())
    .find(Boolean);
}

function extractStringValue(source: string, key: string) {
  const match = source.match(new RegExp(`${key}\\s*=\\s*["']([^"']+)["']`));
  return match?.[1] ?? '';
}

function extractEnumNote(fieldType: string, args: string) {
  if (!['CharEnumField', 'IntEnumField'].includes(fieldType)) return undefined;
  const keyword = args.match(/enum_type\s*=\s*([A-Za-z_][A-Za-z0-9_.]*)/);
  if (keyword) return keyword[1].split('.').pop();
  const positional = args.match(/^\s*([A-Za-z_][A-Za-z0-9_.]*)/);
  return positional?.[1]?.split('.').pop();
}

function fieldTypeFromTortoise(fieldType: string): FieldType {
  if (fieldType.includes('EnumField')) return 'enum';
  if (['ForeignKeyField', 'OneToOneField'].includes(fieldType)) return 'relation';
  if (fieldType === 'BooleanField') return 'boolean';
  if (/DateField|DatetimeField|TimeField/.test(fieldType)) return 'date';
  if (/IntField|BigIntField|SmallIntField|DecimalField|FloatField/.test(fieldType)) return 'number';
  return 'text';
}

function collectFieldStatements(body: string) {
  const statements: string[] = [];
  let current = '';
  let balance = 0;

  for (const line of body.split(/\r?\n/)) {
    if (!current && !line.includes('= fields.')) continue;

    current = current ? `${current}\n${line}` : line;
    balance += (line.match(/\(/g) || []).length;
    balance -= (line.match(/\)/g) || []).length;

    if (current && balance <= 0) {
      statements.push(current);
      current = '';
      balance = 0;
    }
  }

  return statements;
}

function uniqueFields(fields: FieldConfig[]) {
  const seen = new Set<string>();
  return fields.filter(field => {
    if (field.name === 'id' || seen.has(field.name)) return false;
    seen.add(field.name);
    return true;
  });
}

function parseFieldsFromBody(body: string) {
  const fields: FieldConfig[] = [];
  const relationIds = new Set<string>();

  for (const line of body.split(/\r?\n/)) {
    const typedId = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*_id)\s*:\s*(?:int|int\s*\|)/);
    if (typedId) {
      relationIds.add(typedId[1]);
    }
  }

  for (const statement of collectFieldStatements(body)) {
    const fieldMatch = statement.match(
      /^\s*(?:(?:[A-Za-z_][A-Za-z0-9_]*)\s*:\s*[^=]+=\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*fields\.([A-Za-z]+Field)\(([\s\S]*)\)\s*$/
    );
    if (!fieldMatch) continue;

    const [, rawName, fieldType, args] = fieldMatch;
    const type = fieldTypeFromTortoise(fieldType);
    const name = type === 'relation' && !rawName.endsWith('_id') ? `${rawName}_id` : rawName;
    relationIds.delete(name);

    fields.push({
      name,
      label: extractStringValue(args, 'description') || name,
      type,
      note: extractEnumNote(fieldType, args)
    });
  }

  relationIds.forEach(name => fields.push({ name, label: name, type: 'relation' }));
  return uniqueFields(fields);
}

function buildModelFromSource(name: string, bases: string, body: string): ModelConfig {
  const doc = body.match(/^\s*(?:"""|''')([\s\S]*?)(?:"""|''')/m);
  const fields = parseFieldsFromBody(body);
  const textFields = fields.filter(field => field.type === 'text').map(field => field.name);
  const dateFields = fields.filter(field => field.type === 'date').map(field => field.name);
  const exactFields = fields
    .filter(
      field =>
        field.type !== 'text' ||
        field.name.endsWith('_id') ||
        ['status', 'category', 'type'].some(token => field.name.includes(token))
    )
    .map(field => field.name);
  const scopeOptions = fields.filter(
    field => field.type === 'relation' || field.type === 'number' || field.name.endsWith('_id')
  );
  const userField = scopeOptions.find(field => ['user_id', 'owner_id'].includes(field.name))?.name || 'created_by';
  const scopeField =
    scopeOptions.find(field =>
      ['department_id', 'tenant_id', 'project_id', 'store_id', 'scope_id'].includes(field.name)
    )?.name || 'id';
  const title = firstDocLine(doc?.[1] ?? '') || extractStringValue(body, 'table_description') || name;

  return {
    name,
    title,
    table: extractStringValue(body, 'table') || `biz_${moduleName.value}_${toSnake(name)}`,
    route: `/${moduleName.value}/${toKebab(name)}`,
    selected: true,
    tree: bases.includes('TreeMixin'),
    softDelete: bases.includes('SoftDeleteMixin'),
    dataScopeEnabled: scopeOptions.some(field =>
      ['user_id', 'owner_id', 'department_id', 'tenant_id', 'scope_id'].includes(field.name)
    ),
    userField,
    scopeField,
    contains: textFields,
    exact: exactFields,
    listFields: fields.slice(0, 6).map(field => field.name),
    searchFields: [...textFields.slice(0, 2), ...exactFields.slice(0, 3), ...dateFields.slice(0, 1)].filter(
      (field, index, array) => array.indexOf(field) === index
    ),
    listOrder: ['id'],
    fields
  };
}

function parseModelsFromSource(source: string) {
  const classMatches = [...source.matchAll(/^class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\):/gm)];
  const parsed: ModelConfig[] = [];

  classMatches.forEach((match, index) => {
    const bases = match[2];
    if (!bases.includes('BaseModel')) return;

    const bodyStart = (match.index ?? 0) + match[0].length;
    const bodyEnd = classMatches[index + 1]?.index ?? source.length;
    const body = source.slice(bodyStart, bodyEnd);
    const model = buildModelFromSource(match[1], bases, body);
    if (model.fields.length) {
      parsed.push(model);
    }
  });

  return parsed;
}

function parseModelSource() {
  const parsed = parseModelsFromSource(modelSource.value);
  if (!parsed.length) {
    window.$message?.warning('没有识别到继承 BaseModel 且包含字段的 Model');
    return;
  }

  replaceModels(parsed, parsed[0].name);
  goStep(2);
  window.$message?.success(`已解析 ${parsed.length} 个 Model`);
}

watch(models, persistChangedModelConfigs, { deep: true });
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

    <NCard :bordered="false" size="small" class="card-wrapper guide-card">
      <NSpace vertical :size="12">
        <NSteps :current="currentStep" size="small">
          <NStep
            v-for="(step, index) in guideSteps"
            :key="step.title"
            :title="step.title"
            :description="step.description"
            @click="goStep(index + 1)"
          />
        </NSteps>
        <div class="guide-footer">
          <NAlert type="info" :show-icon="false" class="guide-tip">{{ currentStepTip }}</NAlert>
          <NSpace>
            <NButton secondary :disabled="currentStep === 1" @click="prevStep">上一步</NButton>
            <NButton v-if="currentStep < guideSteps.length" type="primary" @click="nextStep">下一步</NButton>
            <NButton v-else type="primary" @click="copyText(command, '生成命令')">
              <template #icon><icon-ic-round-content-copy class="text-icon" /></template>
              复制命令
            </NButton>
          </NSpace>
        </div>
      </NSpace>
    </NCard>

    <NGrid v-show="currentStep === 1" responsive="screen" item-responsive :x-gap="16" :y-gap="16">
      <NGridItem span="24 l:8">
        <NCard :bordered="false" size="small" class="quick-start-card h-full">
          <NSpace vertical :size="14">
            <div>
              <NTag type="info" size="small">推荐起点</NTag>
              <h3 class="m-0 mt-10px text-18px font-semibold">HR 管理示例</h3>
              <p class="m-0 mt-6px text-13px text-gray-500">部门管理、员工管理、标签管理，已配置搜索字段和数据范围。</p>
            </div>
            <NButton type="primary" size="large" block @click="loadHrExample">
              <template #icon><icon-ic-round-workspaces class="text-icon" /></template>
              载入 HR 管理示例
            </NButton>
          </NSpace>
        </NCard>
      </NGridItem>
      <NGridItem span="24 l:16">
        <NCard title="粘贴 Model" :bordered="false" size="small" class="card-wrapper h-full">
          <NSpace vertical :size="12">
            <NInput
              v-model:value="modelSource"
              type="textarea"
              :autosize="{ minRows: 7, maxRows: 12 }"
              :placeholder="modelSourcePlaceholder"
            />
            <NSpace>
              <NButton type="primary" @click="parseModelSource">
                <template #icon><icon-ic-round-plus class="text-icon" /></template>
                解析并替换配置
              </NButton>
              <NButton secondary @click="modelSource = ''">清空</NButton>
            </NSpace>
          </NSpace>
        </NCard>
      </NGridItem>
    </NGrid>

    <NGrid v-show="currentStep === 2 || currentStep === 4" responsive="screen" item-responsive :x-gap="16" :y-gap="16">
      <NGridItem :span="currentStep === 4 ? '24 l:9' : '24'">
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

      <NGridItem v-if="currentStep === 4" span="24 l:15">
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

    <NCard v-show="currentStep === 2" title="模型与字段配置" :bordered="false" size="small" class="card-wrapper">
      <template #header-extra>
        <NSpace>
          <NText v-if="activeModelConfigChanged" :depth="3" class="hidden text-12px sm:inline">
            已按 {{ activeModel.table }} 保存
          </NText>
          <NButton size="small" secondary :disabled="!activeModelConfigChanged" @click="resetActiveModelConfig">
            <template #icon><icon-ic-round-refresh class="text-icon" /></template>
            重置配置
          </NButton>
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

    <NCard
      v-show="currentStep === 3"
      title="CRUD 页面预览"
      :bordered="false"
      size="small"
      class="card-wrapper preview-card"
    >
      <template #header-extra>
        <NTag type="info">{{ activeModel.name }}</NTag>
      </template>
      <NSpace vertical :size="12">
        <div class="preview-toolbar">
          <div>
            <div class="preview-title">{{ activeModel.title }}</div>
            <div class="preview-subtitle">{{ activeModel.route }} · {{ activeModel.table }}</div>
          </div>
          <NSelect
            v-model:value="activeModelName"
            :options="previewModelOptions"
            size="small"
            class="preview-model-select"
            placeholder="选择预览模型"
          />
        </div>
        <NForm label-placement="top" size="small" class="preview-search">
          <NGrid responsive="screen" item-responsive :x-gap="12" :y-gap="8">
            <NFormItemGi
              v-for="control in previewSearchControls"
              :key="control.key"
              span="24 m:12 l:6"
              :label="control.field.label"
            >
              <NInput
                v-if="control.field.type === 'text'"
                v-model:value="previewTextValues[control.key]"
                clearable
                :placeholder="`请输入${control.field.label}`"
              />
              <NInputNumber
                v-else-if="control.field.type === 'number'"
                v-model:value="previewNumberValues[control.key]"
                clearable
                class="w-full"
                :placeholder="`请输入${control.field.label}`"
              />
              <NDatePicker
                v-else-if="control.field.type === 'date'"
                v-model:value="previewDateValues[control.key]"
                clearable
                type="daterange"
                class="w-full"
              />
              <NSelect
                v-else
                v-model:value="previewSelectValues[control.key]"
                clearable
                filterable
                :options="control.options"
                :placeholder="`请选择${control.field.label}`"
              />
            </NFormItemGi>
            <NFormItemGi span="24 m:12 l:6" label=" ">
              <NSpace class="preview-actions">
                <NButton size="small" secondary @click="resetPreviewSearch">
                  <template #icon><icon-ic-round-refresh class="text-icon" /></template>
                  重置
                </NButton>
                <NButton size="small" type="primary" ghost>
                  <template #icon><icon-ic-round-search class="text-icon" /></template>
                  搜索
                </NButton>
              </NSpace>
            </NFormItemGi>
          </NGrid>
        </NForm>
        <div class="preview-table">
          <NDataTable
            :columns="previewColumns"
            :data="previewData"
            size="small"
            :scroll-x="900"
            :pagination="{ pageSize: 5 }"
          />
        </div>
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

.guide-card :deep(.n-step) {
  cursor: pointer;
}

.guide-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.guide-tip {
  flex: 1;
  min-width: 0;
}

.quick-start-card {
  border: 1px solid rgba(99, 102, 241, 0.22);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.09), rgba(20, 184, 166, 0.06)), rgba(248, 250, 252, 0.86);
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

.preview-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.preview-title {
  font-size: 15px;
  font-weight: 650;
  line-height: 1.35;
}

.preview-subtitle {
  margin-top: 2px;
  color: rgb(100, 116, 139);
  font-size: 12px;
}

.preview-model-select {
  width: 240px;
}

.preview-card {
  flex: none;
}

.preview-card :deep(.n-card__content) {
  overflow: visible;
}

.preview-search {
  min-height: 44px;
  padding: 10px;
  border: 1px solid var(--codegen-border);
  border-radius: 8px;
  background: rgba(248, 250, 252, 0.72);
}

.preview-actions {
  width: 100%;
  min-height: 34px;
  align-items: center;
}

.preview-table {
  overflow-x: auto;
  overflow-y: visible;
  padding-bottom: 2px;
}

@media (max-width: 640px) {
  .guide-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .summary-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .preview-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .preview-model-select {
    width: 100%;
  }
}
</style>
