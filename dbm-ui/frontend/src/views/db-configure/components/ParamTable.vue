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
  <ApplyPermissionCatch>
    <BkLoading :loading="loading">
      <div class="param-operations mb-16">
        <div>
          <AuthTemplate
            :action-id="actionId"
            class="param-operations-left"
            :permission="permissions[actionId]"
            :resource="resourceId">
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
            <BkButton
              v-bk-tooltips="{
                content: t('请勾选参数'),
                disabled: selectedRows.length > 0,
              }"
              :disabled="selectedRows.length === 0"
              @click="handleShowBatchRestoreInfoBox">
              {{ t('批量处理自定义') }}
            </BkButton>
          </AuthTemplate>
        </div>
        <div class="param-operations-right">
          <BkCheckbox
            v-model="showCustomOnly"
            @change="refreshTable">
            {{ t('仅显示自定义') }}
          </BkCheckbox>
          <DbQuickSearch
            v-model="searchValue"
            :data="quickSearchData"
            :placeholder="t('搜索参数名_当前值_允许值_重启生效')"
            style="width: 500px"
            @change="refreshTable" />
        </div>
      </div>
      <DbTable
        ref="paramTableRef"
        :data-source="paramDataSource"
        :default-limit="100"
        :disable-select-method="disableSelectMethod"
        :filter-value="searchValue"
        :fixed-pagination="fixedPagination"
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
                <BkTag
                  v-if="row.level_name === levelName || row.op_type === 'add'"
                  size="small"
                  theme="warning">
                  {{ t('自定义') }}
                </BkTag>
                <AuthTemplate
                  v-if="row.flag_readonly !== 1"
                  :action-id="actionId"
                  :permission="permissions[actionId]"
                  :resource="resourceId">
                  <template #default="{ permission }">
                    <DbIcon
                      v-if="permission"
                      v-bk-tooltips="{ content: t('编辑参数') }"
                      class="value-cell-edit"
                      type="bk-dbm-icon db-icon-edit"
                      @click="handleStartEdit(row)" />
                  </template>
                </AuthTemplate>
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
          col-key="operation"
          fixed="right"
          :title="t('操作')"
          :width="150">
          <template #default="{ row, rowIndex }: { row: ConfItem, rowIndex: number }">
            <!-- 编辑/新增状态下不显示操作按钮（已移至当前值列） -->
            <template v-if="(isAddingRow && rowIndex === 0) || editingRowKey === String(row[rowKeyField])">
              --
            </template>
            <template v-else-if="row.flag_readonly !== 1 || row.level_name === levelName">
              <!-- 编辑按钮：非只读参数可编辑 -->
              <AuthButton
                v-if="row.flag_readonly !== 1"
                :action-id="actionId"
                class="mr-16"
                :permission="permissions[actionId]"
                :resource="resourceId"
                text
                theme="primary"
                @click="handleStartEdit(row)">
                {{ t('编辑') }}
              </AuthButton>
              <!-- 恢复按钮：自定义参数（level_name === levelName 即「自定义」）可恢复 -->
              <AuthButton
                v-if="row.level_name === levelName && row.flag_readonly !== 1"
                :action-id="actionId"
                :permission="permissions[actionId]"
                :resource="resourceId"
                text
                theme="primary"
                @click="handleShowRestoreInfoBox(row)">
                {{ isCancelUseParam(row) ? t('取消使用') : t('恢复默认') }}
              </AuthButton>
            </template>
            <template v-else> -- </template>
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
  </ApplyPermissionCatch>
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

  import { ClusterTypes, ConfLevels, DBTypes } from '@common/const';
  import { clusterTypeInfos } from '@common/const/clusterTypesInfos';
  import { dbTippy } from '@common/tippy';

  import ApplyPermissionCatch from '@components/apply-permission/Catch.vue';
  import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import BatchEditSideslider from '@views/db-configure/components/BatchEditSideslider.vue';
  import ValueEditor from '@views/db-configure/components/ValueEditor.vue';

  import { messageSuccess } from '@utils';

  type LevelConfigResult = ServiceReturnType<typeof getLevelConfig>;

  export type ConfItem = LevelConfigResult['conf_items'][number];

  export interface Props {
    /** 集群 ID（用于集群级权限 Resource ID） */
    clusterId?: number | string;
    clusterType?: ClusterTypes;
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
    namespace: string;
    /** 行唯一标识字段 */
    rowKey?: string;
    /** 是否支持行选择（批量编辑） */
    selectable?: boolean;
    version: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    clusterId: undefined,
    configName: '',
    fixedPagination: false,
    levelInfo: undefined,
    levelName: 'app',
    levelValue: window.PROJECT_CONFIG.BIZ_ID,
    rowKey: 'conf_name',
    selectable: false,
  });

  const emit = defineEmits<(e: 'change') => void>();

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const route = useRoute();

  const saveLoading = ref(false);
  // 所有配置项
  const allConfItems = ref<ConfItem[]>([]);
  // 原始配置项
  const originConfItems = ref<ConfItem[]>([]);
  // 可添加的参数
  const availableParams = ref<ConfItem[]>([]);
  // 权限
  const permissions = ref<ServiceReturnType<typeof getLevelConfig>['permission']>({
    dbconfig_edit: false,
  });

  // 数据库类型对应的参数配置编辑权限 actionId
  const dbconfigEditActionIdMap: Record<DBTypes, string> = {
    [DBTypes.DORIS]: 'doris_dbconfig_edit',
    [DBTypes.ES]: 'es_dbconfig_edit',
    [DBTypes.HDFS]: 'hdfs_dbconfig_edit',
    [DBTypes.INFLUXDB]: 'influxdb_dbconfig_edit',
    [DBTypes.KAFKA]: 'kafka_dbconfig_edit',
    [DBTypes.MONGODB]: 'mongodb_dbconfig_edit',
    [DBTypes.MYSQL]: 'mysql_dbconfig_edit',
    [DBTypes.ORACLE]: 'oracle_dbconfig_edit',
    [DBTypes.PULSAR]: 'pulsar_dbconfig_edit',
    [DBTypes.REDIS]: 'redis_dbconfig_edit',
    [DBTypes.RIAK]: 'riak_dbconfig_edit',
    [DBTypes.SQLSERVER]: 'sqlserver_dbconfig_edit',
    [DBTypes.TENDBCLUSTER]: 'tendbcluster_dbconfig_edit',
  };

  /** 根据层级和集群类型计算权限 actionId */
  const actionId = computed(() => {
    if (props.levelName === 'cluster') {
      const dbType = clusterTypeInfos[props.clusterType || (route.params.clusterType as ClusterTypes)]?.dbType;
      return dbconfigEditActionIdMap[dbType];
    }
    return 'dbconfig_edit';
  });

  /** 根据层级计算权限 resourceId */
  const resourceId = computed(() => {
    if (props.levelName === 'cluster') {
      return props.clusterId;
    }
    return clusterTypeInfos[props.clusterType || (route.params.clusterType as ClusterTypes)]?.dbType;
  });

  // 行唯一标识字段
  const rowKeyField = computed(() => props.rowKey as keyof ConfItem);

  // 参数搜索
  const searchValue = ref<Record<string, any>>({});
  const quickSearchData = [
    { id: 'conf_name', name: t('参数名'), type: 'input' as const },
    // { id: 'value_default', name: t('默认值'), type: 'input' as const },
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

  // 仅显示自定义
  const showCustomOnly = ref(false);

  /**
   * 判断该参数是否为"取消使用"形态。
   *
   * 规则：当行的"上一级配置"层级为 PLAT（平台），且 flag_visible === 0（业务默认不可见）时，
   * 该参数是用户通过"添加参数"加入的；其语义不是"恢复为父级值"，
   * 而是"从当前配置中清除"，因此按钮文案与确认文案均需切换。
   *
   * 注意：判定来源是 up_level_value.level_name（上一级层级），而非行自身的 level_name；
   * 后端在该字段中返回参数所继承的上一级配置层级。
   */
  const isCancelUseParam = (row: ConfItem) =>
    (row.level_name !== ConfLevels.PLAT && !row.up_level_value) || // row.up_level_value 返回null
    (row.level_name !== ConfLevels.PLAT && row.up_level_value && Object.keys(row.up_level_value).length === 0); // row.up_level_value 返回空对象{}

  /** 重置编辑状态 */
  const resetEditingState = () => {
    editingRowKey.value = '';
    editingValue.value = '';
    editingOriginValue.value = '';
    refreshTable();
  };

  /** 检测单元格文本是否溢出（用于控制 tooltip 仅在溢出时显示） */
  const handleCellMouseEnter = (e: MouseEvent, row: ConfItem) => {
    const el = e.target as HTMLElement;
    overflowStates.value[row.conf_name] = el.scrollWidth > el.clientWidth;
  };

  /** 仅刷新表格数据（不会请求接口） */
  const refreshTable = () => {
    paramTableRef.value?.fetchData({}, true);
  };

  /** 批量编辑保存后的处理 */
  const handleBatchEditSaved = () => {
    fetchLevelConfig(fetchParams.value); // 重新拉取配置列表（并且刷新表格）
    emit('change');
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
    level_name: (props.levelName as any) ?? 'app',
    level_value: props.levelValue ?? globalBizsStore.currentBizId,
    meta_cluster_type: props.namespace,
    version: props.version,
  }));

  /** 参数列表数据源 */
  const paramDataSource = (params: { limit: number; offset: number }) => {
    let data = [...allConfItems.value];

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

    if (selectedRows.value.length) {
      // 更新 selectedRows 中对应项的属性，保持响应式
      selectedRows.value.forEach((row) => {
        const latestItem = data.find((item) => item.conf_name === row.conf_name);
        if (latestItem) {
          Object.assign(row, latestItem);
        }
      });
    }

    const start = params.offset;
    const end = start + params.limit;
    const result = {
      count: data.length,
      results: data.slice(start, end),
    };

    return Promise.resolve(result);
  };

  /** 拉取配置列表（并且刷新表格） */
  const { loading, run: fetchLevelConfig } = useRequest(getLevelConfig, {
    manual: true,
    onSuccess(res) {
      permissions.value = res.permission;
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
      messageSuccess(t('操作成功，参数已恢复为默认值'));
      fetchLevelConfig(fetchParams.value);
      emit('change');
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
          version: props.version,
        });
      }
    },
    { immediate: true },
  );

  /** 选中变化 */
  const handleSelectionChange = (_keys: string[], list: ConfItem[]) => {
    selectedRows.value = list;
  };

  /** 只读项禁用选择，hover 提示 */
  const disableSelectMethod = (row: ConfItem) => {
    if (row.flag_readonly === 1) {
      return t('该参数不允许业务编辑');
    }
    return false;
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
      meta_cluster_type: props.namespace,
      version: props.version,
    });
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

    allConfItems.value.unshift({
      ...paramInfo,
      conf_value: confValue,
      level_name: props.levelName,
      op_type: 'add',
    });

    saveLoading.value = true;
    try {
      await updateBusinessConfig(buildUpdateParams([{ ...paramInfo, conf_value: confValue, op_type: 'add' }]));
      messageSuccess(t('操作成功'));
      refreshTable(); // 仅刷新表格
      emit('change');
    } finally {
      saveLoading.value = false;
    }
    isAddingRow.value = false;
  };

  /** 取消新增 */
  const handleCancelAdd = () => {
    isAddingRow.value = false;
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
    editingOriginValue.value = row.conf_value ?? '';
    // 加密参数不带入原值，由用户输入新值
    if (row.flag_encrypt === 1) {
      editingValue.value = '';
    } else {
      editingValue.value = row.conf_value ?? '';
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
        fetchLevelConfig(fetchParams.value); // 重新拉取配置列表（并且刷新表格）
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

  /**
   * 批量恢复默认值 InfoBox
   *
   * 规则:
   * - N: 用户勾选总数
   * - Y: 自动跳过数（只读 或 当前已是默认值即未自定义）
   * - X: 实际生效数 = N - Y
   * - X = 0 时确定按钮置灰，提示"选中的参数均不可恢复"
   * - Y > 0 时显示 infobar 提醒
   */
  const handleShowBatchRestoreInfoBox = () => {
    const selected = selectedRows.value;
    const total = selected.length;

    // 判断是否可恢复：
    // 1) 当前层级自定义参数 且 非只读，或
    // 2) "取消使用"型参数（level_name === PLAT 且 flag_visible === 0）且非只读
    const isRestorable = (item: ConfItem) =>
      item.flag_readonly !== 1 && (item.level_name === props.levelName || isCancelUseParam(item));

    const restorableItems = selected.filter(isRestorable);

    // 按 isCancelUseParam 分组：restore(恢复默认) / cancel_use(取消使用)
    const restoreItems = restorableItems.filter((item) => !isCancelUseParam(item));
    const cancelUseItems = restorableItems.filter((item) => isCancelUseParam(item));

    const skipCount = total - restorableItems.length;
    const restoreCount = restoreItems.length;
    const cancelUseCount = cancelUseItems.length;

    InfoBox({
      // 用 beforeClose 拦截 X=0 时的"确定"操作
      beforeClose(action: string) {
        if (action === 'confirm') {
          if (restorableItems.length === 0) {
            return false;
          }
          runRecoverDefault({
            bk_biz_id: globalBizsStore.currentBizId,
            conf_file: props.version,
            conf_names: restorableItems.map((r) => r.conf_name),
            conf_type: props.confType,
            level_name: props.levelName || 'app',
            level_value: String(props.levelValue),
            meta_cluster_type: props.namespace,
          });
        }
        return true;
      },
      cancelText: t('取消'),
      confirmText: t('确定'),
      content: () =>
        h('div', { class: 'param-batch-custom-content' }, [
          // 跳过提示
          skipCount > 0 &&
            h('div', { class: 'custom-infobar' }, [
              h('i', { class: 'infobar-icon bk-dbm-icon db-icon-attention' }),
              h('span', [
                t('已自动过滤 '),
                h('strong', { style: { color: '#ff9c01' } }, skipCount),
                t(' 个不适用的参数（只读或已是默认值），不受本次操作影响。'),
              ]),
            ]),
          // 描述文本：根据两组数量动态决定文案
          (() => {
            if (restoreCount > 0 && cancelUseCount > 0) {
              return h('div', { class: 'custom-desc' }, [
                t('将恢复 '),
                h('strong', restoreCount),
                t(' 个参数为默认值，并取消使用 '),
                h('strong', cancelUseCount),
                t(' 个主动添加的参数。'),
              ]);
            }
            if (restoreCount > 0) {
              return h('div', { class: 'custom-desc' }, [
                t('将恢复 '),
                h('strong', restoreCount),
                t(' 个参数为默认值。'),
              ]);
            }
            if (cancelUseCount > 0) {
              return h('div', { class: 'custom-desc' }, [
                t('将取消使用 '),
                h('strong', cancelUseCount),
                t(' 个主动添加的参数。'),
              ]);
            }
            return null;
          })(),
          // 分组1：恢复默认
          restoreCount > 0 &&
            h('div', { class: 'custom-section' }, [
              h('div', { class: 'section-header' }, [
                h('span', t('恢复默认')),
                h('span', { class: 'ml-4' }, ['( ', h('strong', restoreCount), ' )']),
              ]),
              h(
                'div',
                { class: 'section-list' },
                restoreItems.map((item) => {
                  const oldVal = item.flag_encrypt === 1 ? '******' : (item.conf_value ?? '--');
                  const newVal = item.up_level_value?.conf_value ?? '--';
                  return h('div', { class: 'affect-item', key: item.conf_name }, [
                    h('span', { class: 'affect-name' }, item.conf_name),
                    h('span', { class: 'affect-value' }, [
                      h(
                        'span',
                        {
                          class: 'value-old',
                          title: String(oldVal),
                        },
                        String(oldVal === '' ? t('空字符串') : oldVal),
                      ),
                      h('span', { class: 'value-arrow' }, '→'),
                      h(
                        'span',
                        {
                          class: 'value-new',
                          title: String(newVal),
                        },
                        String(newVal === '' ? t('空字符串') : newVal),
                      ),
                    ]),
                  ]);
                }),
              ),
            ]),
          // 分组2：取消使用
          cancelUseCount > 0 &&
            h('div', { class: 'custom-section' }, [
              h('div', { class: 'section-header' }, [
                h('span', t('取消使用')),
                h('span', { class: 'ml-4' }, ['( ', h('strong', cancelUseCount), ' )']),
              ]),
              h(
                'div',
                { class: 'section-list' },
                cancelUseItems.map((item) =>
                  h('div', { class: 'affect-item' }, [h('span', { class: 'affect-name' }, item.conf_name)]),
                ),
              ),
            ]),
          // 空状态
          restorableItems.length === 0 && h('div', { class: 'affect-empty' }, t('当前已无可处理的参数')),
        ]),
      contentAlign: 'left',
      extCls:
        restorableItems.length === 0 ? 'param-batch-custom-infobox is-confirm-disabled' : 'param-batch-custom-infobox',
      headerAlign: 'left',
      title: () =>
        h('div', { class: 'custom-title' }, [
          h('span', { class: 'custom-title-text' }, t('确认批量处理自定义参数')),
          h('span', { class: 'custom-sub-title' }, [
            t('已选'),
            h('span', { class: 'sub-title-num' }, String(total)),
            t('个参数'),
          ]),
        ]),
      width: 640,
    });
  };

  /** 恢复单行默认 / 取消使用 */
  const handleShowRestoreInfoBox = (row: ConfItem) => {
    const isCancel = isCancelUseParam(row);
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确认'),
      content: () =>
        h(
          'div',
          { class: 'param-restore-content' },
          isCancel
            ? [
                h('p', `${t('参数名')}：${row.conf_name}`),
                h('p', t('该参数将从当前配置中清除；如需再次使用，可通过【添加参数】重新加入。')),
              ]
            : [
                h('p', `${t('参数名')}：${row.conf_name}`),
                h('p', `${t('当前值')}：${row.conf_value} → ${row.up_level_value?.conf_value ?? '--'}`),
                h('p', t('恢复后该参数重新继承父级配置，\n随父级配置更新而自动同步')),
              ],
        ),
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
          level_value: String(props.levelValue),
          meta_cluster_type: props.namespace,
        });
      },
      title: isCancel ? t('确认不再使用该参数？') : t('确认恢复为默认值？'),
    });
  };

  /** 是否有变更 */
  const hasChange = () => !_.isEqual(allConfItems.value, originConfItems.value);

  /** 重置 */
  const handleReset = () => {
    allConfItems.value = [];
    originConfItems.value = [];
    availableParams.value = [];
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
    height: 26px;
    min-width: 26px;
    padding: 0;
    font-size: 16px;
    align-items: center;
    justify-content: center;
  }

  .inline-edit-cell-cancel {
    display: inline-flex;
    height: 26px;
    min-width: 26px;
    padding: 0;
    font-size: 16px;
    align-items: center;
    justify-content: center;
  }

  .value-cell {
    display: inline-flex;
    align-items: center;
    gap: 4px;
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
    color: #63656e;
    cursor: pointer;
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
    color: #c4c6cc;
    cursor: pointer;

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

  .param-restore-infobox {
    .param-restore-content {
      padding: 16px 24px;
      font-size: 13px;
      line-height: 22px;
      color: #63656e;
      background: #fafbfd;
      border-radius: 2px;
    }

    p {
      margin-bottom: 6px;

      &:last-child {
        padding-top: 10px;
        margin-top: 10px;
        margin-bottom: 0;
      }
    }
  }

  .param-batch-custom-infobox {
    .bk-infobox-title {
      margin-top: 0;
    }

    .custom-title {
      display: flex;
      align-items: center;
      justify-content: flex-start;
      gap: 8px;

      .custom-title-text {
        font-size: 20px;
        font-weight: 400;
        line-height: 28px;
        color: #313238;
      }
    }

    .custom-sub-title {
      display: inline-flex;
      align-items: center;
      padding: 0 8px;
      font-size: 12px;
      line-height: 22px;
      color: #63656e;
      background: #f0f1f5;
      border-radius: 2px;

      .sub-title-num {
        padding: 0 4px;
        font-weight: 700;
        color: #3a84ff;
      }
    }

    &.is-confirm-disabled {
      .bk-infobox-footer .bk-button-primary {
        color: #fff !important;
        pointer-events: none;
        cursor: not-allowed;
        background-color: #dcdee5 !important;
        border-color: #dcdee5 !important;
        opacity: 100% !important;
      }
    }

    .param-batch-custom-content {
      font-size: 14px;
      line-height: 22px;
      color: #63656e;

      .custom-desc {
        margin-bottom: 12px;
      }

      .custom-infobar {
        display: flex;
        padding: 8px 12px;
        margin-bottom: 16px;
        font-size: 12px;
        line-height: 20px;
        color: #63656e;
        background: #fff4e2;
        border: 1px solid #ffdfac;
        border-radius: 2px;
        align-items: center;

        .infobar-icon {
          margin-right: 8px;
          font-size: 14px;
          color: #ff9c01;
        }
      }

      .custom-section {
        margin-bottom: 12px;
        border: 1px solid #f0f1f5;
        border-radius: 2px;

        &:last-child {
          margin-bottom: 0;
        }
      }

      .section-header {
        display: flex;
        align-items: center;
        padding: 8px 16px;
        font-size: 12px;
        line-height: 20px;
        background: #f5f7fa;
        border-bottom: 1px solid #f0f1f5;
      }

      .section-list {
        max-height: 182px;
        overflow-y: auto;
      }

      .affect-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 16px;
        font-size: 12px;
        line-height: 20px;
        border-bottom: 1px solid #f0f1f5;

        &:last-child {
          border-bottom: none;
        }

        .affect-name {
          flex-shrink: 0;
          margin-right: 16px;
          font-family: 'Roboto Mono', Consolas, Menlo, monospace;
          color: #313238;
        }

        .affect-value {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: flex-end;
          overflow: hidden;
          color: #979ba5;

          .value-old,
          .value-new {
            max-width: 220px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }

          .value-old {
            color: #ff9c01;
          }

          .value-new {
            font-weight: 700;
            color: #3a84ff;
          }

          .value-arrow {
            margin: 0 8px;
            color: #c4c6cc;
          }
        }
      }

      .affect-empty {
        padding: 24px 16px;
        font-size: 12px;
        color: #c4c6cc;
        text-align: center;
      }
    }
  }
</style>
