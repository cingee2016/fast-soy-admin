"""前端代码生成器 — service / typings / views / i18n。"""

from __future__ import annotations

import re
from pathlib import Path

from app.cli.parser import FieldInfo, ModelInfo, RelationInfo

# ─── 命名转换 ───


def snake_to_camel(s: str) -> str:
    """snake_case → camelCase"""
    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def snake_to_pascal(s: str) -> str:
    """snake_case → PascalCase"""
    return "".join(p.title() for p in s.split("_"))


def route_segment(name: str) -> str:
    """snake_case → kebab-case route/path segment."""
    return name.replace("_", "-")


def module_route_key(module: str) -> str:
    """Return the Elegant Router key for a generated module root."""
    return route_segment(module)


def model_route_key(module: str, model: ModelInfo) -> str:
    """Return the Elegant Router key for a generated CRUD view."""
    return f"{module_route_key(module)}_{route_segment(model.snake_name)}"


def camel_to_kebab(s: str) -> str:
    """camelCase → kebab-case."""
    return re.sub(r"(?<!^)(?=[A-Z])", "-", s).lower()


def relation_id_name(r: RelationInfo) -> str:
    return f"{r.name}_id"


def relation_camel_name(r: RelationInfo) -> str:
    return f"{snake_to_camel(r.name)}Id"


def relation_label_key(r: RelationInfo) -> str:
    return snake_to_camel(r.name)


def option_prop_name(name: str) -> str:
    return f"{snake_to_camel(name)}Options"


def find_fk_relation(model: ModelInfo, name: str) -> RelationInfo | None:
    for relation in model.relations:
        if relation.relation_type not in ("ForeignKeyField", "OneToOneField"):
            continue
        if name in {relation.name, relation_id_name(relation)}:
            return relation
    return None


def _button_code(module: str, model: ModelInfo, action: str) -> str:
    module_part = module.replace("-", "_").upper()
    model_part = model.snake_name.upper()
    return f"B_{module_part}_{model_part}_{action}"


def cn_title(description: str, fallback: str) -> str:
    """从 description 中提取中文标题：截断到第一个句号前。"""
    if not description:
        return fallback
    text = description
    for sep in ("。", "."):
        if sep in text:
            text = text.split(sep)[0]
    return text.strip() or fallback


def en_title(field_name: str) -> str:
    """英文标题：snake_case → camelCase"""
    return snake_to_camel(field_name)


# ─── 字段 → TS 类型 / 表单组件 映射 ───


def field_ts_type(f: FieldInfo) -> str:
    """返回 TS 类型字符串。"""
    mapping = {
        "CharField": "string",
        "TextField": "string",
        "UUIDField": "string",
        "IntField": "number",
        "BigIntField": "number",
        "SmallIntField": "number",
        "BooleanField": "boolean",
        "DecimalField": "number",
        "FloatField": "number",
        "DatetimeField": "string",
        "DateField": "string",
        "TimeField": "string",
        "JSONField": "Record<string, any>",
        "CharEnumField": "string",
        "IntEnumField": "number",
    }
    return mapping.get(f.field_type, "string")


def field_form_component(f: FieldInfo) -> str:
    """返回表单组件类型标识: input / textarea / int / decimal / switch / date / datetime / select-status / select-todo。"""
    if f.field_type == "TextField":
        return "textarea"
    if f.field_type in ("CharField",):
        return "input"
    if f.field_type in ("IntField", "BigIntField", "SmallIntField"):
        return "int"
    if f.field_type in ("DecimalField", "FloatField"):
        return "decimal"
    if f.field_type == "BooleanField":
        return "switch"
    if f.field_type == "DateField":
        return "date"
    if f.field_type == "TimeField":
        return "time"
    if f.field_type == "DatetimeField":
        return "datetime"
    if f.field_type == "CharEnumField" and f.enum_type == "StatusType":
        return "select-status"
    if f.field_type in ("CharEnumField", "IntEnumField"):
        return "select-todo"
    return "input"


# ─── 生成 service ts ───


def gen_service_ts(module: str, models: list[ModelInfo]) -> str:
    ns = snake_to_pascal(module) + "Manage"
    lines = [
        "import { request } from '../request';",
        "",
    ]
    for model in models:
        entity = model.name  # PascalCase
        entity_snake = model.snake_name
        entity_plural = model.plural_snake
        url_base = f"/business/{module}/{entity_plural}"

        lines.extend([
            f"// ---- {entity} ----",
            f"export function fetchGet{entity}List(data?: Api.{ns}.{entity}SearchParams) {{",
            f"  return request<Api.{ns}.{entity}List>({{",
            f"    url: '{url_base}/search',",
            "    method: 'post',",
            "    data: data ?? {}",
            "  });",
            "}",
            "",
            f"export function fetchGet{entity}(id: string) {{",
            f"  return request<Api.{ns}.{entity}>({{",
            f"    url: `{url_base}/${{id}}`,",
            "    method: 'get'",
            "  });",
            "}",
            "",
            f"export function fetchAdd{entity}(data?: Api.{ns}.{entity}AddParams) {{",
            "  return request<null, 'json'>({",
            f"    url: '{url_base}',",
            "    method: 'post',",
            "    data",
            "  });",
            "}",
            "",
            f"export function fetchUpdate{entity}(data?: Api.{ns}.{entity}UpdateParams) {{",
            "  return request<null, 'json'>({",
            f"    url: `{url_base}/${{data?.id}}`,",
            "    method: 'patch',",
            "    data",
            "  });",
            "}",
            "",
            f"export function fetchDelete{entity}(data?: Api.{ns}.CommonDeleteParams) {{",
            "  return request<null>({",
            f"    url: `{url_base}/${{data?.id}}`,",
            "    method: 'delete'",
            "  });",
            "}",
            "",
            f"export function fetchBatchDelete{entity}(data?: Api.{ns}.CommonBatchDeleteParams) {{",
            "  return request<null>({",
            f"    url: '{url_base}',",
            "    method: 'delete',",
            "    data",
            "  });",
            "}",
            "",
            "",
            f"void {entity_snake};",  # placeholder to avoid unused var warning; removed below
        ])

    # 移除占位符
    lines = [line for line in lines if not line.startswith("void ")]
    return "\n".join(lines) + "\n"


# ─── 生成 typings d.ts ───


def _ts_field_line(name: str, ts_type: str, optional: bool = False, nullable: bool = False) -> str:
    """生成单行 TS 字段声明。"""
    opt = "?" if optional else ""
    nul = " | null" if nullable else ""
    return f"      {name}{opt}: {ts_type}{nul};"


def gen_typings_dts(module: str, models: list[ModelInfo], search_fields_map: dict[str, list[str]]) -> str:
    ns = snake_to_pascal(module) + "Manage"
    lines = [
        "declare namespace Api {",
        f"  namespace {ns} {{",
        "    type CommonDeleteParams = { id: string };",
        "    type CommonBatchDeleteParams = { ids: string[] };",
        "    type CommonSearchParams = Pick<Common.PaginatingCommonParams, 'current' | 'size'>;",
        "",
    ]

    for model in models:
        entity = model.name
        fields = model.schema_fields
        fk_relations = [r for r in model.relations if r.relation_type in ("ForeignKeyField", "OneToOneField")]

        lines.append(f"    // ---- {entity} ----")

        # ---- Entity ----
        lines.append(f"    type {entity} = Common.CommonRecord<{{")
        for f in fields:
            camel = snake_to_camel(f.name)
            lines.append(_ts_field_line(camel, field_ts_type(f), optional=False, nullable=not f.required))
        for r in fk_relations:
            camel = relation_camel_name(r)
            lines.append(_ts_field_line(camel, "string", optional=False, nullable=r.nullable))
        lines.append("    }>;")
        lines.append("")

        # ---- AddParams ----
        lines.append(f"    type {entity}AddParams = {{")
        for f in fields:
            camel = snake_to_camel(f.name)
            lines.append(_ts_field_line(camel, field_ts_type(f), optional=not f.required, nullable=not f.required))
        for r in fk_relations:
            camel = relation_camel_name(r)
            lines.append(_ts_field_line(camel, "string", optional=r.nullable, nullable=r.nullable))
        lines.append("    };")
        lines.append("")

        # ---- UpdateParams ----
        lines.append(f"    type {entity}UpdateParams = {{ id?: string }} & Partial<{entity}AddParams>;")
        lines.append("")

        # ---- SearchParams ----
        search_names = search_fields_map.get(model.name, [])
        # 搜索参数始终加上 status (如果有)
        has_status_enum = any(f.name == "status" and f.enum_type for f in fields)

        lines.append(f"    type {entity}SearchParams = CommonType.RecordNullable<")
        lines.append("      {")
        for name in search_names:
            f = next((x for x in fields if x.name == name), None)
            if f:
                camel = snake_to_camel(name)
                lines.append(f"        {camel}?: {field_ts_type(f)};")
                continue
            r = find_fk_relation(model, name)
            if r:
                lines.append(f"        {relation_camel_name(r)}?: string;")
        if has_status_enum and "status" not in search_names:
            lines.append("        status?: string;")
        lines.append("      } & CommonSearchParams")
        lines.append("    >;")
        lines.append("")

        # ---- List ----
        lines.append(f"    type {entity}List = Common.PaginatingQueryRecord<{entity}>;")
        lines.append("")

    lines.extend([
        "  }",
        "}",
        "",
    ])
    return "\n".join(lines)


# ─── 生成 Vue views ───


def _form_item_block(
    f: FieldInfo | RelationInfo,
    i18n_page: str,
    *,
    is_relation: bool = False,
    option_expr: str | None = None,
) -> list[str]:
    """为单个字段生成 <NFormItem> 块（用于 operate-drawer）。"""
    if is_relation:
        assert isinstance(f, RelationInfo)
        name_camel = relation_camel_name(f)
        label_key = f"{i18n_page}.{relation_label_key(f)}"
        placeholder_key = f"{i18n_page}.form.{relation_label_key(f)}"
        return [
            f'      <NFormItem :label="$t(\'{label_key}\')" path="{name_camel}">',
            "        <NSelect",
            f'          v-model:value="model.{name_camel}"',
            f'          :options="{option_expr or "[]"}"',
            "          clearable",
            "          filterable",
            f"          :placeholder=\"$t('{placeholder_key}')\"",
            "        />",
            "      </NFormItem>",
        ]

    assert isinstance(f, FieldInfo)
    name_camel = snake_to_camel(f.name)
    label_key = f"{i18n_page}.{name_camel}"
    placeholder_key = f"{i18n_page}.form.{name_camel}"
    component = field_form_component(f)

    base = f'      <NFormItem :label="$t(\'{label_key}\')" path="{name_camel}">'
    end = "      </NFormItem>"

    body: list[str]
    if f.field_type == "JSONField":
        body = [
            "        <NInput",
            f'          :value="formatJsonInput(model.{name_camel})"',
            '          type="textarea"',
            f"          :placeholder=\"$t('{placeholder_key}')\"",
            f'          @update:value="value => (model.{name_camel} = parseJsonInput(value))"',
            "        />",
        ]
    elif component == "input":
        body = [f'        <NInput v-model:value="model.{name_camel}" :placeholder="$t(\'{placeholder_key}\')" />']
    elif component == "textarea":
        body = [f'        <NInput v-model:value="model.{name_camel}" type="textarea" :placeholder="$t(\'{placeholder_key}\')" />']
    elif component == "int":
        body = [f'        <NInputNumber v-model:value="model.{name_camel}" :placeholder="$t(\'{placeholder_key}\')" class="w-full" />']
    elif component == "decimal":
        precision = 2
        body = [f'        <NInputNumber v-model:value="model.{name_camel}" :precision="{precision}" :placeholder="$t(\'{placeholder_key}\')" class="w-full" />']
    elif component == "switch":
        body = [
            "        <NSwitch",
            f'          :value="Boolean(model.{name_camel})"',
            f'          @update:value="value => (model.{name_camel} = value)"',
            "        />",
        ]
    elif component in ("date", "datetime"):
        value_format = "yyyy-MM-dd" if component == "date" else "yyyy-MM-dd HH:mm:ss"
        body = [
            "        <NDatePicker",
            f'          v-model:formatted-value="model.{name_camel}"',
            f'          type="{component}"',
            f'          value-format="{value_format}"',
            "          clearable",
            '          class="w-full"',
            "        />",
        ]
    elif component == "time":
        body = [
            "        <NTimePicker",
            f'          v-model:formatted-value="model.{name_camel}"',
            '          value-format="HH:mm:ss"',
            "          clearable",
            '          class="w-full"',
            "        />",
        ]
    elif component == "select-status":
        body = [
            "        <NSelect",
            f'          v-model:value="model.{name_camel}"',
            '          :options="statusTypeOptions"',
            "          clearable",
            f"          :placeholder=\"$t('{placeholder_key}')\"",
            "        />",
        ]
    elif component == "select-todo":
        body = [
            "        <NSelect",
            f'          v-model:value="model.{name_camel}"',
            f'          :options="{option_expr or "[]"}"',
            "          clearable",
            "          filterable",
            f"          :placeholder=\"$t('{placeholder_key}')\"",
            "        />",
        ]
    else:
        body = [f'        <NInput v-model:value="model.{name_camel}" :placeholder="$t(\'{placeholder_key}\')" />']

    return [base, *body, end]


def _default_value_for_field(f: FieldInfo) -> str:
    """用于 createDefaultModel() 的字段默认值。"""
    if f.field_type in ("DatetimeField", "DateField", "TimeField"):
        return "null"
    if f.field_type in ("CharField", "TextField", "UUIDField"):
        return "''"
    if f.field_type in ("IntField", "BigIntField", "SmallIntField", "DecimalField", "FloatField"):
        return "null"
    if f.field_type == "BooleanField":
        return "false"
    if f.field_type == "CharEnumField":
        return "''"
    return "null"


def gen_view_index(module: str, model: ModelInfo, list_fields: list[str], *, button_auth: bool = False) -> str:
    """生成 views/<module>/<entity>/index.vue"""
    entity = model.name
    entity_snake = model.snake_name
    entity_kebab = entity_snake.replace("_", "-")
    ns = snake_to_pascal(module) + "Manage"
    i18n_page = f"page.{module}.{entity_snake}"

    fields = model.schema_fields
    fk_relations = [r for r in model.relations if r.relation_type in ("ForeignKeyField", "OneToOneField")]
    custom_enum_fields = [f for f in fields if field_form_component(f) == "select-todo"]
    option_props = [option_prop_name(f.name) for f in custom_enum_fields] + [option_prop_name(r.name) for r in fk_relations]
    option_ref_lines = [
        "type SelectOptionItem = { label: string; value: string | number };",
        "",
    ]
    for prop in option_props:
        option_ref_lines.append(f"const {prop} = ref<SelectOptionItem[]>([]);")
    if option_props:
        option_ref_lines.extend([
            "",
            "// TODO: 在这里加载真实 options 数据源，并传给搜索区和抽屉。",
            "",
        ])
    else:
        option_ref_lines = []

    vue_imports = ["reactive"]
    if option_props:
        vue_imports.append("ref")

    # 列定义
    col_lines = [
        "    { type: 'selection', align: 'center', width: 48 },",
        "    { key: 'index', title: $t('common.index'), width: 64, align: 'center', render: (_, index) => index + 1 },",
    ]
    for name in list_fields:
        f = next((x for x in fields if x.name == name), None)
        if not f:
            # 可能是外键
            r = find_fk_relation(model, name)
            if r:
                camel = relation_camel_name(r)
                col_lines.append(f"    {{ key: '{camel}', title: $t('{i18n_page}.{relation_label_key(r)}'), align: 'center', minWidth: 120 }},")
            continue
        camel = snake_to_camel(f.name)
        col_lines.append(f"    {{ key: '{camel}', title: $t('{i18n_page}.{camel}'), align: 'center', minWidth: 120 }},")

    # 搜索参数字段（给 reactive 的默认值）
    search_param_lines = ["  current: 1,", "  size: 10,"]
    # 搜索参数不在这里定义，只定义 list 列；search 字段在 search.vue 里

    search_prop_lines = [f'      :{camel_to_kebab(prop)}="{prop}"' for prop in option_props]
    drawer_prop_lines = [f'        :{camel_to_kebab(prop)}="{prop}"' for prop in option_props]

    search_component = "\n".join([
        f"    <{entity}Search",
        '      v-model:model="searchParams"',
        *search_prop_lines,
        '      @search="getDataByPage"',
        "    />",
    ])
    drawer_component = "\n".join([
        f"      <{entity}OperateDrawer",
        '        v-model:visible="drawerVisible"',
        '        :operate-type="operateType"',
        '        :row-data="editingData"',
        *drawer_prop_lines,
        '        @submitted="getDataByPage"',
        "      />",
    ])

    button_auth_lines: list[str] = []
    if button_auth:
        button_auth_lines = [
            "import { useAuth } from '@/hooks/business/auth';",
        ]

    auth_setup = "const { hasAuth } = useAuth();" if button_auth else ""
    edit_button = (
        f"""{{hasAuth('{_button_code(module, model, "EDIT")}') && (
              <NButton type="primary" ghost size="small" onClick={{() => edit(row.id)}}>
                {{$t('common.edit')}}
              </NButton>
            )}}"""
        if button_auth
        else """<NButton type="primary" ghost size="small" onClick={() => edit(row.id)}>
              {$t('common.edit')}
            </NButton>"""
    )
    delete_button = (
        f"""{{hasAuth('{_button_code(module, model, "DELETE")}') && (
              <NPopconfirm onPositiveClick={{() => handleDelete(row.id)}}>
                {{{{
                  default: () => $t('common.confirmDelete'),
                  trigger: () => (
                    <NButton type="error" ghost size="small">
                      {{$t('common.delete')}}
                    </NButton>
                  )
                }}}}
              </NPopconfirm>
            )}}"""
        if button_auth
        else """<NPopconfirm onPositiveClick={() => handleDelete(row.id)}>
              {{
                default: () => $t('common.confirmDelete'),
                trigger: () => (
                  <NButton type="error" ghost size="small">
                    {$t('common.delete')}
                  </NButton>
                )
              }}
            </NPopconfirm>"""
    )
    if button_auth:
        header_operation = f"""        <TableHeaderOperation v-model:columns="columnChecks" :loading="loading" @refresh="getData">
          <NButton v-if="hasAuth('{_button_code(module, model, "CREATE")}')" size="small" ghost type="primary" @click="handleAdd">
            <template #icon><icon-ic-round-plus class="text-icon" /></template>
            {{{{ $t('common.add') }}}}
          </NButton>
          <NPopconfirm v-if="hasAuth('{_button_code(module, model, "DELETE")}')" @positive-click="handleBatchDelete">
            <template #trigger>
              <NButton size="small" ghost type="error" :disabled="checkedRowKeys.length === 0">
                <template #icon><icon-ic-round-delete class="text-icon" /></template>
                {{{{ $t('common.batchDelete') }}}}
              </NButton>
            </template>
            {{{{ $t('common.confirmDelete') }}}}
          </NPopconfirm>
        </TableHeaderOperation>"""
    else:
        header_operation = """        <TableHeaderOperation
          v-model:columns="columnChecks"
          :disabled-delete="checkedRowKeys.length === 0"
          :loading="loading"
          @add="handleAdd"
          @delete="handleBatchDelete"
          @refresh="getData"
        />"""

    template = f"""<script setup lang="tsx">
import {{ {", ".join(vue_imports)} }} from 'vue';
import {{ NButton, NPopconfirm }} from 'naive-ui';
import {{ fetchBatchDelete{entity}, fetchDelete{entity}, fetchGet{entity}List }} from '@/service/api';
import {{ useAppStore }} from '@/store/modules/app';
import {{ defaultTransform, useNaivePaginatedTable, useTableOperate }} from '@/hooks/common/table';
{chr(10).join(button_auth_lines)}
import {{ $t }} from '@/locales';
import {entity}OperateDrawer from './modules/{entity_kebab}-operate-drawer.vue';
import {entity}Search from './modules/{entity_kebab}-search.vue';

const appStore = useAppStore();
{auth_setup}

{chr(10).join(option_ref_lines)}

const searchParams: Api.{ns}.{entity}SearchParams = reactive({{
  current: 1,
  size: 10
}});

const {{ columns, columnChecks, data, loading, getData, getDataByPage, mobilePagination }} = useNaivePaginatedTable({{
  api: () => fetchGet{entity}List(searchParams),
  transform: response => defaultTransform(response),
  onPaginationParamsChange: params => {{
    searchParams.current = params.page;
    searchParams.size = params.pageSize;
  }},
  columns: () => [
{chr(10).join(col_lines)}
    {{
      key: 'operate',
      title: $t('common.operate'),
      align: 'center',
      width: 130,
      render: row => (
        <div class="flex-center gap-8px">
          {edit_button}
          {delete_button}
        </div>
      )
    }}
  ]
}});

const {{ drawerVisible, operateType, editingData, handleAdd, handleEdit, checkedRowKeys, onBatchDeleted, onDeleted }} =
  useTableOperate(data, 'id', getData);

async function handleBatchDelete() {{
  const {{ error }} = await fetchBatchDelete{entity}({{ ids: checkedRowKeys.value as string[] }});
  if (!error) onBatchDeleted();
}}

async function handleDelete(id: string) {{
  const {{ error }} = await fetchDelete{entity}({{ id }});
  if (!error) onDeleted();
}}

function edit(id: string) {{
  handleEdit(id);
}}
</script>

<template>
  <div class="min-h-500px flex-col-stretch gap-16px overflow-hidden lt-sm:overflow-auto">
{search_component}
    <NCard :title="$t('{i18n_page}.pageTitle')" :bordered="false" size="small" class="card-wrapper sm:flex-1-hidden">
      <template #header-extra>
{header_operation}
      </template>
      <NDataTable
        v-model:checked-row-keys="checkedRowKeys"
        :columns="columns"
        :data="data"
        size="small"
        :flex-height="!appStore.isMobile"
        :scroll-x="600"
        :loading="loading"
        remote
        :row-key="row => row.id"
        :pagination="mobilePagination"
        class="sm:h-full"
      />
{drawer_component}
    </NCard>
  </div>
</template>
"""
    # 规避未使用变量
    _ = search_param_lines
    return template


def gen_view_search(module: str, model: ModelInfo, search_field_names: list[str]) -> str:
    """生成 <entity>-search.vue"""
    entity = model.name
    entity_snake = model.snake_name
    entity_kebab = entity_snake.replace("_", "-")
    ns = snake_to_pascal(module) + "Manage"
    i18n_page = f"page.{module}.{entity_snake}"

    fields = model.schema_fields
    option_props: list[str] = []

    # 生成 form items
    form_items: list[str] = []
    for name in search_field_names:
        f = next((x for x in fields if x.name == name), None)
        if not f:
            r = find_fk_relation(model, name)
            if not r:
                continue
            camel = relation_camel_name(r)
            label_key = f"{i18n_page}.{relation_label_key(r)}"
            placeholder_key = f"{i18n_page}.form.{relation_label_key(r)}"
            prop = option_prop_name(r.name)
            if prop not in option_props:
                option_props.append(prop)
            item_start = f'            <NFormItemGi span="24 s:12 m:6" :label="$t(\'{label_key}\')" path="{camel}" class="pr-24px">'
            item_end = "            </NFormItemGi>"
            body = (
                "              <NSelect\n"
                f'                v-model:value="model.{camel}"\n'
                f'                :options="props.{prop}"\n'
                "                clearable\n"
                "                filterable\n"
                f"                :placeholder=\"$t('{placeholder_key}')\"\n"
                "              />"
            )
            form_items.extend([item_start, body, item_end])
            continue

        camel = snake_to_camel(name)
        label_key = f"{i18n_page}.{camel}"
        placeholder_key = f"{i18n_page}.form.{camel}"
        component = field_form_component(f)

        item_start = f'            <NFormItemGi span="24 s:12 m:6" :label="$t(\'{label_key}\')" path="{camel}" class="pr-24px">'
        item_end = "            </NFormItemGi>"

        if component in ("input", "textarea"):
            body = f'              <NInput v-model:value="model.{camel}" :placeholder="$t(\'{placeholder_key}\')" />'
        elif component in ("int", "decimal"):
            body = f'              <NInputNumber v-model:value="model.{camel}" :placeholder="$t(\'{placeholder_key}\')" class="w-full" />'
        elif component == "select-status":
            body = f'              <NSelect v-model:value="model.{camel}" :options="statusTypeOptions" clearable :placeholder="$t(\'{placeholder_key}\')" />'
        elif component == "select-todo":
            prop = option_prop_name(f.name)
            if prop not in option_props:
                option_props.append(prop)
            body = (
                "              <NSelect\n"
                f'                v-model:value="model.{camel}"\n'
                f'                :options="props.{prop}"\n'
                "                clearable\n"
                "                filterable\n"
                f"                :placeholder=\"$t('{placeholder_key}')\"\n"
                "              />"
            )
        elif component == "switch":
            body = (
                "              <NSelect\n"
                f'                :value="model.{camel} as any"\n'
                '                :options="booleanOptions"\n'
                "                clearable\n"
                f"                :placeholder=\"$t('{placeholder_key}')\"\n"
                f'                @update:value="value => (model.{camel} = value as boolean | null)"\n'
                "              />"
            )
        elif component == "date":
            body = f'              <NDatePicker v-model:formatted-value="model.{camel}" type="date" value-format="yyyy-MM-dd" clearable class="w-full" />'
        elif component == "datetime":
            body = f'              <NDatePicker v-model:formatted-value="model.{camel}" type="datetime" value-format="yyyy-MM-dd HH:mm:ss" clearable class="w-full" />'
        elif component == "time":
            body = f'              <NTimePicker v-model:formatted-value="model.{camel}" value-format="HH:mm:ss" clearable class="w-full" />'
        else:
            body = f'              <NInput v-model:value="model.{camel}" :placeholder="$t(\'{placeholder_key}\')" />'

        form_items.extend([item_start, body, item_end])

    # 是否引入 statusTypeOptions
    needs_status_import = any((next((x for x in fields if x.name == n), None) or FieldInfo("", "", "")).enum_type == "StatusType" for n in search_field_names)
    needs_boolean_options = any((next((x for x in fields if x.name == n), None) or FieldInfo("", "", "")).field_type == "BooleanField" for n in search_field_names)

    imports = [
        "import { toRaw } from 'vue';",
        "import { jsonClone } from '@sa/utils';",
        "import { $t } from '@/locales';",
    ]
    if needs_status_import:
        imports.append("import { statusTypeOptions } from '@/constants/business';")

    boolean_options = ""
    if needs_boolean_options:
        boolean_options = """
const booleanOptions = [
  { label: $t('common.yesOrNo.yes'), value: true },
  { label: $t('common.yesOrNo.no'), value: false }
] as any;
"""

    props_block = ""
    if option_props:
        props_lines = [
            "type SelectOptionItem = { label: string; value: string | number };",
            "",
            "interface Props {",
        ]
        props_lines.extend(f"  {prop}?: SelectOptionItem[];" for prop in option_props)
        props_lines.extend([
            "}",
            "",
            "const props = withDefaults(defineProps<Props>(), {",
        ])
        props_lines.extend(f"  {prop}: () => []," for prop in option_props)
        props_lines.extend([
            "});",
            "",
        ])
        props_block = "\n".join(props_lines)

    template = f"""<script setup lang="ts">
{chr(10).join(imports)}
{boolean_options}
{props_block}

defineOptions({{ name: '{entity}Search' }});

interface Emits {{
  (e: 'search'): void;
}}

const emit = defineEmits<Emits>();
const model = defineModel<Api.{ns}.{entity}SearchParams>('model', {{ required: true }});
const defaultModel = jsonClone(toRaw(model.value));

function resetModel() {{
  Object.assign(model.value, defaultModel);
}}

function search() {{
  emit('search');
}}
</script>

<template>
  <NCard :bordered="false" size="small" class="card-wrapper">
    <NCollapse :default-expanded-names="['{entity_kebab}-search']">
      <NCollapseItem :title="$t('common.search')" name="{entity_kebab}-search">
        <NForm :model="model" label-placement="left" :label-width="80">
          <NGrid responsive="screen" item-responsive>
{chr(10).join(form_items)}
            <NFormItemGi span="24 s:12 m:6">
              <NSpace class="w-full" justify="end">
                <NButton @click="resetModel">
                  <template #icon><icon-ic-round-refresh class="text-icon" /></template>
                  {{{{ $t('common.reset') }}}}
                </NButton>
                <NButton type="primary" ghost @click="search">
                  <template #icon><icon-ic-round-search class="text-icon" /></template>
                  {{{{ $t('common.search') }}}}
                </NButton>
              </NSpace>
            </NFormItemGi>
          </NGrid>
        </NForm>
      </NCollapseItem>
    </NCollapse>
  </NCard>
</template>
"""
    return template


def gen_view_drawer(module: str, model: ModelInfo) -> str:
    """生成 <entity>-operate-drawer.vue"""
    entity = model.name
    entity_snake = model.snake_name
    ns = snake_to_pascal(module) + "Manage"
    i18n_page = f"page.{module}.{entity_snake}"

    fields = model.schema_fields
    fk_relations = [r for r in model.relations if r.relation_type in ("ForeignKeyField", "OneToOneField")]
    custom_enum_fields = [f for f in fields if field_form_component(f) == "select-todo"]
    option_props = [option_prop_name(f.name) for f in custom_enum_fields] + [option_prop_name(r.name) for r in fk_relations]

    # 生成 form items
    form_items: list[str] = []
    for f in fields:
        option_expr = f"props.{option_prop_name(f.name)}" if field_form_component(f) == "select-todo" else None
        form_items.extend(_form_item_block(f, i18n_page, is_relation=False, option_expr=option_expr))
    for r in fk_relations:
        form_items.extend(_form_item_block(r, i18n_page, is_relation=True, option_expr=f"props.{option_prop_name(r.name)}"))

    # 默认 model
    default_entries: list[str] = []
    for f in fields:
        camel = snake_to_camel(f.name)
        default_entries.append(f"    {camel}: {_default_value_for_field(f)}")
    for r in fk_relations:
        camel = relation_camel_name(r)
        default_entries.append(f"    {camel}: null")

    # 必填规则
    required_rules: list[str] = []
    for f in fields:
        if f.required:
            camel = snake_to_camel(f.name)
            required_rules.append(f"  {camel}: defaultRequiredRule")
    for r in fk_relations:
        if not r.nullable:
            camel = relation_camel_name(r)
            required_rules.append(f"  {camel}: defaultRequiredRule")

    # 是否需要 statusTypeOptions
    needs_status_import = any(f.enum_type == "StatusType" for f in fields)

    extra_imports: list[str] = []
    if needs_status_import:
        extra_imports.append("import { statusTypeOptions } from '@/constants/business';")

    entity_title_key = f"{i18n_page}.pageTitle"
    add_key = f"{i18n_page}.add{entity}"
    edit_key = f"{i18n_page}.edit{entity}"
    needs_json_helpers = any(f.field_type == "JSONField" for f in fields)
    form_hook_imports = "useFormRules, useNaiveForm" if required_rules else "useNaiveForm"
    form_rules_setup = "const { defaultRequiredRule } = useFormRules();" if required_rules else ""
    rules_block = (
        f"""const rules: Record<string, App.Global.FormRule> = {{
{("," + chr(10)).join(required_rules)}
}};"""
        if required_rules
        else "const rules: Record<string, App.Global.FormRule> = {};"
    )
    json_helpers = (
        """function formatJsonInput(value: unknown): string {
  if (value === null || value === undefined || value === '') return '';
  if (typeof value === 'string') return value;
  return JSON.stringify(value, null, 2);
}

function parseJsonInput(value: string): Record<string, any> | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  return JSON.parse(trimmed) as Record<string, any>;
}
"""
        if needs_json_helpers
        else ""
    )
    props_lines = [
        "interface Props {",
        "  operateType: NaiveUI.TableOperateType;",
        f"  rowData?: Api.{ns}.{entity} | null;",
    ]
    if option_props:
        props_lines.insert(0, "type SelectOptionItem = { label: string; value: string | number };\n")
        props_lines.extend(f"  {prop}?: SelectOptionItem[];" for prop in option_props)
        props_lines.extend([
            "}",
            "",
            "const props = withDefaults(defineProps<Props>(), {",
        ])
        props_lines.extend(f"  {prop}: () => []," for prop in option_props)
        props_lines.extend([
            "});",
        ])
    else:
        props_lines.extend([
            "}",
            "",
            "const props = defineProps<Props>();",
        ])
    props_block = "\n".join(props_lines)

    template = f"""<script setup lang="ts">
import {{ computed, ref, watch }} from 'vue';
import {{ jsonClone }} from '@sa/utils';
import {{ fetchAdd{entity}, fetchUpdate{entity} }} from '@/service/api';
import {{ {form_hook_imports} }} from '@/hooks/common/form';
import {{ $t }} from '@/locales';
{chr(10).join(extra_imports)}

defineOptions({{ name: '{entity}OperateDrawer' }});

{props_block}

interface Emits {{
  (e: 'submitted'): void;
}}

const emit = defineEmits<Emits>();
const visible = defineModel<boolean>('visible', {{ default: false }});
const {{ formRef, validate, restoreValidation }} = useNaiveForm();
{form_rules_setup}

const title = computed(() => {{
  const titles: Record<NaiveUI.TableOperateType, string> = {{
    add: $t('{add_key}'),
    edit: $t('{edit_key}')
  }};
  return titles[props.operateType];
}});

const model = ref(createDefaultModel());

function createDefaultModel(): Api.{ns}.{entity}AddParams {{
  return {{
{("," + chr(10)).join(default_entries)}
  }} as unknown as Api.{ns}.{entity}AddParams;
}}

{rules_block}

{json_helpers}
function handleInitModel() {{
  model.value = createDefaultModel();
  if (props.operateType === 'edit' && props.rowData) {{
    Object.assign(model.value, jsonClone(props.rowData));
  }}
}}

function closeDrawer() {{
  visible.value = false;
}}

async function handleSubmit() {{
  await validate();
  if (props.operateType === 'add') {{
    const {{ error }} = await fetchAdd{entity}(model.value);
    if (error) return;
    window.$message?.success($t('common.addSuccess'));
  }} else {{
    const {{ error }} = await fetchUpdate{entity}({{ id: props.rowData?.id, ...model.value }});
    if (error) return;
    window.$message?.success($t('common.updateSuccess'));
  }}
  closeDrawer();
  emit('submitted');
}}

watch(visible, () => {{
  if (visible.value) {{
    handleInitModel();
    restoreValidation();
  }}
}});
</script>

<template>
  <NDrawer v-model:show="visible" display-directive="show" :width="420">
    <NDrawerContent :title="title" :native-scrollbar="false" closable>
      <NForm ref="formRef" :model="model" :rules="rules">
{chr(10).join(form_items)}
      </NForm>
      <template #footer>
        <NSpace :size="16">
          <NButton @click="closeDrawer">{{{{ $t('common.cancel') }}}}</NButton>
          <NButton type="primary" @click="handleSubmit">{{{{ $t('common.confirm') }}}}</NButton>
        </NSpace>
      </template>
    </NDrawerContent>
  </NDrawer>
</template>
"""
    # 规避未使用变量
    _ = entity_title_key
    return template


# ─── i18n 片段 ───


def gen_i18n_zh(module: str, module_cn: str, models: list[ModelInfo]) -> str:
    """生成 zh-cn TS 模块 — default export `{ route, page }`，由 locale.ts 自动 glob 合并。"""
    lines = [
        f"// 自动生成（cli-gen-web）— 模块：{module_cn}",
        "// 由 web/src/locales/locale.ts 通过 import.meta.glob 自动合并到 zh-CN messages。",
        "// 修改字段含义请改对应模型 description 后重跑 cli-gen-web；未涵盖的文案可在本文件追加。",
        "",
        "export default {",
        "  route: {",
        f"    '{module_route_key(module)}': '{module_cn}',",
    ]
    for model in models:
        lines.append(f"    '{model_route_key(module, model)}': '{model.cn_name}',")
    lines.append("  },")
    lines.append("  page: {")
    lines.append(f"    {module}: {{")
    lines.append("      common: { status: '状态', form: { status: '请选择状态' } },")
    for model in models:
        entity_snake = model.snake_name
        fields = model.schema_fields
        fk_relations = [r for r in model.relations if r.relation_type in ("ForeignKeyField", "OneToOneField")]

        lines.append(f"      {entity_snake}: {{")
        lines.append(f"        pageTitle: '{model.cn_name}',")
        for f in fields:
            camel = snake_to_camel(f.name)
            title = cn_title(f.description, f.name)
            lines.append(f"        {camel}: '{title}',")
        for r in fk_relations:
            camel = snake_to_camel(r.name)
            if r.description:
                lines.append(f"        {camel}: '{cn_title(r.description, r.name)}',")
            else:
                lines.append(f"        {camel}: '{camel}',  // TODO: 手动填写中文")
        lines.append("        form: {")
        for f in fields:
            camel = snake_to_camel(f.name)
            title = cn_title(f.description, f.name)
            verb = "请选择" if field_form_component(f).startswith("select") else "请输入"
            lines.append(f"          {camel}: '{verb}{title}',")
        for r in fk_relations:
            camel = snake_to_camel(r.name)
            if r.description:
                lines.append(f"          {camel}: '请选择{cn_title(r.description, r.name)}',")
            else:
                lines.append(f"          {camel}: '请选择{camel}',  // TODO")
        lines.append("        },")
        lines.append(f"        add{model.name}: '新增{model.cn_name}',")
        lines.append(f"        edit{model.name}: '编辑{model.cn_name}'")
        lines.append("      },")
    lines.append("    },")
    lines.append("  },")
    lines.append("};")
    lines.append("")
    return "\n".join(lines)


def gen_i18n_en(module: str, models: list[ModelInfo]) -> str:
    """生成 en-us TS 模块 — default export `{ route, page }`。"""
    module_pascal = snake_to_pascal(module)
    lines = [
        f"// Auto-generated by cli-gen-web — module: {module_pascal}",
        "// Merged into en-US messages by web/src/locales/locale.ts via import.meta.glob.",
        "",
        "export default {",
        "  route: {",
        f"    '{module_route_key(module)}': '{module_pascal}',",
    ]
    for model in models:
        name_title = re.sub(r"(?<!^)(?=[A-Z])", " ", model.name).strip()
        lines.append(f"    '{model_route_key(module, model)}': '{name_title}',")
    lines.append("  },")
    lines.append("  page: {")
    lines.append(f"    {module}: {{")
    lines.append("      common: { status: 'Status', form: { status: 'Please select status' } },")
    for model in models:
        entity_snake = model.snake_name
        entity_en = re.sub(r"(?<!^)(?=[A-Z])", " ", model.name).strip()
        fields = model.schema_fields
        fk_relations = [r for r in model.relations if r.relation_type in ("ForeignKeyField", "OneToOneField")]

        lines.append(f"      {entity_snake}: {{")
        lines.append(f"        pageTitle: '{entity_en}',")
        for f in fields:
            camel = snake_to_camel(f.name)
            lines.append(f"        {camel}: '{camel}',")
        for r in fk_relations:
            camel = snake_to_camel(r.name)
            lines.append(f"        {camel}: '{camel}',")
        lines.append("        form: {")
        for f in fields:
            camel = snake_to_camel(f.name)
            verb = "Please select" if field_form_component(f).startswith("select") else "Please input"
            lines.append(f"          {camel}: '{verb} {camel}',")
        for r in fk_relations:
            camel = snake_to_camel(r.name)
            lines.append(f"          {camel}: 'Please select {camel}',")
        lines.append("        },")
        lines.append(f"        add{model.name}: 'Add {entity_en}',")
        lines.append(f"        edit{model.name}: 'Edit {entity_en}'")
        lines.append("      },")
    lines.append("    },")
    lines.append("  },")
    lines.append("};")
    lines.append("")
    return "\n".join(lines)


def gen_i18n_schema_dts(module: str, models: list[ModelInfo]) -> str:
    """生成 types.d.ts — 通过 declare 合并向 `App.I18n.GeneratedPages` 注入 `page.<module>` 类型。

    Schema.page 与本接口取交集，使 `$t('page.<module>.<entity>.xxx')` 可被 vue-tsc 校验。
    """
    lines = [
        f"// 自动生成（cli-gen-web）— 模块 {module} 的 i18n 类型扩展。",
        "// 通过 interface declaration merging 注入 App.I18n.GeneratedPages。",
        "",
        "declare global {",
        "  namespace App.I18n {",
        "    interface GeneratedPages {",
        f"      {module}: {{",
        "        common: {",
        "          status: string;",
        "          form: { status: string };",
        "        };",
    ]
    for model in models:
        entity_snake = model.snake_name
        fields = model.schema_fields
        fk_relations = [r for r in model.relations if r.relation_type in ("ForeignKeyField", "OneToOneField")]

        lines.append(f"        {entity_snake}: {{")
        lines.append("          pageTitle: string;")
        for f in fields:
            lines.append(f"          {snake_to_camel(f.name)}: string;")
        for r in fk_relations:
            lines.append(f"          {snake_to_camel(r.name)}: string;")
        lines.append("          form: {")
        for f in fields:
            lines.append(f"            {snake_to_camel(f.name)}: string;")
        for r in fk_relations:
            lines.append(f"            {snake_to_camel(r.name)}: string;")
        lines.append("          };")
        lines.append(f"          add{model.name}: string;")
        lines.append(f"          edit{model.name}: string;")
        lines.append("        };")
    lines.append("      };")
    lines.append("    }")
    lines.append("  }")
    lines.append("}")
    lines.append("")
    lines.append("export {};")
    lines.append("")
    return "\n".join(lines)


# ─── 幂等追加 service/api/index.ts ───


def append_to_index_ts(web_root: Path, module: str, *, dry_run: bool = False) -> str:
    """向 service/api/index.ts 追加 export，已存在则跳过。返回状态。"""
    index_path = web_root / "src" / "service" / "api" / "index.ts"
    if not index_path.exists():
        return "not-found"

    content = index_path.read_text(encoding="utf-8")
    export_line = f"export * from './{module}-manage';"
    if export_line in content:
        return "exists"

    if dry_run:
        return "would-append"

    new_content = content.rstrip() + "\n" + export_line + "\n"
    index_path.write_text(new_content, encoding="utf-8")
    return "appended"


# ─── 汇总生成 ───


def generate_web(
    web_root: Path,
    module: str,
    module_cn: str,
    models: list[ModelInfo],
    *,
    list_fields_map: dict[str, list[str]],
    search_fields_map: dict[str, list[str]],
    button_auth_models: set[str] | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> list[tuple[str, str]]:
    """生成前端所有文件，返回 [(相对路径, 状态)] 列表。"""
    results: list[tuple[str, str]] = []
    button_auth_models = button_auth_models or set()

    def write(path: Path, content: str) -> None:
        rel = path.relative_to(web_root).as_posix()
        path_exists = path.exists()
        if path_exists and not force:
            results.append((rel, "exists"))
            return
        if dry_run:
            results.append((rel, "would-overwrite" if path_exists else "would-create"))
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        results.append((rel, "created"))

    # service ts
    write(
        web_root / "src" / "service" / "api" / f"{module}-manage.ts",
        gen_service_ts(module, models),
    )

    # typings d.ts
    write(
        web_root / "src" / "typings" / "api" / f"{module}-manage.d.ts",
        gen_typings_dts(module, models, search_fields_map),
    )

    # views
    module_view_dir = route_segment(module)
    for model in models:
        entity_kebab = route_segment(model.snake_name)
        view_dir = web_root / "src" / "views" / module_view_dir / entity_kebab

        list_fields = list_fields_map.get(model.name, [f.name for f in model.schema_fields[:5]])
        search_fields = search_fields_map.get(model.name, [])

        write(view_dir / "index.vue", gen_view_index(module, model, list_fields, button_auth=model.name in button_auth_models))
        write(view_dir / "modules" / f"{entity_kebab}-search.vue", gen_view_search(module, model, search_fields))
        write(view_dir / "modules" / f"{entity_kebab}-operate-drawer.vue", gen_view_drawer(module, model))

    # i18n — 真实 TS 模块，由 web/src/locales/locale.ts 通过 import.meta.glob 自动合并
    i18n_dir = web_root / "src" / "locales" / "langs" / "_generated" / module
    write(i18n_dir / "zh-cn.ts", gen_i18n_zh(module, module_cn, models))
    write(i18n_dir / "en-us.ts", gen_i18n_en(module, models))
    write(i18n_dir / "types.d.ts", gen_i18n_schema_dts(module, models))

    # 追加 index.ts
    status = append_to_index_ts(web_root, module, dry_run=dry_run)
    results.append(("src/service/api/index.ts", status))

    return results
