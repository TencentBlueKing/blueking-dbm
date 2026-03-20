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
    <BkAlert
      class="mb-16"
      closable
      theme="info"
      :title="
        t(
          '参数的初始值均继承自父级_父级更新默认值时会自动同步_可随时修改参数值_修改后将转为自定义状态_不再随父级更新_同时支持恢复为默认值',
        )
      " />
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
          :title="t('确认批量恢复 n 个参数默认值？', { n: selectedRows.length })"
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
            <BkButton>
              {{ t('恢复默认') }}
            </BkButton>
          </span>
        </BkPopConfirm>
      </div>
      <DbQuickSearch
        v-model="paramSearchValue"
        :data="paramQuickSearchData"
        :placeholder="t('搜索参数名_当前值_约束值_描述_重启生效')"
        style="width: 500px"
        @change="handleParamSearchChange" />
    </div>
    <DbTable
      ref="paramTableRef"
      :data-source="paramDataSource"
      :filter-value="filterValue"
      :fixed-pagination="fixedPagination"
      :row-key="rowKey"
      :selectable="selectable"
      @clear-search="handleParamSearchChange"
      @filter-change="
        (val: Record<string, string>) => {
          filterValue = val;
          refreshTable();
        }
      "
      @selection="handleSelectionChange">
      <TableColumn
        col-key="conf_name"
        :title="t('参数名')"
        :width="200">
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
          </template>
        </template>
      </TableColumn>
      <!-- <TableColumn
        col-key="value_default"
        :title="t('默认值')"
        :width="150">
        <template #default="{ row, rowIndex }">
          <template v-if="rowIndex === 0 && isAddingRow"> -- </template>
          <template v-else>
            {{ row.value_default ?? '--' }}
          </template>
        </template>
      </TableColumn> -->
      <TableColumn
        col-key="conf_value"
        :title="t('当前值')"
        :width="200">
        <template #default="{ row, rowIndex }">
          <template v-if="rowIndex === 0 && isAddingRow">
            <BkInput
              v-model="newRow.conf_value"
              :placeholder="t('请输入')" />
          </template>
          <template v-else-if="editingRowKey === row[rowKey]">
            <div class="inline-edit-cell">
              <BkInput
                v-model="editingValue"
                :placeholder="t('请输入')"
                @enter="handleConfirmEdit" />
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
              <span class="value-cell-text">{{ row.conf_value ?? '--' }}</span>
              <BkTag
                v-if="row.stage"
                theme="warning">
                {{ t('自定义') }}
              </BkTag>
              <DbIcon
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
        :title="t('约束值')"
        :width="150">
        <template #default="{ row, rowIndex }">
          <template v-if="rowIndex === 0 && isAddingRow"> -- </template>
          <template v-else>
            {{ row.value_allowed || '--' }}
          </template>
        </template>
      </TableColumn>
      <TableColumn
        col-key="description"
        ellipsis
        :title="t('描述')"
        :width="150">
        <template #default="{ row, rowIndex }">
          <template v-if="rowIndex === 0 && isAddingRow"> -- </template>
          <template v-else>
            {{ row.description || '--' }}
          </template>
        </template>
      </TableColumn>
      <TableColumn
        col-key="need_restart"
        :filter="needRestartFilter"
        :title="t('重启生效')"
        :width="100">
        <template #default="{ row, rowIndex }">
          <template v-if="rowIndex === 0 && isAddingRow"> -- </template>
          <template v-else>
            <span :class="row.need_restart === 1 ? 'restart-icon-yes' : 'restart-icon-no'">
              <DbIcon :type="row.need_restart === 1 ? 'check-line' : 'close'" />
            </span>
          </template>
        </template>
      </TableColumn>
      <TableColumn
        col-key="operation"
        fixed="right"
        :title="t('操作')"
        :width="200">
        <template #default="{ row, rowIndex }: { row: ConfItem, rowIndex: number }">
          <template v-if="rowIndex === 0 && isAddingRow">
            <BkButton
              class="mr-8"
              text
              theme="primary"
              @click="handleConfirmAdd">
              {{ t('确定') }}
            </BkButton>
            <BkButton
              text
              theme="primary"
              @click="handleCancelAdd">
              {{ t('取消') }}
            </BkButton>
          </template>
          <template v-else-if="editingRowKey === row[rowKey as keyof ConfItem]"> -- </template>
          <template v-else>
            <BkButton
              class="mr-8"
              text
              theme="primary"
              @click="handleStartEdit(row)">
              {{ t('编辑') }}
            </BkButton>
            <BkPopConfirm
              :cancel-text="t('取消')"
              :confirm-text="t('确认恢复')"
              :title="t('确认恢复默认值？')"
              trigger="click"
              :width="275"
              @confirm="handleRestoreRowDefault(row)">
              <template #content>
                <div
                  class="mb-16"
                  style="line-height: 20px">
                  <p class="mb-6">
                    {{ t('参数名称_:_name', { name: row.conf_name }) }}
                  </p>
                  <p>
                    {{ t('恢复后，该参数的值降默认继承父级的值，随父级内容变化') }}
                  </p>
                </div>
              </template>
              <span @click.stop>
                <BkButton
                  text
                  theme="primary">
                  {{ t('恢复默认') }}
                </BkButton>
              </span>
            </BkPopConfirm>
          </template>
        </template>
      </TableColumn>
    </DbTable>

    <!-- 批量编辑弹窗 -->
    <BkDialog
      v-model:is-show="batchEditConfig.isShow"
      :confirm-text="t('确定')"
      :esc-confirm="false"
      :loading="batchEditConfig.loading"
      :title="t('批量编辑')"
      width="640"
      @confirm="handleBatchEditConfirm">
      <div class="batch-edit-content">
        <div class="batch-edit-tip mb-16">
          {{ t('共选中 n 个参数，将批量修改为相同值', { n: selectedRows.length }) }}
        </div>
        <BkForm
          form-type="vertical"
          :model="batchEditConfig">
          <BkFormItem :label="t('新值')">
            <BkInput
              v-model="batchEditConfig.newValue"
              :placeholder="t('请输入')" />
          </BkFormItem>
        </BkForm>
      </div>
    </BkDialog>
  </BkLoading>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import {
    getConfigNames,
    getLevelConfig,
    recoverDefaultConfigItem,
    updateBusinessConfig,
  } from '@services/source/configs';

  import { useGlobalBizs } from '@stores';

  import DbTable from '@components/db-table/IndexNew.vue';

  import { type DiffItem, useDiff } from '@views/db-configure-new/hooks/useDiff';

  type LevelConfigResult = ServiceReturnType<typeof getLevelConfig>;

  export type ConfItem = LevelConfigResult['conf_items'][number];

  export interface Props {
    clusterType: string;
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

  // 行唯一标识字段
  const rowKeyField = computed(() => props.rowKey as keyof ConfItem);

  // 参数搜索
  const paramSearchValue = ref<Record<string, any>>({});
  const paramQuickSearchData = [
    { id: 'conf_name', name: t('参数名'), type: 'input' as const },
    // { id: 'value_default', name: t('默认值'), type: 'input' as const },
    { id: 'conf_value', name: t('当前值'), type: 'input' as const },
    { id: 'value_allowed', name: t('约束值'), type: 'input' as const },
    { id: 'description', name: t('描述'), type: 'input' as const },
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
  const selectedRows = ref<ConfItem[]>([]);

  // 表格列筛选
  const filterValue = ref<Record<string, string>>({});
  const needRestartFilter = {
    name: t('重启生效'),
    props: {
      list: [
        { label: t('是'), value: '1' },
        { label: t('否'), value: '0' },
      ],
    },
    showConfirmAndReset: true,
    type: 'multiple' as const,
  };

  // 新增行
  const isAddingRow = ref(false);
  const newRow = ref({
    conf_name: '',
    conf_value: '',
  });

  // 行内编辑
  const editingRowKey = ref('');
  const editingValue = ref('');
  const editingOriginValue = ref('');

  // 批量编辑弹窗
  const batchEditConfig = reactive({
    isShow: false,
    loading: false,
    newValue: '',
  });

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
    meta_cluster_type: props.clusterType,
    version: props.version,
  }));

  /** 参数数据源函数 */
  const paramDataSource = (params: { limit: number; offset: number }) => {
    let data = [...allConfItems.value];

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

    // 如果正在新增行，在首行插入空行
    if (isAddingRow.value) {
      const emptyRow = {
        conf_name: '',
        conf_value: '',
        description: '',
        flag_disable: 0,
        flag_locked: 0,
        need_restart: 0,
        op_type: 'add',
        value_allowed: '',
        value_default: '',
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
      nextTick(() => {
        paramTableRef.value?.fetchData({}, true);
      });
    },
  });

  /** 获取可选参数名 */
  const { run: fetchConfigNames } = useRequest(getConfigNames, {
    manual: true,
    onSuccess(res) {
      availableParams.value = res;
    },
  });

  /** 恢复默认 - 全部或选中行 */
  const { run: runRecoverDefault } = useRequest(recoverDefaultConfigItem, {
    manual: true,
    onSuccess() {
      // 恢复成功后重新获取数据
      loading.value = true;
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
          meta_cluster_type: props.clusterType,
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

  /** 添加参数 */
  const handleAddParam = () => {
    isAddingRow.value = true;
    newRow.value = { conf_name: '', conf_value: '' };
    refreshTable();
  };

  /** 确认新增 */
  const handleConfirmAdd = () => {
    if (!newRow.value.conf_name) return;

    const paramInfo = availableParams.value.find((p) => p.conf_name === newRow.value.conf_name);
    if (paramInfo) {
      allConfItems.value.unshift({
        ...paramInfo,
        conf_value: newRow.value.conf_value || paramInfo.conf_value || '',
        op_type: 'add',
      });
    }
    isAddingRow.value = false;
    refreshTable();
    emit('change');
  };

  /** 取消新增 */
  const handleCancelAdd = () => {
    isAddingRow.value = false;
    refreshTable();
  };

  /** 开始行内编辑 */
  const handleStartEdit = (row: ConfItem) => {
    editingRowKey.value = row[rowKeyField.value] as any;
    editingValue.value = row.conf_value ?? '';
    editingOriginValue.value = row.conf_value ?? '';
  };

  /** 确认编辑 */
  const handleConfirmEdit = async () => {
    const target = allConfItems.value.find((item) => item[rowKeyField.value] === editingRowKey.value);
    if (target) {
      target.conf_value = editingValue.value;
      target.op_type = 'update';

      saveLoading.value = true;
      try {
        await updateBusinessConfig(buildUpdateParams([target]));
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
    batchEditConfig.newValue = '';
  };

  /** 批量编辑确认 */
  const handleBatchEditConfirm = async () => {
    if (!batchEditConfig.newValue) return;

    batchEditConfig.loading = true;
    try {
      const confItems = selectedRows.value.map((row) => ({
        ...row,
        conf_value: batchEditConfig.newValue,
        op_type: 'update',
      }));

      await updateBusinessConfig(buildUpdateParams(confItems));

      batchEditConfig.isShow = false;
      refreshTable();
      emit('change');
    } finally {
      batchEditConfig.loading = false;
    }
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
      meta_cluster_type: props.clusterType,
    });
  };

  /** 恢复单行默认 */
  const handleRestoreRowDefault = (row: ConfItem) => {
    runRecoverDefault({
      bk_biz_id: globalBizsStore.currentBizId,
      conf_file: props.version,
      conf_names: [row.conf_name],
      conf_type: props.confType,
      level_name: props.levelName || 'app',
      level_value: String(props.levelValue ?? globalBizsStore.currentBizId),
      meta_cluster_type: props.clusterType,
    });
  };

  /** 是否有变更 */
  const hasChange = () => !_.isEqual(allConfItems.value, originConfItems.value);

  /** 重置 */
  const handleReset = () => {
    allConfItems.value = [];
    originConfItems.value = [];
    availableParams.value = [];
  };

  /** 绑定参数配置 — 供父组件调用 */
  const bindConfigParameters = () => {
    const { data } = useDiff(allConfItems.value, originConfItems.value);
    const confItems = data
      .map((item: DiffItem) => {
        const diffData = item.status === 'delete' ? item.before : item.after;
        if (!diffData) return null;
        return Object.assign(diffData, { op_type: item.status === 'delete' ? 'remove' : 'update' });
      })
      .filter((item): item is ConfItem => item !== null);

    return updateBusinessConfig(buildUpdateParams(confItems));
  };

  defineExpose({
    bindConfigParameters,
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
</style>
