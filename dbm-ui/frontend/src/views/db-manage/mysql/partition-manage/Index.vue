<template>
  <div class="spider-manage-paritition-page">
    <div class="header-action mb-16">
      <AuthButton
        action-id="mysql_partition_create"
        class="w-88"
        theme="primary"
        @click="handleCreate">
        {{ t('新建') }}
      </AuthButton>
      <DbPopconfirm
        :confirm-handler="handleBatchRemove"
        :content="t('移除后将不可恢复')"
        :title="t('确认移除选中的策略')">
        <BkButton
          class="ml-8"
          :disabled="selectionList.length < 1">
          {{ t('删除') }}
        </BkButton>
      </DbPopconfirm>
      <DbSearchSelect
        v-model="searchValues"
        :data="serachData"
        :placeholder="t('输入关键字或选择条件搜索')"
        style="width: 500px; margin-left: auto"
        unique-select
        @change="handleSearch" />
    </div>
    <DbTable
      ref="tableRef"
      class="partition-table"
      :columns="tableColumn"
      :data-source="getList"
      :row-class="getRowClass"
      selectable
      :settings="tableSetting"
      show-settings
      @clear-search="handleClearSearch"
      @selection="handleTableSelection"
      @setting-change="handleSettingChange" />
    <PartitionOperation
      v-model:is-show="isShowOperation"
      :data="operationData"
      @create-success="handleOperationCreateSuccess"
      @edit-success="handleOperationEditSuccess" />
    <DbSideslider
      v-model:is-show="isShowExecuteLog"
      :show-footer="false"
      :title="t(`查看执行记录`)"
      :width="1000">
      <ExecuteLog
        v-if="operationData"
        :data="operationData" />
    </DbSideslider>
  </div>
</template>
<script setup lang="tsx">
  import { Message } from 'bkui-vue';
  import _ from 'lodash';
  import { ref, shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type PartitionModel from '@services/model/partition/partition';
  import {
    batchRemove,
    disablePartition,
    dryRun,
    enablePartition,
    execute,
    getList,
  } from '@services/source/partitionManage';

  import { useTicketMessage } from '@hooks';

  import { ClusterTypes } from '@common/const';
  import { batchSplitRegex } from '@common/regex';

  import { getSearchSelectorParams, messageSuccess } from '@utils';

  import ExecuteLog from './components/ExecuteLog.vue';
  import PartitionOperation from './components/Operation.vue';
  import useTableSetting from './hooks/useTableSetting';

  type DryRunData = ServiceReturnType<typeof dryRun>;

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();
  const { handleChange: handleSettingChange, setting: tableSetting } = useTableSetting();

  const tableRef = ref();
  const searchValues = ref([]);
  const isShowOperation = ref(false);
  const isShowExecuteLog = ref(false);
  const executeLoadingMap = ref<Record<number, boolean>>({});

  const operationData = shallowRef<PartitionModel>();
  const selectionList = shallowRef<number[]>([]);

  const serachData = [
    {
      id: 'ids',
      multiple: true,
      name: t('策略 ID'),
    },
    {
      id: 'immute_domains',
      multiple: true,
      name: t('域名'),
    },
    {
      id: 'dblikes',
      multiple: true,
      name: t('DB 名'),
    },
    {
      id: 'tblikes',
      multiple: true,
      name: t('表名'),
    },
  ];

  const tableColumn = [
    {
      field: 'id',
      fixed: 'left',
      label: t('策略 ID'),
      render: ({ data }: { data: PartitionModel }) => (
        <div class='id-container'>
          <span>{data.id}</span>
          {data.isNew && (
            <bk-tag
              class='ml-4'
              size='small'
              theme='success'>
              NEW
            </bk-tag>
          )}
          {data.isOffline && (
            <bk-tag
              class='ml-4'
              size='small'>
              {t('已禁用')}
            </bk-tag>
          )}
        </div>
      ),
      width: 100,
    },
    {
      field: 'immute_domain',
      label: t('集群域名'),
      render: ({ data }: { data: PartitionModel }) => data.immute_domain || '--',
      width: 240,
    },
    {
      field: 'dblike',
      label: t('DB 名'),
      render: ({ data }: { data: PartitionModel }) => {
        if (!data.dblike) {
          return '--';
        }
        return <bk-tag>{data.dblike}</bk-tag>;
      },
      width: 150,
    },
    {
      field: 'tblike',
      label: t('表名'),
      render: ({ data }: { data: PartitionModel }) => {
        if (!data.tblike) {
          return '--';
        }
        return <bk-tag>{data.tblike}</bk-tag>;
      },
      width: 150,
    },
    {
      field: 'partition_columns',
      label: t('分区字段'),
      render: ({ data }: { data: PartitionModel }) => data.partition_columns || '--',
    },
    {
      field: 'partition_column_type',
      label: t('分区字段类型'),
      render: ({ data }: { data: PartitionModel }) => data.partition_column_type || '--',
    },
    {
      field: 'partition_time_interval',
      label: t('分区间隔（天）'),
      render: ({ data }: { data: PartitionModel }) => data.partition_time_interval || '--',
    },
    {
      field: 'expire_time',
      label: t('数据过期时间（天）'),
      minWidth: 150,
      render: ({ data }: { data: PartitionModel }) => data.expire_time || '--',
    },
    {
      field: 'status',
      label: t('最近一次执行状态'),
      render: ({ data }: { data: PartitionModel }) => (
        <div>
          <db-icon
            class={{ 'rotate-loading': data.isRunning }}
            style='vertical-align: middle;'
            type={data.statusIcon}
            svg
          />
          <span class='ml-4'>{data.statusText}</span>
        </div>
      ),
      width: 200,
    },
    {
      field: 'execute_time',
      label: t('最近一次执行时间'),
      render: ({ data }: { data: PartitionModel }) => data.executeTimeDisplay || '--',
      width: 240,
    },
    {
      fixed: 'right',
      label: t('操作'),
      render: ({ data }: { data: PartitionModel }) => {
        const renderAction = () => {
          if (data.isRunning) {
            return (
              <router-link
                to={{
                  name: 'bizTicketManage',
                  params: {
                    ticketId: data.ticket_id,
                  },
                }}
                target='_blank'>
                {t('查看')}
              </router-link>
            );
          }
          if (!data.isOnline) {
            return (
              <auth-button
                actionId='mysql_partition_enable_disable'
                permission={data.permission.mysql_partition_enable_disable}
                resource={data.cluster_id}
                theme='primary'
                text
                onClick={() => handleEnable(data)}>
                {t('启用')}
              </auth-button>
            );
          }
          return (
            <auth-button
              actionId='mysql_partition'
              loading={executeLoadingMap.value[data.id]}
              permission={data.permission.mysql_partition}
              resource={data.cluster_id}
              theme='primary'
              text
              onClick={() => handleExecute(data)}>
              {t('执行')}
            </auth-button>
          );
        };
        return (
          <>
            {renderAction()}
            <span
              v-bk-tooltips={{
                content: t('正在执行中，无法编辑'),
                disabled: !data.isRunning,
              }}
              class='ml-8'>
              <auth-button
                actionId='mysql_partition_update'
                disabled={data.isRunning}
                permission={data.permission.mysql_partition_update}
                resource={data.cluster_id}
                theme='primary'
                text
                onClick={() => handleEdit(data)}>
                {t('编辑')}
              </auth-button>
            </span>
            <auth-button
              action-id='mysql_partition'
              class='ml-8 mr-16'
              permission={data.permission.mysql_partition}
              resource={data.cluster_id}
              theme='primary'
              text
              onClick={() => handleShowExecuteLog(data)}>
              {t('执行记录')}
            </auth-button>
            <more-action-extend>
              {{
                default: () => (
                  <>
                    {data.isOnline && (
                      <bk-dropdown-item>
                        <auth-template
                          action-id='mysql_partition_enable_disable'
                          permission={data.permission.mysql_partition_enable_disable}
                          resource={data.cluster_id}>
                          <div onClick={() => handleDisable(data)}>{t('禁用')}</div>
                        </auth-template>
                      </bk-dropdown-item>
                    )}
                    <bk-dropdown-item>
                      <auth-template
                        action-id='mysql_partition_create'
                        permission={data.permission.mysql_partition_create}>
                        <div onClick={() => handleClone(data)}>{t('克隆')}</div>
                      </auth-template>
                    </bk-dropdown-item>
                    <bk-dropdown-item>
                      <auth-template
                        action-id='mysql_partition_delete'
                        permission={data.permission.mysql_partition_delete}
                        resource={data.cluster_id}>
                        <db-popconfirm
                          confirm-handler={() => handleRemove(data)}
                          content={t('删除操作无法撤回，请谨慎操作！')}
                          title={t('确认删除该分区策略？')}>
                          <div>{t('删除')}</div>
                        </db-popconfirm>
                      </auth-template>
                    </bk-dropdown-item>
                  </>
                ),
              }}
            </more-action-extend>
          </>
        );
      },
      showOverflow: false,
      width: 180,
    },
  ];

  watch(searchValues, () => {
    tableRef.value!.clearSelected();
  });

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

  const fetchData = () => {
    const searchParams = getSearchSelectorParams(searchValues.value);
    /**
     * 多域名精确查询、单域名模糊查询，用domain_name字段
     */
    if (searchParams.immute_domains?.split(batchSplitRegex).length <= 1) {
      searchParams.domain_name = searchParams.immute_domains;
      delete searchParams.immute_domains;
    }
    tableRef.value?.fetchData(searchParams, {
      cluster_type: ClusterTypes.TENDBHA,
    });
  };

  // 新建
  const handleCreate = () => {
    operationData.value = undefined;
    isShowOperation.value = true;
  };

  // 批量删除
  const handleBatchRemove = () => {
    operationData.value = undefined;
    return batchRemove({
      cluster_type: ClusterTypes.TENDBHA,
      ids: selectionList.value,
    }).then(() => {
      fetchData();
      Object.values(selectionList.value).forEach((hostId) => {
        tableRef.value.removeSelectByKey(hostId);
      });
      selectionList.value = [];
      messageSuccess(t('移除成功'));
    });
  };

  // 搜索
  const handleSearch = () => {
    fetchData();
  };

  const handleTableSelection = (payload: string[]) => {
    selectionList.value = payload.map((item) => Number(item));
  };

  // 清空搜索
  const handleClearSearch = () => {
    searchValues.value = [];
    fetchData();
  };

  // 执行
  const handleExecute = async (data: PartitionModel) => {
    executeLoadingMap.value[data.id] = true;
    operationData.value = data;
    try {
      const dryRunResults = await dryRun({
        cluster_id: data.cluster_id,
        config_id: data.id,
      });
      const dryRunData = Object.keys(dryRunResults).reduce<DryRunData>(
        (result, configId) =>
          Object.assign(result, {
            [configId]: _.filter(dryRunResults[Number(configId)], (item) => !item.message),
          }),
        {},
      );
      if (!dryRunData[data.id].length) {
        const messageConfig = {
          actions: [
            {
              disabled: true,
              id: 'assistant',
            },
          ],
          message: {
            assistant: '',
            code: '',
            details: {
              message: dryRunResults[data.id][0].message,
            },
            overview: t('目标分区异常'),
            suggestion: '',
            type: 'key-value',
          },
          theme: 'error',
        };
        Message(messageConfig);
      } else {
        const executeResult = await execute({
          cluster_id: data.cluster_id,
          partition_objects: dryRunData,
        });
        ticketMessage(executeResult[0].id);
      }
    } finally {
      executeLoadingMap.value[data.id] = false;
    }
  };
  // 编辑
  const handleEdit = (payload: PartitionModel) => {
    isShowOperation.value = true;
    operationData.value = payload;
  };
  // 执行记录
  const handleShowExecuteLog = (payload: PartitionModel) => {
    isShowExecuteLog.value = true;
    operationData.value = payload;
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
</script>
<style lang="less">
  .spider-manage-paritition-page {
    .header-action {
      display: flex;
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
  }
</style>
