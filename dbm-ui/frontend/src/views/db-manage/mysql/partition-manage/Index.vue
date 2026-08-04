<template>
  <div class="spider-manage-paritition-page">
    <div class="header-action mb-16">
      <AuthButton
        action-id="mysql_partition_manage"
        class="w-88"
        theme="primary"
        @click="handleCreate">
        {{ t('新建策略') }}
      </AuthButton>
      <AuthButton
        action-id="mysql_partition_manage"
        class="w-88 ml-8"
        @click="handleShowExcelImport">
        {{ t('导入策略') }}
      </AuthButton>
      <!-- 导出下拉 -->
      <BkDropdown
        class="batch-operation ml-8"
        :popover-options="{
          clickContentAutoHide: true,
          boundary: 'body',
          renderDirective: 'show',
        }"
        trigger="click">
        <template #default="{ popoverShow }">
          <BkButton>
            {{ t('导出') }}
            <DbIcon
              class="batch-operation-icon ml-4"
              :class="[{ 'batch-operation-icon-active': popoverShow }]"
              type="up-big " />
          </BkButton>
        </template>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem>
              <BkButton
                text
                @click="handleExportAll">
                {{ t('导出所有') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                :disabled="disabled"
                text
                @click="handleExportSelected">
                {{ t('导出已选') }}
              </BkButton>
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <!-- 批量操作下拉 -->
      <BkDropdown
        v-bk-tooltips="{
          disabled: !disabled,
          content: t('请选择策略'),
        }"
        class="batch-operation ml-8"
        :popover-options="{
          clickContentAutoHide: true,
          boundary: 'body',
          renderDirective: 'show',
          disableOutsideClick: disabled,
        }"
        trigger="click">
        <template #default="{ popoverShow }">
          <BkButton :disabled="disabled">
            {{ t('批量操作') }}
            <DbIcon
              class="batch-operation-icon ml-4"
              :class="[{ 'batch-operation-icon-active': popoverShow }]"
              type="up-big " />
          </BkButton>
        </template>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem>
              <BkButton
                :disabled="allDisabledSelected"
                text
                @click="handleBatchExecute">
                {{ t('批量执行') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                :disabled="allEnabledSelected"
                text
                @click="handleBatchEnable">
                {{ t('批量启用') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                :disabled="allDisabledSelected"
                text
                @click="handleBatchDisable">
                {{ t('批量禁用') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                text
                theme="danger"
                @click="handleBatchRemove">
                {{ t('批量删除') }}
              </BkButton>
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <DbQuickSearch
        v-model="searchValue"
        :data="serachData"
        parse-url
        :placeholder="t('输入关键字或选择条件搜索')"
        style="width: 500px; margin-left: auto"
        @change="handleSearch" />
    </div>
    <DbTable
      ref="tableRef"
      :bk-ui-settings="tableSetting"
      class="partition-table"
      :data-source="dataSource"
      releate-url-query
      :row-class="getRowClass"
      row-key="id"
      selectable
      @bk-ui-settings-change="updateTableSettings"
      @clear-search="handleClearSearch"
      @selection="handleTableSelection">
      <TableColumn
        col-key="id"
        fixed="left"
        title="ID"
        :width="100">
        <template #default="{ row }: { row: PartitionModel }">
          <AuthButton
            action-id="mysql_partition_manage"
            :permission="row.permission.mysql_partition_manage"
            :resource="row.cluster_id"
            text
            theme="primary"
            @click="handleEdit(row)">
            {{ row.id }}
          </AuthButton>
          <BkTag
            v-if="row.isNew"
            class="ml-4"
            size="small"
            theme="success">
            NEW
          </BkTag>
          <BkTag
            v-if="row.isOffline"
            class="ml-4"
            size="small">
            {{ t('已禁用') }}
          </BkTag>
        </template>
      </TableColumn>
      <TableColumn
        col-key="immute_domain"
        :title="t('集群')"
        :width="240">
        <template #default="{ row }: { row: PartitionModel }">
          {{ row.immute_domain || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="dblike"
        :title="t('DB 名')"
        :width="120">
        <template #default="{ row }: { row: PartitionModel }">
          <span v-if="!row.dblike">--</span>
          <BkTag>{{ row.dblike }}</BkTag>
        </template>
      </TableColumn>
      <TableColumn
        col-key="tblike"
        :title="t('表名')"
        :width="160">
        <template #default="{ row }: { row: PartitionModel }">
          <span v-if="!row.tblike">--</span>
          <BkTag>{{ row.tblike }}</BkTag>
        </template>
      </TableColumn>
      <TableColumn
        col-key="partition_column"
        :title="t('分区字段')"
        :width="140">
        <template #default="{ row }: { row: PartitionModel }">
          {{ row.partition_column || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="partition_column_type"
        :title="t('字段类型')"
        :width="140">
        <template #default="{ row }: { row: PartitionModel }">
          {{ row.partition_column_type || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="partition_time_interval"
        :title="t('分区间隔（天）')"
        :width="140">
        <template #default="{ row }: { row: PartitionModel }">
          {{ row.partition_time_interval || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="expire_time"
        :title="t('数据过期时间（天）')"
        :width="140">
        <template #default="{ row }: { row: PartitionModel }">
          {{ row.expire_time || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="status"
        :title="t('最近执行状态')"
        :width="180">
        <template #default="{ row }: { row: PartitionModel }">
          <DbIcon
            style="vertical-align: middle"
            svg
            :type="row.statusIcon" />
          <span class="ml-4">{{ row.statusText }}</span>
          <DbIcon
            v-if="row.status === PartitionModel.STATUS_FAILED"
            v-bk-tooltips="t('查看失败日志')"
            class="ml-4"
            style="vertical-align: middle; cursor: pointer; color: #3a84ff"
            type="bk-dbm-icon db-icon-form"
            @click="handleShowFailLog(row)" />
        </template>
      </TableColumn>
      <TableColumn
        col-key="execute_time"
        :title="t('最近执行时间')"
        :width="240">
        <template #default="{ row }: { row: PartitionModel }">
          {{ utcDisplayTime(row.execute_time) || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="operation"
        fixed="right"
        :title="t('操作')"
        :width="130">
        <template #default="{ row }: { row: PartitionModel }">
          <!-- 执行按钮 -->
          <AuthButton
            action-id="mysql_partition_manage"
            :disabled="row.isOffline"
            :loading="executeLoadingMap[row.id]"
            :permission="row.permission.mysql_partition_manage"
            :resource="row.cluster_id"
            text
            theme="primary"
            @click="handleExecute(row)">
            {{ t('执行') }}
          </AuthButton>
          <!-- 编辑按钮 -->
          <AuthButton
            action-id="mysql_partition_manage"
            class="ml-8"
            :permission="row.permission.mysql_partition_manage"
            :resource="row.cluster_id"
            text
            theme="primary"
            @click="handleEdit(row)">
            {{ t('编辑') }}
          </AuthButton>
          <!-- 禁用/启用按钮 -->
          <AuthButton
            v-if="row.isOnline"
            action-id="mysql_partition_manage"
            class="ml-8"
            :permission="row.permission.mysql_partition_manage"
            :resource="row.cluster_id"
            text
            theme="primary"
            @click="handleDisable(row)">
            {{ t('禁用') }}
          </AuthButton>
          <AuthButton
            v-else
            action-id="mysql_partition_manage"
            class="ml-8"
            :permission="row.permission.mysql_partition_manage"
            :resource="row.cluster_id"
            text
            theme="primary"
            @click="handleEnable(row)">
            {{ t('启用') }}
          </AuthButton>
          <!-- 更多操作（克隆、删除） -->
          <MoreActionExtend>
            <template #default>
              <div>
                <AuthButton
                  action-id="mysql_partition_manage"
                  :permission="row.permission.mysql_partition_manage"
                  text
                  @click="handleClone(row)">
                  {{ t('克隆') }}
                </AuthButton>
              </div>
              <div>
                <DbPopconfirm
                  :confirm-handler="() => handleRemove(row)"
                  :content="t('删除操作无法撤回，请谨慎操作！')"
                  :title="t('确认删除该分区策略？')">
                  <div style="height: 100%">
                    <AuthButton
                      action-id="mysql_partition_manage"
                      :permission="row.permission.mysql_partition_manage"
                      :resource="row.cluster_id"
                      text>
                      {{ t('删除') }}
                    </AuthButton>
                  </div>
                </DbPopconfirm>
              </div>
            </template>
          </MoreActionExtend>
        </template>
      </TableColumn>
    </DbTable>
    <!-- 新增/编辑 -->
    <PartitionOperation
      v-model:is-show="isShowOperation"
      :data="operationData"
      @create-success="handleOperationCreateSuccess"
      @edit-success="handleOperationEditSuccess" />
    <!-- excel 导入 -->
    <ExcelImport
      v-model:is-show="isShowExcelImport"
      @success="handleExcelImportSuccess" />
    <!-- 查看失败日志 -->
    <FailLog
      v-model:is-show="isShowFailLog"
      :data="operationData" />
  </div>
</template>
<script setup lang="tsx">
  import { InfoBox, Table as BkTable } from 'bkui-vue';
  import _ from 'lodash';
  import { ref, shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  const BkTableColumn = BkTable.Column;

  import PartitionModel from '@services/model/partition/partition';
  import {
    batchRemove,
    disablePartition,
    enablePartition,
    execute,
    exportPartitions,
    getList,
  } from '@services/source/partitionManage';

  import { useTableSettings, useTicketMessage } from '@hooks';

  import { ClusterTypes, UserPersonalSettings } from '@common/const';

  import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';
  import MoreActionExtend from '@components/more-action-extend/Index.vue';

  import { messageSuccess, utcDisplayTime } from '@utils';

  import ExcelImport from './components/excel-import/Index.vue';
  import FailLog from './components/fail-log/Index.vue';
  import PartitionOperation from './components/Operation.vue';

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const { settings: tableSetting, updateTableSettings } = useTableSettings(
    UserPersonalSettings.PARTITION_TABLE_SETTINGS,
    {
      checked: [
        'id',
        'immute_domain',
        'dblike',
        'tblike',
        'partition_column',
        'partition_column_type',
        'partition_time_interval',
        'expire_time',
        'status',
        'execute_time',
        'operation',
      ],
    },
  );

  const tableRef = ref();
  const searchValue = ref<Record<string, string>>({});
  const isShowOperation = ref(false);
  const isShowExcelImport = ref(false);
  const isShowFailLog = ref(false);
  const executeLoadingMap = ref<Record<number, boolean>>({});

  const operationData = shallowRef<PartitionModel>();
  const selectionList = shallowRef<number[]>([]);
  const selectionRowList = shallowRef<PartitionModel[]>([]);

  const disabled = computed(() => selectionList.value.length === 0);

  // 勾选的策略是否全部为已禁用状态
  const allDisabledSelected = computed(() => {
    if (selectionRowList.value.length === 0) return true;
    return selectionRowList.value.every((row) => row.isOffline);
  });

  // 勾选的策略是否全部为已启用状态
  const allEnabledSelected = computed(() => {
    if (selectionRowList.value.length === 0) return true;
    return selectionRowList.value.every((row) => row.isOnline);
  });

  const serachData = [
    {
      id: 'ids',
      name: t('策略 ID'),
      type: 'multiple-input',
      validator: (value: string) => {
        return !isNaN(Number(value)) ? true : t('ID 只支持数字');
      },
    },
    {
      description: t('单个值支持模糊搜索'),
      id: 'immute_domains',
      name: t('域名'),
      type: 'multiple-input',
    },
    {
      description: t('单个值支持模糊搜索'),
      id: 'dblikes',
      name: t('DB 名'),
      type: 'multiple-input',
    },
    {
      description: t('单个值支持模糊搜索'),
      id: 'tblikes',
      name: t('表名'),
      type: 'multiple-input',
    },
    {
      id: 'status',
      list: [
        {
          label: t('执行失败'),
          value: PartitionModel.STATUS_FAILED,
        },
        {
          label: t('执行成功'),
          value: PartitionModel.STATUS_SUCCESS,
        },
      ],
      name: t('最近执行状态'),
      type: 'multiple',
    },
  ] as QuickSearchProps['data'];

  // watch(searchValue, () => {
  //   tableRef.value!.clearSelected();
  // });

  const getRowClass = (data: PartitionModel) => {
    const classList: string[] = [];
    if (data.isOffline) {
      classList.push('is-offline');
    }
    if (data.isNew) {
      classList.push('is-new-row');
    }
    return classList.join(' ');
  };

  const dataSource = async (params: Record<string, any>) => {
    const result = await getList({
      ...params,
      ...searchValue.value,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_type: ClusterTypes.TENDBHA,
    });
    // 失败状态排前面
    result.results.sort((a: PartitionModel, b: PartitionModel) => {
      if (a.status === PartitionModel.STATUS_FAILED && b.status !== PartitionModel.STATUS_FAILED) return -1;
      if (a.status !== PartitionModel.STATUS_FAILED && b.status === PartitionModel.STATUS_FAILED) return 1;
      return 0;
    });
    return result;
  };

  const fetchData = () => {
    tableRef.value?.fetchData(searchValue.value, {
      cluster_type: ClusterTypes.TENDBHA,
    });
  };

  // 新建
  const handleCreate = () => {
    operationData.value = undefined;
    isShowOperation.value = true;
  };

  interface BatchConfirmOptions {
    confirmButtonTheme?: 'danger' | 'primary';
    description?: string;
    descriptionStyle?: string;
    filterFn?: (row: PartitionModel) => boolean;
    filterTip?: string;
    onConfirm: (validRows: PartitionModel[]) => Promise<boolean>;
    title: (count: number) => string;
  }

  /**
   * 通用批量操作确认弹窗
   * 支持过滤不符合条件的行、混合状态提示、自定义描述和操作
   */
  const showBatchConfirmBox = (options: BatchConfirmOptions) => {
    operationData.value = undefined;
    const rows = selectionRowList.value;
    const validRows = options.filterFn ? rows.filter(options.filterFn) : rows;
    const filteredCount = rows.length - validRows.length;

    InfoBox({
      cancelText: t('取消'),
      confirmButtonTheme: options.confirmButtonTheme ?? 'primary',
      confirmText: t('确定'),
      content: () => (
        <>
          {filteredCount > 0 && options.filterTip && (
            <div style='margin-bottom:16px;padding: 12px 16px;display: flex;align-items: center;background: #FFF3E1;border-radius: 2px;font-size: 12px;color: #63656E;'>
              {t(options.filterTip, { n: filteredCount })}
            </div>
          )}
          {options.description && (
            <div style={options.descriptionStyle ?? 'margin-bottom:16px;font-size: 12px;color: #63656E;'}>
              {t(options.description)}
            </div>
          )}
          <BkTable
            border='outer'
            data={validRows.map((row) => ({
              dblike: row.dblike,
              id: row.id,
              immute_domain: row.immute_domain,
              tblike: row.tblike,
            }))}
            height={254}>
            <BkTableColumn
              align='left'
              field='id'
              label={t('策略ID')}
              minWidth={80}
            />
            <BkTableColumn
              align='left'
              field='immute_domain'
              label={t('集群')}
              minWidth={120}
              showOverflowTooltip
            />
            <BkTableColumn
              align='left'
              field='dblike'
              label={t('DB名')}
              minWidth={80}
            />
            <BkTableColumn
              align='left'
              field='tblike'
              label={t('表名')}
              minWidth={80}
            />
          </BkTable>
        </>
      ),
      footerAlign: 'center',
      headerAlign: 'center',
      onConfirm: () => options.onConfirm(validRows),
      title: options.title(validRows.length),
      width: 560,
    });
  };

  // 批量启用
  const handleBatchEnable = () => {
    showBatchConfirmBox({
      filterFn: (row) => row.isOffline,
      filterTip: '已自动过滤 n 条已启用策略，不受本次操作影响。',
      onConfirm: async (validRows) => {
        const result = await enablePartition({
          cluster_type: ClusterTypes.TENDBHA,
          ids: validRows.map((row) => row.id),
        });
        if (result) {
          fetchData();
          messageSuccess(t('启用成功'));
          return true;
        }
        return false;
      },
      title: (n) => t('确定批量启用 n 条分区策略？', { n }),
    });
  };

  // 批量禁用
  const handleBatchDisable = () => {
    showBatchConfirmBox({
      filterFn: (row) => row.isOnline,
      filterTip: '已自动过滤 n 条已禁用策略，不受本次操作影响。',
      onConfirm: async (validRows) => {
        const result = await disablePartition({
          cluster_type: ClusterTypes.TENDBHA,
          ids: validRows.map((row) => row.id),
        });
        if (result) {
          fetchData();
          messageSuccess(t('禁用成功'));
          return true;
        }
        return false;
      },
      title: (n) => t('确定批量禁用 n 条分区策略？', { n }),
    });
  };

  // 批量删除
  const handleBatchRemove = () => {
    showBatchConfirmBox({
      confirmButtonTheme: 'danger',
      description: '删除后不可恢复。',
      descriptionStyle: 'margin-bottom:16px;font-size: 12px;color: #EA3636;',
      onConfirm: async () => {
        const result = await batchRemove({
          cluster_type: ClusterTypes.TENDBHA,
          ids: selectionList.value,
        });
        if (result) {
          fetchData();
          Object.values(selectionList.value).forEach((hostId) => {
            tableRef.value.removeSelectByKey(hostId);
          });
          selectionList.value = [];
          selectionRowList.value = [];
          messageSuccess(t('删除成功'));
          return true;
        }
        return false;
      },
      title: (n) => t('确定批量删除 n 条分区策略？', { n }),
    });
  };

  // 批量执行
  const handleBatchExecute = () => {
    showBatchConfirmBox({
      description: '执行后，将按当前配置对所选策略立即执行一次分区管理。',
      filterFn: (row) => row.isOnline,
      filterTip: '已自动过滤 n 条已禁用策略，不受本次操作影响。',
      onConfirm: async (validRows) => {
        const result = await execute({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          partition_infos: validRows.map((data: PartitionModel) => ({
            cluster_id: data.cluster_id,
            configs: [
              {
                config_id: data.id,
                dblike: data.dblike,
                expire_time: data.expire_time,
                extra_partition: data.extra_partition,
                partition_column: data.partition_column,
                partition_column_type: data.partition_column_type,
                partition_time_interval: data.partition_time_interval,
                partition_type: data.partition_type,
                phase: data.phase,
                tblike: data.tblike,
                time_zone: data.time_zone,
              },
            ],
            force: false,
          })),
        });
        if (result) {
          fetchData();
          ticketMessage(result.map((ticket) => ticket.id));
          return true;
        }
        return false;
      },
      title: (n) => t('确定批量执行 n 条分区策略？', { n }),
    });
  };

  // 导出所有
  const handleExportAll = () => {
    exportPartitions({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_type: ClusterTypes.TENDBHA,
      export_type: 'all',
    });
  };

  // 导出已选
  const handleExportSelected = () => {
    exportPartitions({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_type: ClusterTypes.TENDBHA,
      export_type: 'selected',
      selected_ids: selectionList.value,
    });
  };

  // 搜索
  const handleSearch = () => {
    fetchData();
  };

  const handleTableSelection = (payload: string[]) => {
    selectionList.value = payload.map((item) => Number(item));
    const tableData = tableRef.value?.getData() || [];
    selectionRowList.value = tableData.filter((data: PartitionModel) => selectionList.value.includes(data.id));
  };

  // 清空搜索
  const handleClearSearch = () => {
    searchValue.value = {};
    fetchData();
  };

  // 执行
  const handleExecute = async (data: PartitionModel) => {
    executeLoadingMap.value[data.id] = true;
    operationData.value = data;
    try {
      const executeResult = await execute({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        partition_infos: [
          {
            cluster_id: data.cluster_id,
            configs: [
              {
                config_id: data.id,
                dblike: data.dblike,
                expire_time: data.expire_time,
                extra_partition: data.extra_partition,
                partition_column: data.partition_column,
                partition_column_type: data.partition_column_type,
                partition_time_interval: data.partition_time_interval,
                partition_type: data.partition_type,
                phase: data.phase,
                tblike: data.tblike,
                time_zone: data.time_zone,
              },
            ],
            force: false,
          },
        ],
      });
      ticketMessage(executeResult[0].id);
    } finally {
      executeLoadingMap.value[data.id] = false;
    }
  };

  // 编辑
  const handleEdit = (payload: PartitionModel) => {
    isShowOperation.value = true;
    operationData.value = payload;
  };

  // 导入策略
  const handleShowExcelImport = () => {
    isShowExcelImport.value = true;
  };

  // Excel 导入成功
  const handleExcelImportSuccess = () => {
    fetchData();
  };

  // 编辑成功
  const handleOperationEditSuccess = () => {
    fetchData();
  };
  // 新建成功
  const handleOperationCreateSuccess = () => {
    operationData.value = undefined;
    fetchData();
  };

  const handleDisable = (payload: PartitionModel) => {
    disablePartition({
      cluster_type: ClusterTypes.TENDBHA,
      ids: [payload.id],
    }).then(() => {
      fetchData();
      messageSuccess(t('禁用成功'));
    });
  };

  const handleEnable = (payload: PartitionModel) => {
    enablePartition({
      cluster_type: ClusterTypes.TENDBHA,
      ids: [payload.id],
    }).then(() => {
      fetchData();
      messageSuccess(t('启用成功'));
    });
  };

  const handleClone = (payload: PartitionModel) => {
    const rowDataClone = _.cloneDeep(payload);
    rowDataClone.id = 0;
    operationData.value = rowDataClone;
    isShowOperation.value = true;
  };

  const handleRemove = (payload: PartitionModel) =>
    batchRemove({
      cluster_type: ClusterTypes.TENDBHA,
      ids: [payload.id],
    }).then(() => {
      fetchData();
      messageSuccess(t('移除成功'));
    });

  const handleShowFailLog = (payload: PartitionModel) => {
    operationData.value = payload;
    isShowFailLog.value = true;
  };

  onMounted(() => {
    fetchData();
  });
</script>
<style lang="less">
  .spider-manage-paritition-page {
    .header-action {
      display: flex;
    }

    .batch-operation {
      .batch-operation-icon {
        transform: rotate(0);
        transition: all 0.2s;
      }

      .batch-operation-icon-active {
        transform: rotate(180deg);
      }
    }

    .more-action {
      display: flex;
      width: 32px;
      height: 32px;
      font-size: 14px;
      cursor: pointer;
      border-radius: 50%;
      align-items: center;
      justify-content: center;

      &:hover {
        background: #dcdee5;
      }
    }

    .partition-table {
      .id-container {
        display: flex;
        align-items: center;
      }
    }

    .sub-title {
      position: relative;
      display: flex;
      height: 22px;
      padding-left: 9px;
      margin-left: 16px;
      font-family: MicrosoftYaHei, sans-serif;
      font-size: 14px;
      line-height: 22px;
      letter-spacing: 0;
      color: #979ba5;

      &::before {
        position: absolute;
        top: 4px;
        left: 0;
        width: 1px;
        height: 14px;
        background-color: #979ba580;
        content: '';
      }

      .sub-title-label {
        margin-right: 8px;
      }

      .sub-title-value {
        margin-right: 20px;
      }
    }
  }
</style>
