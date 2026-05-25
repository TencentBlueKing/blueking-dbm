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
        <BkPopConfirm
          :cancel-text="t('取消')"
          :confirm-text="t('确认恢复')"
          :title="
            t('确认批量恢复 n 个参数默认值？', {
              n: selectedRows.filter((item) => item.level_name === levelName).length,
            })
          "
          trigger="click"
          :width="275"
          @confirm="handleRestoreDefault">
          <template #content>
            <div
              class="mb-16"
              style="line-height: 20px">
              <p>
                {{ t('恢复后，该参数的值降默认继承父级的值，随父级内容变化') }}
              </p>
            </div>
          </template>
          <span @click.stop>
            <BkButton :disabled="selectedRows.every((item) => item.level_name !== levelName)">
              {{ t('恢复默认') }}
            </BkButton>
          </span>
        </BkPopConfirm>
      </div>
      <div class="param-operations-right">
        <BkCheckbox
          v-model="showCustomOnly"
          @change="refreshTable">
          {{ t('仅显示自定义') }}
        </BkCheckbox>
        <DbQuickSearch
          v-model="paramSearchValue"
          :data="paramQuickSearchData"
          :placeholder="t('搜索参数名_当前值_允许值_重启生效')"
          style="width: 500px"
          @change="handleParamSearchChange" />
      </div>
    </div>
    <DbTable
      ref="paramTableRef"
      :data-source="paramDataSource"
      :disable-select-method="(row: any) => row.flag_readonly === 1"
      :filter-value="filterValue"
      :fixed-pagination="fixedPagination"
      :row-key="rowKey"
      :selectable="selectable"
      @clear-search="handleParamSearchChange"
      @filter-change="handleFilterChange"
      @request-success="handleRequestSuccess"
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
        ellipsis
        :title="t('当前值')"
        :width="200">
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
                :loading="saveLoading"
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
                :loading="saveLoading"
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
              <span class="value-cell-text">{{ row.flag_encrypt === 1 ? '******' : (row.conf_value ?? '--') }}</span>
              <BkTag
                v-if="row.level_name === levelName"
                size="small"
                theme="warning">
                {{ t('自定义') }}
              </BkTag>
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
        :width="200">
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
        col-key="operation"
        fixed="right"
        :title="t('操作')"
        :width="150">
        <template #default="{ row, rowIndex }: { row: ConfItem, rowIndex: number }">
          <!-- 编辑/新增状态下不显示操作按钮（已移至当前值列） -->
          <template v-if="isAddingRow && rowIndex === 0 || editingRowKey === row[rowKey as keyof ConfItem]">
            --
          </template>
          <template v-else-if="row.flag_readonly !== 1 || row.level_name === levelName">
            <BkButton
              v-if="row.flag_readonly !== 1"
              class="mr-16"
              text
              theme="primary"
              @click="handleStartEdit(row)">
              {{ t('编辑') }}
            </BkButton>
            <BkButton
              v-if="row.level_name === levelName"
              text
              theme="primary"
              @click="handleShowRestoreInfoBox(row)">
              {{ t('恢复默认') }}
            </BkButton>
          </template>
          <template v-else> -- </template>
        </template>
      </TableColumn>
    </DbTable>

    <!-- 批量编辑侧滑 -->
    <BatchEditSideslider
      v-model:is-show="batchEditConfig.isShow"
      :cluster="cluster"
      :conf-type="confType"
      :data="selectedRows"
      :version="version"
      @saved="handleBatchEditSaved" />
  </BkLoading>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import _ from 'lodash';
  import type { Instance } from 'tippy.js';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import {
    getConfigNames,
    getLevelConfig,
    recoverDefaultConfigItem,
    updateBusinessConfig,
    validateConfItems,
  } from '@services/source/configs';

  import { useGlobalBizs } from '@stores';

  import type { ClusterTypes } from '@common/const';
  import { dbTippy } from '@common/tippy';

  import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import ValueEditor from '@views/db-configure-new/components/ValueEditor.vue';

  import { messageSuccess } from '@utils';

  import BatchEditSideslider from './BatchEditSideslider.vue';

  type LevelConfigResult = ServiceReturnType<typeof getLevelConfig>;

  export type ConfItem = LevelConfigResult['conf_items'][number];

  export interface Props {
    cluster: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
    };
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
    levelValue?: number | string;
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

  const emit = defineEmits<(e: 'change') => void>();

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const saveLoading = ref(false);
  const allConfItems = ref<ConfItem[]>([]);
  const originConfItems = ref<ConfItem[]>([]);
  const availableParams = ref<ConfItem[]>([]);
  // 本地新增但尚未被服务端数据刷新覆盖的项（追加到列表末尾，不破坏原始排序）
  const pendingAddedItems = ref<ConfItem[]>([]);

  // 行唯一标识字段
  const rowKeyField = computed(() => props.rowKey as keyof ConfItem);

  // 参数搜索
  const paramSearchValue = ref<Record<string, any>>({});
  const paramQuickSearchData = [
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

  // 表格列筛选
  const filterValue = ref<Record<string, string>>({});
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

  // 仅显示自定义
  const showCustomOnly = ref(false);

  /** 重置编辑状态 */
  const resetEditingState = () => {
    editingRowKey.value = '';
    editingValue.value = '';
    editingOriginValue.value = '';
    refreshTable();
  };

  /** 刷新表格数据 */
  const refreshTable = () => {
    paramTableRef.value?.fetchData({}, true);
    setTimeout(() => initDescriptionTippy(), 300);
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
    meta_cluster_type: props.cluster.cluster_type,
    version: props.version,
  }));

  /** 参数数据源函数 */
  const paramDataSource = (params: { limit: number; offset: number }) => {
    // 合并本地新增项（排在前面）+ 服务端数据
    let data = [...pendingAddedItems.value, ...allConfItems.value];

    // 前端搜索过滤
    const filters = paramSearchValue.value;
    if (Object.keys(filters).length > 0) {
      data = data.filter((item) =>
        Object.entries(filters).every(([key, val]) => {
          if (!val) return true;
          if (key === 'need_restart') {
            // need_restart 是多选，值为逗号分隔的字符串如 "1,0"
            const searchValues = String(val).split(',');
            return searchValues.includes(String(item.need_restart));
          }
          const search = String(val).toLowerCase();
          const fieldValue = String((item as Record<string, any>)[key] ?? '').toLowerCase();
          return fieldValue.includes(search);
        }),
      );
    }

    // 列筛选过滤
    const needRestartValue = filterValue.value.need_restart;
    if (needRestartValue) {
      const values = Array.isArray(needRestartValue) ? needRestartValue : [needRestartValue];
      data = data.filter((item) => values.includes(String(item.need_restart)));
    }

    // 仅显示自定义
    if (showCustomOnly.value && !isAddingRow.value) {
      data = data.filter((item) => item.level_name === props.levelName);
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
    return Promise.resolve({
      count: data.length,
      results: data.slice(start, end),
    });
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
      filterAvailableParams(res);
    },
  });

  /**
   * 从全量配置名列表中过滤掉已存在于当前配置的参数，
   * 避免下拉选项中出现可添加但实际已存在的重复项。
   * 在接口返回和点击"添加参数"时均需调用。
   */
  const filterAvailableParams = (allNames: ConfItem[]) => {
    const existNames = new Set(allConfItems.value.map((item) => item.conf_name));
    availableParams.value = allNames.filter((p) => !existNames.has(p.conf_name));
  };

  /** 恢复默认 */
  const { run: runRecoverDefault } = useRequest(recoverDefaultConfigItem, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'));
      fetchLevelConfig(fetchParams.value);
      emit('change');
    },
  });

  // 监听 version 变化重新获取数据
  watch(
    () => props.version,
    (version) => {
      if (version) {
        fetchLevelConfig(fetchParams.value);
        fetchConfigNames({
          conf_type: props.confType,
          meta_cluster_type: props.cluster.cluster_type,
          version: props.version,
        });
      }
    },
    { immediate: true },
  );

  /** 搜索变化 */
  const handleParamSearchChange = () => {
    refreshTable();
  };

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
    // 重新拉取可选参数名并根据当前配置列表过滤（排除已存在项）
    fetchConfigNames({
      conf_type: props.confType,
      meta_cluster_type: props.cluster.cluster_type,
      version: props.version,
    });
  };

  /** 过滤器变化 */
  const handleFilterChange = (val: Record<string, string>) => {
    filterValue.value = val;
    refreshTable();
  };

  /** 数据请求成功后重新初始化 tippy（含分页切换场景） */
  const handleRequestSuccess = () => {
    setTimeout(() => initDescriptionTippy(), 100);
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
  const handleConfirmAdd = async () => {
    if (!newRow.value.conf_name) return;

    const paramInfo = availableParams.value.find((p) => p.conf_name === newRow.value.conf_name);
    if (!paramInfo) return;

    const confValue = newRow.value.conf_value || paramInfo.conf_value || '';

    // 后端校验合法性
    try {
      await validateConfItems([
        {
          conf_name: paramInfo.conf_name,
          op_type: 'add',
          value_allowed: paramInfo.value_allowed,
          value_default: confValue,
          value_type: paramInfo.value_type ?? '',
          value_type_sub: paramInfo.value_type_sub ?? '',
        },
      ]);
    } catch {
      return;
    }

    // 追加到 pending 列表末尾，不破坏原始数据排序
    pendingAddedItems.value.push({
      ...paramInfo,
      conf_value: confValue,
      op_type: 'add',
    });

    saveLoading.value = true;
    try {
      await updateBusinessConfig(buildUpdateParams([{ ...paramInfo, conf_value: confValue, op_type: 'add' }]));
      messageSuccess(t('操作成功'));
      emit('change');
    } finally {
      saveLoading.value = false;
    }
    isAddingRow.value = false;
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
  const handleConfirmEdit = async () => {
    const target = allConfItems.value.find((item) => item[rowKeyField.value] === editingRowKey.value);
    if (target) {
      target.conf_value = editingValue.value;
      target.op_type = 'update';

      // 后端校验合法性
      try {
        await validateConfItems([
          {
            conf_name: target.conf_name,
            op_type: 'update',
            value_allowed: target.value_allowed,
            value_default: editingValue.value,
            value_type: target.value_type ?? '',
            value_type_sub: target.value_type_sub ?? '',
          },
        ]);
      } catch {
        return;
      }

      saveLoading.value = true;
      try {
        await updateBusinessConfig(buildUpdateParams([target]));
        messageSuccess(
          target.level_name === props.levelName ? t('操作成功_参数已修改') : t('操作成功_参数已转为自定义'),
        );
        fetchLevelConfig(fetchParams.value);
        emit('change');
      } finally {
        saveLoading.value = false;
      }
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

  const handleRestoreDefault = () => {
    const targets = selectedRows.value.length > 0 ? selectedRows.value : allConfItems.value;
    const confNames = targets.map((r) => r.conf_name);
    runRecoverDefault({
      bk_biz_id: globalBizsStore.currentBizId,
      conf_file: props.version,
      conf_names: confNames,
      conf_type: props.confType,
      level_name: props.levelName || 'app',
      level_value: String(props.levelValue ?? globalBizsStore.currentBizId),
      meta_cluster_type: props.cluster.cluster_type,
    });
  };

  /** 恢复单行默认 */
  const handleShowRestoreInfoBox = (row: ConfItem) => {
    const originItem = originConfItems.value.find((o) => o.conf_name === row.conf_name);
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确认'),
      content: () =>
        h('div', { class: 'param-restore-content' }, [
          h('p', `${t('参数名')}：${row.conf_name}`),
          h('p', `${t('当前值')}：${row.conf_value} → ${originItem?.value_default ?? '--'}`),
          h('p', t('恢复后该参数重新继承父级配置，随父级配置更新而自动同步')),
        ]),
      contentAlign: 'left',
      extCls: 'param-restore-infobox',
      infoType: 'warning',
      onConfirm() {
        runRecoverDefault({
          bk_biz_id: globalBizsStore.currentBizId,
          conf_file: props.version,
          conf_names: [row.conf_name],
          conf_type: props.confType,
          level_name: props.levelName || 'app',
          level_value: String(props.levelValue ?? globalBizsStore.currentBizId),
          meta_cluster_type: props.cluster.cluster_type,
        });
      },
      title: t('确认恢复为默认值？'),
    });
  };

  /** 是否有变更 */
  const hasChange = () => pendingAddedItems.value.length > 0 || !_.isEqual(allConfItems.value, originConfItems.value);

  /** 回车确认 */
  const handleEnter = (e: KeyboardEvent) => {
    if (e.key === 'Enter') handleConfirmEdit();
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

  onMounted(() => {
    document.addEventListener('keydown', handleEnter);
  });

  onUnmounted(() => {
    document.removeEventListener('keydown', handleEnter);
    tippyInstances.forEach((inst) => inst.destroy());
    tippyInstances.length = 0;
  });

  /** 批量编辑保存成功 */
  const handleBatchEditSaved = () => {
    messageSuccess('保存成功');
    fetchLevelConfig(fetchParams.value);
  };

  defineExpose({
    handleReset,
    hasChange,
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
    gap: 8px;
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

  .value-cell-text {
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

  .param-restore-infobox {
    .param-restore-content {
      padding: 16px 24px;
      background: #fafbfd;
      border-radius: 2px;
      font-size: 13px;
      line-height: 22px;
      color: #63656e;
    }

    p {
      margin-bottom: 6px;

      &:last-child {
        margin-bottom: 0;
        margin-top: 10px;
        padding-top: 10px;
      }
    }
  }
</style>
