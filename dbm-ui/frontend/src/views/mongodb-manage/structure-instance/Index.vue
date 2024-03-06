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
  <div class="mongo-struct-ins-page">
    <BkAlert
      closable
      theme="info"
      :title="t('构造实例：通过定点构造产生的实例，可以将实例数据写回原集群或者直接销毁')" />
    <div class="top-operation">
      <BkButton
        :disabled="selectedList.length === 0"
        @click="() => handleDestroyCluster()">
        {{ t('批量销毁') }}
      </BkButton>
      <BkSearchSelect
        v-model="searchValue"
        class="input-box"
        :data="searchSelectList"
        :placeholder="t('请选择条件搜索')"
        unique-select
        value-split-code="+"
        @search="fetchTableData" />
    </div>
    <BkLoading
      :loading="isTableDataLoading"
      :z-index="2">
      <DbTable
        ref="tableRef"
        class="mongo-record-table"
        :clear-selection="false"
        :columns="columns"
        :data-source="queryRestoreRecord"
        selectable
        selection-key="target_cluster_id"
        :settings="settings"
        @clear-search="handleClearFilters"
        @column-filter="handleColumnFilter"
        @selection="handleSelection" />
    </BkLoading>
  </div>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import MongodbRollbackRecordModel from '@services/model/mongodb/mongodb-rollback-record';
  import { queryRestoreRecord } from '@services/source/mongodbRestore';
  import { createTicket } from '@services/source/ticket';

  import {
    useCopy,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import OperationBtnStatusTips from '@components/cluster-common/OperationBtnStatusTips.vue';
  import RenderOperationTag from '@components/cluster-common/RenderOperationTagNew.vue';
  import RenderRow from '@components/render-row/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { getSearchSelectorParams } from '@utils';

  interface SearchSelectItem {
    id: string,
    name: string,
  }

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const copy = useCopy();
  const handleDeleteSuccess = useTicketMessage();

  const searchValue = ref<Array<SearchSelectItem & {values: SearchSelectItem[]}>>([]);
  const selectedList = ref<MongodbRollbackRecordModel[]>([]);
  const isTableDataLoading = ref(false);
  const tableRef = ref();

  const searchSelectList = computed(() => ([
    {
      name: t('集群'),
      id: 'immute_domain',
    },
    {
      name: t('集群类型'),
      id: 'cluster_type',
      multiple: true,
      children: [
        {
          id: 'MongoReplicaSet',
          name: t('副本集集群'),

        },
        {
          id: 'MongoShardedCluster',
          name: t('分片集群'),
        },
      ]
    },
    {
      name: 'IP',
      id: 'ips',
    },
  ]));

  const settings = {
    fields: [
      {
        label: t('构造的集群'),
        field: 'target_cluster',
      },
      {
        label: t('源集群'),
        field: 'source_cluster',
      },
      {
        label: t('集群类型'),
        field: 'cluster_type',
      },
      {
        label: t('构造的主机'),
        field: 'target_nodes',
      },
      {
        label: t('每台主机Shard数'),
        field: 'instance_per_host',
      },
      {
        label: t('构造类型'),
        field: 'struct_type',
      },
      {
        label: t('关联单据'),
        field: 'ticket_id',
      },
      {
        label: t('构造DB名'),
        field: 'db_patterns',
      },
      {
        label: t('忽略DB名'),
        field: 'ignore_dbs',
      },
      {
        label: t('构造表名'),
        field: 'table_patterns',
      },
      {
        label: t('忽略表名'),
        field: 'ignore_tables',
      },

    ],
    checked: ['target_cluster', 'source_cluster', 'cluster_type', 'target_nodes', 'instance_per_host', 'struct_type', 'ticket_id'],
  };

  const columns = [
    {
      label: t('构造的集群'),
      field: 'target_cluster',
      fixed: 'left',
      minWidth: 140,
      width: 140,
      render: ({ data }: {data: MongodbRollbackRecordModel}) => (
        <TextOverflowLayout>
          {{
            default: () => <span>{data.target_cluster.immute_domain}</span>,
            append: () => (
              <>
              {
                data.operationTagTips.map(item => <RenderOperationTag class="cluster-tag" data={item} />)
              }
              <db-icon
                type="copy"
                v-bk-tooltips={t('复制n', { n: t('构造的集群') })}
                onClick={() => copy(data.target_cluster.immute_domain)} />
              </>
            ),
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: t('源集群'),
      field: 'source_cluster',
      showOverflowTooltip: true,
      minWidth: 150,
      render: ({ data }: {data: MongodbRollbackRecordModel}) => (
        <TextOverflowLayout>
          {{
            default: () => <span>{data.sourceClusteText}</span>,
            append: () => (
              <db-icon
                type="copy"
                v-bk-tooltips={t('复制n', { n: t('源集群') })}
                onClick={() => copy(data.sourceClusteText)} />
            ),
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: t('集群类型'),
      field: 'cluster_type',
      showOverflowTooltip: false,
      minWidth: 100,
      width: 100,
      filter: {
        list: [
          {
            value: 'MongoReplicaSet',
            text: t('副本集集群'),

          },
          {
            value: 'MongoShardedCluster',
            text: t('分片集群'),
          },
        ]
      },
      render: ({ data }: {data: MongodbRollbackRecordModel}) => data.sourceClusterTypeText,
    },
    {
      label: t('构造的主机'),
      field: 'target_nodes',
      minWidth: 130,
      render: ({ data }: {data: MongodbRollbackRecordModel}) => (
        <div class="struct-host">
          <RenderRow data={data.target_nodes} showAll />
          <db-icon
            type="copy"
            v-bk-tooltips={t('复制n', { n: t('构造的主机') })}
            onClick={() => copy(data.target_nodes.join(','))} />
        </div>
        ),
    },
    {
      label: t('每台主机Shard数'),
      field: 'instance_per_host',
      minWidth: 140,
      width: 140,
    },

    {
      label: t('构造类型'),
      field: 'struct_type',
      showOverflowTooltip: true,
      minWidth: 120,
      width: 200,
      render: ({ data }: {data: MongodbRollbackRecordModel}) => data.rollbackTypeText,
    },
    {
      label: t('关联单据'),
      field: 'ticket_id',
      showOverflowTooltip: true,
      minWidth: 100,
      width: 100,
      render: ({ data }: {data: MongodbRollbackRecordModel}) => (data.ticket_id ? (
        <router-link
          target="_blank"
          to={{
            name: 'SelfServiceMyTickets',
            query: {
              id: data.ticket_id,
            },
          }}>
          {data.ticket_id}
        </router-link>
        ) : '--'),
    },
    {
      label: t('构造DB名'),
      field: 'db_patterns',
      showOverflowTooltip: false,
      render: ({ data }: {data: MongodbRollbackRecordModel}) => (
        <>
          {data.ns_filter.db_patterns.length > 0 ? data.ns_filter.db_patterns.map(item => <bk-tag>{item}</bk-tag>) : '--'}
        </>
      ),
    },
    {
      label: t('忽略DB名'),
      field: 'ignore_dbs',
      showOverflowTooltip: false,
      render: ({ data }: {data: MongodbRollbackRecordModel}) => (
        <>
          {data.ns_filter.ignore_dbs.length > 0 ? data.ns_filter.ignore_dbs.map(item => <bk-tag>{item}</bk-tag>) : '--'}
        </>
      ),
    },
    {
      label: t('构造表名'),
      field: 'table_patterns',
      showOverflowTooltip: false,
      render: ({ data }: {data: MongodbRollbackRecordModel}) => (
        <>
          {data.ns_filter.table_patterns.length > 0 ? data.ns_filter.table_patterns.map(item => <bk-tag>{item}</bk-tag>) : '--'}
        </>
      ),
    },
    {
      label: t('忽略表名'),
      field: 'ignore_tables',
      showOverflowTooltip: false,
      render: ({ data }: {data: MongodbRollbackRecordModel}) => (
        <>
          {data.ns_filter.ignore_tables.length > 0 ? data.ns_filter.ignore_tables.map(item => <bk-tag>{item}</bk-tag>) : '--'}
        </>
      ),
    },
    {
      label: t('操作'),
      fixed: 'right',
      showOverflowTooltip: true,
      minWidth: 140,
      width: 180,
      render: ({ data }: {data: MongodbRollbackRecordModel}) => (
        <>
          <OperationBtnStatusTips data={data}>
            <bk-button
              text
              theme="primary"
              disabled={data.operationDisabled}
              onClick={() => handleDestroyCluster(data)}>
              {t('销毁')}
            </bk-button>
          </OperationBtnStatusTips>
          <bk-button
            text
            theme="primary"
            onClick={() => copy(data.target_cluster.immute_domain)}
            style="margin-left:10px;">
            {t('复制访问地址')}
          </bk-button>
        </>
      ),
    },
  ];

  watch(searchValue, () => {
    fetchTableData();
  });

  const fetchTableData = () => {
    const searchParams = getSearchSelectorParams(searchValue.value);
    tableRef.value?.fetchData(searchParams, {});
  };

  onMounted(() => {
    fetchTableData();
  });

  const handleSelection = (data: MongodbRollbackRecordModel, list: MongodbRollbackRecordModel[]) => {
    selectedList.value = list;
  };

  const handleColumnFilter = (data: {
    checked: string[],
    column: {
      field: string,
      label: string,
      filter: {
        list: {
          value: string,
          text: string,
        }[]
      }
    },
    index: number,
  }) => {
    if (data.checked.length === 0) {
      searchValue.value = searchValue.value.filter(item => item.id !== data.column.field);
      return;
    }
    searchValue.value = [{
      id: data.column.field,
      name: data.column.label,
      values: data.checked.map(item => ({
        id: item,
        name: data.column.filter.list.find(row => row.value === item)?.text ?? '',
      })),
    }];
  };

  const handleClearFilters = () => {
    searchValue.value = [];
    fetchTableData();
  };

  // 设置行样式
  // const setRowClass = (row: MongodbRollbackRecordModel) => (row.isDestroyed ? 'disable-color' : 'normal-color');


  // 批量销毁
  const handleDestroyCluster = (row?: MongodbRollbackRecordModel) => {
    const params = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.MONGODB_TEMPORARY_DESTROY,
      details: {
        cluster_ids: row ? [row.target_cluster.id] : selectedList.value.map(item => item.target_cluster.id),
      },
    };
    const count = row ? 1 : selectedList.value.length;
    InfoBox({
      title: t('确认销毁n个集群的构造记录', { n: count }),
      subTitle: t('销毁后将不可再恢复，请谨慎操作！'),
      width: 400,
      confirmText: t('删除'),
      onConfirm: () => {
        createTicket(params)
          .then((data) => {
            const ticketId = data.id;
            handleDeleteSuccess(ticketId);
          });
      } });
  };
</script>

<style lang="less" scoped>
  .mongo-struct-ins-page {
    padding-bottom: 20px;

    :deep(.normal-color) {
      .cell {
        color: #63656e;
      }
    }

    :deep(.disable-color) {
      .cell {
        color: #c4c6cc;
      }
    }

    :deep(.operate-box) {
      cursor: pointer;
    }

    :deep(.cell) {
      line-height: normal !important;

      .db-icon-copy {
        display: none;
        margin-left: 4px;
        color: @primary-color;
        cursor: pointer;
      }
    }

    :deep(tr:hover) {
      .db-icon-copy {
        display: inline-block !important;
      }
    }

    :deep(.struct-host) {
      display: flex;
      width: 100%;
      align-items: center;
    }

    .top-operation {
      display: flex;
      width: 100%;
      margin: 16px 0;
      justify-content: space-between;

      .input-box {
        width: 560px;
        height: 32px;
      }
    }

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;

      .safe-action {
        margin-left: auto;

        .safe-action-text {
          padding-bottom: 2px;
          border-bottom: 1px dashed #979ba5;
        }
      }
    }
  }
</style>
