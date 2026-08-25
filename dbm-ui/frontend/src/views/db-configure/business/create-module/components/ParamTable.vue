<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkLoading :loading="loading">
    <div class="param-operations mb-16">
      <div class="param-operations-left">
        <BkButton
          theme="primary"
          @click="handleAddParam">
          {{ t('添加参数') }}
        </BkButton>
        <BkButton
          v-if="selectable"
          :disabled="selectedRows.length === 0"
          @click="handleBatchEdit">
          {{ t('批量编辑') }}
        </BkButton>
        <div
          v-if="changedCount > 0"
          class="only-changed">
          <I18nT
            keypath="已修改n项"
            tag="span">
            <template #n>
              <span style="font-weight: 700; color: #f59500">{{ changedCount }}</span>
            </template>
          </I18nT>
          <BkCheckbox
            v-model="showChangedOnly"
            @change="refreshTable">
            {{ t('仅显示已修改') }}
          </BkCheckbox>
        </div>
      </div>
      <div class="param-operations-right">
        <DbQuickSearch
          v-model="searchValue"
          :data="quickSearchData"
          parse-url
          :placeholder="t('搜索参数名_当前值_允许值_重启生效')"
          style="width: 500px"
          @change="refreshTable" />
      </div>
    </div>
    <DbTable
      ref="paramTableRef"
      :data-source="paramDataSource"
      :default-limit="100"
      :disable-select-method="(row: any) => row.flag_readonly === 1"
      :filter-value="searchValue"
      :fixed-pagination="fixedPagination"
      :row-class-name="getRowClassName"
      :row-key="rowKey"
      :selectable="selectable"
      @clear-search="refreshTable"
      @filter-change="handleFilterChange"
      @request-success="initDescriptionTippy"
      @selection="handleSelectionChange">
      <TableColumn
        col-key="conf_name"
        fixed="left"
        :min-width="300"
        :title="t('参数名')"
        :width="300">
        <template #default="{ row, rowIndex }">
          <template v-if="rowIndex === 0 && isAddingRow">
            <BkSelect
              v-model="newRow.conf_name"
              :clearable="false"
              filterable
              :placeholder="t('请选择参数')">
              <BkOption
                v-for="param of availableParams"
                :key="param.conf_name"
                :label="param.conf_name"
                :value="param.conf_name" />
            </BkSelect>
          </template>
          <template v-else>
            {{ row.conf_name }}
            <DbIcon
              v-if="row.description"
              class="param-desc-icon ml-4"
              :data-conf-name="row.conf_name"
              :data-description="row.description"
              type="bk-dbm-icon db-icon-attention" />
            <BkTag
              v-if="row.op_type === 'add'"
              class="ml-8"
              size="small"
              theme="success">
              NEW
            </BkTag>
          </template>
        </template>
      </TableColumn>
      <TableColumn
        col-key="conf_value"
        :title="t('当前值')"
        :width="300">
        <template #default="{ row, rowIndex }">
          <!-- 新增行 -->
          <template v-if="rowIndex === 0 && isAddingRow">
            <div class="inline-edit-cell">
              <ValueEditor
                v-model="newRow.conf_value"
                :disabled="!selectedParamInfo"
                :value-allowed="selectedParamInfo?.value_allowed || ''"
                :value-default="selectedParamInfo?.value_default || ''"
                :value-type-sub="selectedParamInfo?.value_type_sub || ''" />
              <BkButton
                class="inline-edit-cell-confirm"
                size="small"
                theme="primary"
                @click="handleConfirmAdd">
                <DbIcon type="check-line" />
              </BkButton>
              <BkButton
                class="inline-edit-cell-cancel"
                size="small"
                @click="handleCancelAdd">
                <DbIcon type="close" />
              </BkButton>
            </div>
          </template>
          <!-- 编辑模式 -->
          <template v-else-if="editingRowKey === row[rowKey]">
            <div class="inline-edit-cell">
              <ValueEditor
                v-model="editingValue"
                :is-encrypted="row.flag_encrypt === 1"
                :value-allowed="row.value_allowed || ''"
                :value-type-sub="row.value_type_sub || ''" />
              <BkButton
                class="inline-edit-cell-confirm"
                size="small"
                theme="primary"
                @click="handleConfirmEdit">
                <DbIcon type="check-line" />
              </BkButton>
              <BkButton
                class="inline-edit-cell-cancel"
                size="small"
                @click="handleCancelEdit">
                <DbIcon type="close" />
              </BkButton>
            </div>
          </template>
          <template v-else>
            <span class="value-cell">
              <span
                v-if="row.conf_value === ''"
                class="no-constraint-text">
                {{ t('空字符串') }}
              </span>
              <span
                v-else
                v-bk-tooltips="{
                  content: row.flag_encrypt === 1 ? '******' : (row.conf_value ?? '--'),
                  disabled: !row.conf_value || !overflowStates[row.conf_name],
                  extCls: 'param-table-value-tooltip',
                }"
                class="value-cell-text"
                @mouseenter="handleCellMouseEnter($event, row)">
                {{ row.flag_encrypt === 1 ? '******' : (row.conf_value ?? '--') }}
              </span>
              <DbIcon
                v-if="row.flag_readonly !== 1"
                v-bk-tooltips="{ content: t('编辑参数') }"
                class="value-cell-edit"
                type="bk-dbm-icon db-icon-edit"
                @click="handleStartEdit(row)" />
            </span>
          </template>
        </template>
      </TableColumn>
      <TableColumn
        col-key="value_allowed"
        ellipsis
        :title="t('允许值')"
        :width="300">
        <template #default="{ row, rowIndex }">
          <!-- 新增行 -->
          <template v-if="rowIndex === 0 && isAddingRow">
            <template v-if="selectedParamInfo?.value_type_sub && selectedParamInfo?.value_type_sub !== 'STRING'">
              <BkTag>{{ selectedParamInfo.value_type_sub }}</BkTag>
              <span class="ml-4">{{ selectedParamInfo.value_allowed || '--' }}</span>
            </template>
            <span
              v-else
              class="no-constraint-text">
              {{ t('无约束') }}
            </span>
          </template>
          <!-- 普通行 -->
          <template v-else>
            <template v-if="row.value_type_sub && row.value_type_sub !== 'STRING'">
              <BkTag>{{ row.value_type_sub }}</BkTag>
              <span class="ml-4">{{ row.value_allowed || '--' }}</span>
            </template>
            <span
              v-else
              class="no-constraint-text">
              {{ t('无约束') }}
            </span>
          </template>
        </template>
      </TableColumn>
      <TableColumn
        col-key="need_restart"
        :filter="needRestartFilter"
        :title="t('重启生效')"
        :width="100">
        <template #default="{ row, rowIndex }">
          <template v-if="rowIndex === 0 && isAddingRow">
            {{ selectedParamInfo?.need_restart === 1 ? t('是') : t('否') }}
          </template>
          <template v-else>
            {{ row.need_restart === 1 ? t('是') : t('否') }}
          </template>
        </template>
      </TableColumn>
      <TableColumn
        col-key="row-operation"
        fixed="right"
        :title="t('操作')"
        :width="150">
        <template #default="{ row, rowIndex }: { row: ConfItem, rowIndex: number }">
          <!-- 编辑/新增状态下不显示操作按钮（已移至当前值列） -->
          <template v-if="isAddingRow && rowIndex === 0 || editingRowKey === row[rowKey as keyof ConfItem]">
            --
          </template>
          <template v-else>
            <BkButton
              v-if="row.flag_readonly !== 1"
              class="mr-16"
              text
              theme="primary"
              @click="handleStartEdit(row)">
              {{ t('编辑') }}
            </BkButton>
          </template>
        </template>
      </TableColumn>
    </DbTable>

    <!-- 批量编辑侧滑 -->
    <BatchEditSideslider
      v-model:is-show="batchEditConfig.isShow"
      :data="selectedRows"
      :fetch-params="fetchParams"
      @saved="handleBatchEditSaved" />
  </BkLoading>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import type { Instance } from 'tippy.js';
  import { I18nT, useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getConfigNames, getLevelConfig, updateBusinessConfig, validateConfItems } from '@services/source/configs';

  import { useGlobalBizs } from '@stores';

  import { dbTippy } from '@common/tippy';

  import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import ValueEditor from '@views/db-configure/components/ValueEditor.vue';

  import BatchEditSideslider from './BatchEditSideslider.vue';

  type LevelConfigResult = ServiceReturnType<typeof getLevelConfig>;

  export type ConfItem = {} & LevelConfigResult['conf_items'][number];

  export interface Props {
    /** 配置名称（用于保存时） */
    configName?: string;
    confType: string;
    /** 是否固定分页 */
    fixedPagination?: boolean;
    /** 层级信息（用于集群级别） */
    levelInfo?: Record<string, string>;
    /** 层级名称 */
    levelName?: string;
    /** 层级值 */
    levelValue?: number;
    namespace: string;
    /** 行唯一标识字段 */
    rowKey?: string;
    /** 是否支持行选择（批量编辑） */
    selectable?: boolean;
    version: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    configName: '',
    fixedPagination: false,
    levelInfo: undefined,
    levelName: 'app',
    levelValue: undefined,
    rowKey: 'conf_name',
    selectable: false,
  });

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const allConfItems = ref<ConfItem[]>([]);
  const originConfItems = ref<ConfItem[]>([]);
  const availableParams = ref<ConfItem[]>([]);
  // 本地新增但尚未被服务端数据刷新覆盖的项（追加到列表末尾，不破坏原始排序）
  const pendingAddedItems = ref<ConfItem[]>([]);

  // 行唯一标识字段
  const rowKeyField = computed(() => props.rowKey as keyof ConfItem);

  // 参数搜索
  const searchValue = ref<Record<string, any>>({});
  const quickSearchData = [
    { id: 'conf_name', name: t('参数名'), type: 'input' as const },
    { id: 'conf_value', name: t('当前值'), type: 'input' as const },
    { id: 'value_allowed', name: t('允许值'), type: 'input' as const },
    {
      id: 'need_restart',
      list: [
        { label: t('是'), value: '1' },
        { label: t('否'), value: '0' },
      ],
      name: t('重启生效'),
      type: 'multiple' as const,
    },
  ];

  // 表格
  const paramTableRef = ref<InstanceType<typeof DbTable>>();
  const tippyInstances: Instance[] = [];
  const selectedRows = ref<ConfItem[]>([]);
  // 记录单元格文本是否溢出（key: conf_name，用于控制 tooltip 仅在溢出时显示）
  const overflowStates = ref<Record<string, boolean>>({});

  // 表格列筛选
  const needRestartFilter = {
    component: markRaw(MultipleSelect),
    name: t('重启生效'),
    props: {
      list: [
        { label: t('是'), value: '1' },
        { label: t('否'), value: '0' },
      ],
    },
    showConfirmAndReset: true,
  };

  // 新增行
  const isAddingRow = ref(false);
  const newRow = ref({
    conf_name: '',
    conf_value: '',
  });
  // 当前选择的参数信息
  const selectedParamInfo = ref<ConfItem | null>(null);

  // 行内编辑
  const editingRowKey = ref('');
  const editingValue = ref('');
  const editingOriginValue = ref('');

  // 批量编辑侧滑
  const batchEditConfig = reactive({
    isShow: false,
  });

  // 仅显示已修改
  const showChangedOnly = ref(false);

  /** 重置编辑状态 */
  const resetEditingState = () => {
    editingRowKey.value = '';
    editingValue.value = '';
    editingOriginValue.value = '';
    refreshTable();
  };

  /** 获取行样式名（修改项行添加 class） */
  const getRowClassName = ({ row }: { row: ConfItem }) => {
    const origin = originConfItems.value.find((o) => o.conf_name === row.conf_name);
    if (origin && row.conf_value !== origin.conf_value) {
      return 'row-modified';
    }
    return '';
  };

  /** 刷新表格数据 */
  const refreshTable = () => {
    paramTableRef.value?.fetchData({}, true);
  };

  /** 检测单元格文本是否溢出（用于控制 tooltip 仅在溢出时显示） */
  const handleCellMouseEnter = (e: MouseEvent, row: ConfItem) => {
    const el = e.target as HTMLElement;
    overflowStates.value[row.conf_name] = el.scrollWidth > el.clientWidth;
  };

  /** 初始化描述 tippy 提示 */
  const initDescriptionTippy = () => {
    tippyInstances.forEach((inst) => inst.destroy());
    tippyInstances.length = 0;

    nextTick(() => {
      const icons = document.querySelectorAll('.param-desc-icon');
      icons.forEach((el) => {
        const iconEl = el as HTMLElement;
        const confName = iconEl.dataset.confName || '';
        const description = iconEl.dataset.description || '';
        if (!description) return;

        const content = document.createElement('div');
        content.className = 'description-tippy-content';
        content.innerHTML = `<div class="desc-title">${confName}</div><div class="desc-text">${description}</div>`;

        const instance = dbTippy(iconEl, {
          allowHTML: true,
          appendTo: () => document.body,
          arrow: true,
          content,
          hideOnClick: false,
          interactive: false,
          placement: 'top',
          theme: 'light',
          trigger: 'mouseenter focus',
          zIndex: 9999,
        });
        tippyInstances.push(instance);
      });
    });
  };

  /** 构建更新配置参数 */
  const buildUpdateParams = (confItems: ConfItem[]) => ({
    ...fetchParams.value,
    conf_items: confItems,
    confirm: 0,
    description: '',
    name: props.configName || '',
    publish_description: '',
  });

  const fetchParams = computed(() => ({
    bk_biz_id: globalBizsStore.currentBizId,
    conf_type: props.confType,
    level_info: props.levelInfo,
    level_name: props.levelName as any,
    level_value: props.levelValue ?? globalBizsStore.currentBizId,
    meta_cluster_type: props.namespace,
    version: props.version,
  }));

  /** 参数数据源函数 */
  const paramDataSource = (params: { limit: number; offset: number }) => {
    // 合并本地新增项（排在前面）+ 服务端数据，按 conf_name 去重
    let data = [...pendingAddedItems.value, ...allConfItems.value];
    const seen = new Set<string>();
    data = data.filter((item) => {
      if (seen.has(item.conf_name)) return false;
      seen.add(item.conf_name);
      return true;
    });

    // 前端搜索 + 列筛选统一过滤
    const filters = searchValue.value;
    if (Object.keys(filters).length > 0) {
      data = data.filter((item) =>
        Object.entries(filters).every(([key, val]) => {
          if (!val) return true;
          if (key === 'need_restart') {
            return val.split(',').includes(String(item.need_restart));
          }
          const search = String(val).toLowerCase();
          const fieldValue = String((item as Record<string, any>)[key] ?? '').toLowerCase();
          return fieldValue.includes(search);
        }),
      );
    }

    // 仅显示已修改（包括新增和已修改的参数）
    if (showChangedOnly.value && !isAddingRow.value) {
      const changedNames = new Set([
        ...getChangedItems().map((i) => i.conf_name),
        ...pendingAddedItems.value.map((i) => i.conf_name),
      ]);
      data = data.filter((item) => changedNames.has(item.conf_name));
    }

    // 如果正在新增行，在首行插入空行
    if (isAddingRow.value) {
      const paramInfo =
        selectedParamInfo.value || newRow.value.conf_name
          ? availableParams.value.find((p) => p.conf_name === newRow.value.conf_name)
          : null;
      const emptyRow = {
        ...(paramInfo || {
          conf_name: '',
          conf_value: '',
          description: '',
          flag_readonly: 0,
          flag_visible: 0,
          need_restart: 0,
          op_type: 'add',
          value_allowed: '',
          value_default: '',
        }),
        conf_name: newRow.value.conf_name,
        conf_value: newRow.value.conf_value || paramInfo?.conf_value || '',
        op_type: 'add',
      } as ConfItem;
      data = [emptyRow, ...data];
    }

    const start = params.offset;
    const end = start + params.limit;
    const result = {
      count: data.length,
      results: data.slice(start, end),
    };

    return Promise.resolve(result);
  };

  /** 获取配置 */
  const { loading, run: fetchLevelConfig } = useRequest(getLevelConfig, {
    manual: true,
    onSuccess(res) {
      allConfItems.value = res.conf_items || [];
      originConfItems.value = _.cloneDeep(res.conf_items || []);
      // 服务端数据已包含最新变更，清空本地新增缓存
      pendingAddedItems.value = [];
      nextTick(() => {
        paramTableRef.value?.fetchData({}, true);
      });
    },
  });

  /** 获取可选参数名 */
  const { run: fetchConfigNames } = useRequest(getConfigNames, {
    manual: true,
    onSuccess(res) {
      // 过滤掉已在当前配置列表中存在的参数，避免重复添加
      const existNames = new Set(allConfItems.value.map((item) => item.conf_name));
      availableParams.value = res.filter((p) => !existNames.has(p.conf_name));
    },
  });

  // 监听 version 变化重新获取数据
  watch(
    () => [props.namespace, props.version],
    ([namespace, version]) => {
      if (namespace && version) {
        fetchLevelConfig(fetchParams.value);
        fetchConfigNames({
          conf_type: props.confType,
          meta_cluster_type: namespace,
          version: version,
        });
      }
    },
    { immediate: true },
  );

  /** 选中变化 */
  const handleSelectionChange = (_keys: string[], list: ConfItem[]) => {
    selectedRows.value = list;
  };

  /** 添加参数（若有未完成的编辑，先丢弃） */
  const handleAddParam = () => {
    // 如果有正在进行的行内编辑，先重置
    if (editingRowKey.value) {
      resetEditingState();
    }
    isAddingRow.value = true;
    newRow.value = { conf_name: '', conf_value: '' };
    selectedParamInfo.value = null;
    refreshTable();
  };

  /** 过滤器变化（列筛选 → 同步到 searchValue） */
  const handleFilterChange = (filterVal: Record<string, string>) => {
    searchValue.value = filterVal;
  };

  /** 监听新增行选择参数变化 */
  watch(
    () => newRow.value.conf_name,
    (val) => {
      if (val) {
        selectedParamInfo.value = availableParams.value.find((p) => p.conf_name === val) || null;
      } else {
        selectedParamInfo.value = null;
      }
      refreshTable();
    },
  );

  /** 确认新增 */
  const handleConfirmAdd = () => {
    if (!newRow.value.conf_name) return;

    const paramInfo = availableParams.value.find((p) => p.conf_name === newRow.value.conf_name);
    if (!paramInfo) return;

    const confValue = newRow.value.conf_value || paramInfo.conf_value || '';

    // 追加到 pending 列表末尾，不破坏原始数据排序
    pendingAddedItems.value.push({
      ...paramInfo,
      conf_value: confValue,
      op_type: 'add',
    });

    isAddingRow.value = false;
    refreshTable();
  };

  /** 取消新增 */
  const handleCancelAdd = () => {
    // 从本地新增缓存中移除（不影响服务端数据排序）
    if (newRow.value.conf_name) {
      const idx = pendingAddedItems.value.findIndex((item) => item.conf_name === newRow.value.conf_name);
      if (idx >= 0) {
        pendingAddedItems.value.splice(idx, 1);
      }
    }
    isAddingRow.value = false;
    newRow.value = { conf_name: '', conf_value: '' };
    selectedParamInfo.value = null;
    refreshTable();
  };

  /** 开始行内编辑（若有未完成的新增或编辑，先丢弃） */
  const handleStartEdit = (row: ConfItem) => {
    // 如果正在新增行，先取消
    if (isAddingRow.value) {
      handleCancelAdd();
    }
    // 如果已有其他行在编辑，先重置
    if (editingRowKey.value && editingRowKey.value !== row[rowKeyField.value]) {
      resetEditingState();
    }
    editingRowKey.value = row[rowKeyField.value] as any;
    // 加密参数不带入原值，由用户输入新值
    if (row.flag_encrypt === 1) {
      editingValue.value = '';
      editingOriginValue.value = '';
    } else {
      editingValue.value = row.conf_value ?? '';
      editingOriginValue.value = row.conf_value ?? '';
    }
  };

  /** 确认编辑 */
  const handleConfirmEdit = () => {
    const target = allConfItems.value.find((item) => item[rowKeyField.value] === editingRowKey.value);
    if (target) {
      target.conf_value = editingValue.value;
      target.op_type = 'update';
    }
    resetEditingState();
  };

  /** 取消编辑 */
  const handleCancelEdit = () => {
    // 恢复原始值
    const target = allConfItems.value.find((item) => item[rowKeyField.value] === editingRowKey.value);
    if (target && editingOriginValue.value !== undefined) {
      target.conf_value = editingOriginValue.value;
    }
    resetEditingState();
  };

  /** 批量编辑 */
  const handleBatchEdit = () => {
    batchEditConfig.isShow = true;
  };

  /** 批量编辑保存回调 - 前端暂存变更 */
  const handleBatchEditSaved = (changedItems: ConfItem[]) => {
    changedItems.forEach((changedItem) => {
      const target = allConfItems.value.find((item) => item.conf_name === changedItem.conf_name);
      if (target) {
        target.conf_value = changedItem.conf_value;
        target.op_type = 'update';
      }
    });
    refreshTable();
  };

  /** 是否有变更 */
  const hasChange = () => pendingAddedItems.value.length > 0 || !_.isEqual(allConfItems.value, originConfItems.value);

  /** 获取变更的参数列表 */
  const getChangedItems = () => {
    const changedItems: ConfItem[] = [];

    // 新增的参数（来自本地待提交列表）
    pendingAddedItems.value.forEach((item) => {
      changedItems.push({ ...item, op_type: 'add' });
    });

    // 已修改的参数（与服务端初始值对比）
    allConfItems.value.forEach((item) => {
      const origin = originConfItems.value.find((o) => o.conf_name === item.conf_name);
      if (origin && origin.conf_value !== item.conf_value) {
        changedItems.push({ ...item, op_type: 'update' });
      }
    });

    return changedItems;
  };

  /** 获取已修改项数量 */
  const changedCount = computed(() => getChangedItems().length);

  /** 获取总参数数量 */
  const totalCount = computed(() => allConfItems.value.length + pendingAddedItems.value.length);

  /** 绑定参数配置（由父组件在创建模块成功后调用） */
  const bindConfigParameters = async () => {
    const changedItems = getChangedItems();
    if (changedItems.length === 0) return;

    // 后端校验合法性
    await validateConfItems(
      changedItems.map((item) => ({
        conf_name: item.conf_name,
        op_type: item.op_type as 'add' | 'update',
        value_allowed: item.value_allowed,
        value_default: item.conf_value ?? '',
        value_type: item.value_type ?? '',
        value_type_sub: item.value_type_sub ?? '',
      })),
    );

    await updateBusinessConfig(buildUpdateParams(changedItems));
  };

  /** 重置 */
  const handleReset = () => {
    allConfItems.value = [];
    originConfItems.value = [];
    availableParams.value = [];
    pendingAddedItems.value = [];
    tippyInstances.forEach((inst) => inst.destroy());
    tippyInstances.length = 0;
  };

  /** 回车确认 */
  const handleEnter = (e: KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleConfirmEdit();
    }
  };

  onMounted(() => {
    document.addEventListener('keydown', handleEnter);
  });

  onUnmounted(() => {
    document.removeEventListener('keydown', handleEnter);
    tippyInstances.forEach((inst) => inst.destroy());
    tippyInstances.length = 0;
  });

  defineExpose({
    bindConfigParameters,
    changedCount,
    handleReset,
    hasChange,
    totalCount,
  });
</script>

<style lang="less" scoped>
  .param-operations {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .param-operations-left {
    display: flex;
    align-items: center;
    gap: 16px;

    .only-changed {
      display: flex;
      align-items: center;
      gap: 8px;

      :deep(.bk-checkbox) {
        display: flex;
      }
    }
  }

  .param-operations-right {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .inline-edit-cell {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .inline-edit-cell-confirm {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 26px;
    height: 26px;
    padding: 0;
    font-size: 16px;
  }

  .inline-edit-cell-cancel {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 26px;
    height: 26px;
    padding: 0;
    font-size: 16px;
  }

  .value-cell {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  :deep(.row-modified td:nth-child(2)) {
    background: #fdf4e8 !important;
  }

  .value-cell-text {
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .value-cell-tag {
    padding: 0 4px;
    font-size: 12px;
    line-height: 18px;
    color: #ff9c01;
    white-space: nowrap;
    background: #fff3e1;
    border-radius: 2px;
  }

  .value-cell-edit {
    display: none;
    font-size: 14px;
    cursor: pointer;
    color: #63656e;
  }

  .value-cell-edit:hover {
    color: #3a84ff;
  }

  .restart-icon-yes,
  .restart-icon-no {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: 50%;
  }

  .restart-icon-yes {
    font-size: 12px;
    color: #65c389;
    background: #ebfaf0;
  }

  .restart-icon-no {
    font-size: 16px;
    color: #ff5656;
    background: #ffebeb;
  }

  .no-constraint-text {
    color: #c4c6cc;
  }

  :deep(tr:hover) .value-cell-edit {
    display: inline-block;
  }

  .batch-edit-content {
    padding: 8px 0;
  }

  .batch-edit-tip {
    padding: 12px 16px;
    background: #f5f7fa;
  }

  .param-desc-icon {
    font-size: 14px;
    cursor: pointer;
    color: #c4c6cc;

    &:hover {
      color: #3a84ff;
    }
  }
</style>

<style lang="less">
  .param-table-value-tooltip {
    max-width: 400px;
    word-break: break-word;
  }

  .description-tippy-content {
    max-width: 320px;
    padding: 12px 16px;

    .desc-title {
      margin-bottom: 8px;
      font-size: 12px;
      font-weight: 600;
      color: #313238;
      word-break: break-all;
    }

    .desc-text {
      font-size: 12px;
      line-height: 22px;
      color: #63656e;
      word-break: break-word;
    }
  }
</style>
