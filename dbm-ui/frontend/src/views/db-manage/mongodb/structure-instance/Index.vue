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
        show-settings
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

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import RenderRow from '@components/render-row/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import RenderOperationTag from '@views/db-manage/common/RenderOperationTagNew.vue';

  import { execCopy, getSearchSelectorParams } from '@utils';

  interface SearchSelectItem {
    id: string;
    name: string;
  }

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const handleDeleteSuccess = useTicketMessage();

  const searchValue = ref<Array<{ values: SearchSelectItem[] } & SearchSelectItem>>([]);
  const selectedList = ref<MongodbRollbackRecordModel[]>([]);
  const isTableDataLoading = ref(false);
  const tableRef = ref();

  const searchSelectList = computed(() => [
    {
      id: 'immute_domain',
      name: t('集群'),
    },
    {
      children: [
        {
          id: 'MongoReplicaSet',
          name: t('副本集集群'),
        },
        {
          id: 'MongoShardedCluster',
          name: t('分片集群'),
        },
      ],
      id: 'cluster_type',
      multiple: true,
      name: t('集群类型'),
    },
    {
      id: 'ips',
      name: 'IP',
    },
  ]);

  const settings = {
    checked: [
      'target_cluster',
      'source_cluster',
      'cluster_type',
      'target_nodes',
      'instance_per_host',
      'struct_type',
      'ticket_id',
    ],
    fields: [
      {
        field: 'target_cluster',
        label: t('构造的集群'),
      },
      {
        field: 'source_cluster',
        label: t('源集群'),
      },
      {
        field: 'cluster_type',
        label: t('集群类型'),
      },
      {
        field: 'target_nodes',
        label: t('构造的主机'),
      },
      {
        field: 'instance_per_host',
        label: t('每台主机Shard数'),
      },
      {
        field: 'struct_type',
        label: t('构造类型'),
      },
      {
        field: 'ticket_id',
        label: t('关联单据'),
      },
      {
        field: 'db_patterns',
        label: t('构造DB名'),
      },
      {
        field: 'ignore_dbs',
        label: t('忽略DB名'),
      },
      {
        field: 'table_patterns',
        label: t('构造表名'),
      },
      {
        field: 'ignore_tables',
        label: t('忽略表名'),
      },
    ],
  };

  const columns = [
    {
      field: 'target_cluster',
      fixed: 'left',
      label: t('构造的集群'),
      minWidth: 140,
      render: ({ data }: { data: MongodbRollbackRecordModel }) => (
        <TextOverflowLayout>
          {{
            append: () => (
              <>
                {data.operationTagTips.map((item) => (
                  <RenderOperationTag
                    class='cluster-tag'
                    data={item}
                  />
                ))}
                <db-icon
                  v-bk-tooltips={t('复制n', { n: t('构造的集群') })}
                  type='copy'
                  onClick={() => execCopy(data.target_cluster.immute_domain, t('复制成功，共n条', { n: 1 }))}
                />
              </>
            ),
            default: () => <span>{data.target_cluster.immute_domain}</span>,
          }}
        </TextOverflowLayout>
      ),
      width: 140,
    },
    {
      field: 'source_cluster',
      label: t('源集群'),
      minWidth: 150,
      render: ({ data }: { data: MongodbRollbackRecordModel }) => (
        <TextOverflowLayout>
          {{
            append: () => (
              <db-icon
                v-bk-tooltips={t('复制n', { n: t('源集群') })}
                type='copy'
                onClick={() => execCopy(data.sourceClusteText, t('复制成功，共n条', { n: 1 }))}
              />
            ),
            default: () => <span>{data.sourceClusteText}</span>,
          }}
        </TextOverflowLayout>
      ),
      showOverflowTooltip: true,
    },
    {
      field: 'cluster_type',
      filter: {
        list: [
          {
            text: t('副本集集群'),
            value: 'MongoReplicaSet',
          },
          {
            text: t('分片集群'),
            value: 'MongoShardedCluster',
          },
        ],
      },
      label: t('集群类型'),
      minWidth: 100,
      render: ({ data }: { data: MongodbRollbackRecordModel }) => data.sourceClusterTypeText,
      showOverflowTooltip: false,
      width: 100,
    },
    {
      field: 'target_nodes',
      label: t('构造的主机'),
      minWidth: 130,
      render: ({ data }: { data: MongodbRollbackRecordModel }) => (
        <div class='struct-host'>
          <RenderRow
            data={data.target_nodes}
            showAll
          />
          <db-icon
            v-bk-tooltips={t('复制n', { n: t('构造的主机') })}
            type='copy'
            onClick={() => execCopy(data.target_nodes.join(','), t('复制成功，共n条', { n: 1 }))}
          />
        </div>
      ),
    },
    {
      field: 'instance_per_host',
      label: t('每台主机Shard数'),
      minWidth: 140,
      width: 140,
    },

    {
      field: 'struct_type',
      label: t('构造类型'),
      minWidth: 120,
      render: ({ data }: { data: MongodbRollbackRecordModel }) => data.rollbackTypeText,
      showOverflowTooltip: true,
      width: 200,
    },
    {
      field: 'ticket_id',
      label: t('关联单据'),
      minWidth: 100,
      render: ({ data }: { data: MongodbRollbackRecordModel }) =>
        data.ticket_id ? (
          <router-link
            to={{
              name: 'bizTicketManage',
              params: {
                ticketId: data.ticket_id,
              },
            }}
            target='_blank'>
            {data.ticket_id}
          </router-link>
        ) : (
          '--'
        ),
      showOverflowTooltip: true,
      width: 100,
    },
    {
      field: 'db_patterns',
      label: t('构造DB名'),
      render: ({ data }: { data: MongodbRollbackRecordModel }) => (
        <>
          {data.ns_filter.db_patterns.length > 0
            ? data.ns_filter.db_patterns.map((item) => <bk-tag>{item}</bk-tag>)
            : '--'}
        </>
      ),
      showOverflowTooltip: false,
    },
    {
      field: 'ignore_dbs',
      label: t('忽略DB名'),
      render: ({ data }: { data: MongodbRollbackRecordModel }) => (
        <>
          {data.ns_filter.ignore_dbs.length > 0
            ? data.ns_filter.ignore_dbs.map((item) => <bk-tag>{item}</bk-tag>)
            : '--'}
        </>
      ),
      showOverflowTooltip: false,
    },
    {
      field: 'table_patterns',
      label: t('构造表名'),
      render: ({ data }: { data: MongodbRollbackRecordModel }) => (
        <>
          {data.ns_filter.table_patterns.length > 0
            ? data.ns_filter.table_patterns.map((item) => <bk-tag>{item}</bk-tag>)
            : '--'}
        </>
      ),
      showOverflowTooltip: false,
    },
    {
      field: 'ignore_tables',
      label: t('忽略表名'),
      render: ({ data }: { data: MongodbRollbackRecordModel }) => (
        <>
          {data.ns_filter.ignore_tables.length > 0
            ? data.ns_filter.ignore_tables.map((item) => <bk-tag>{item}</bk-tag>)
            : '--'}
        </>
      ),
      showOverflowTooltip: false,
    },
    {
      fixed: 'right',
      label: t('操作'),
      minWidth: 140,
      render: ({ data }: { data: MongodbRollbackRecordModel }) => (
        <>
          <OperationBtnStatusTips data={data}>
            <bk-button
              disabled={data.operationDisabled}
              theme='primary'
              text
              onClick={() => handleDestroyCluster(data)}>
              {t('销毁')}
            </bk-button>
          </OperationBtnStatusTips>
          <bk-button
            style='margin-left:10px;'
            theme='primary'
            text
            onClick={() => execCopy(data.target_cluster.immute_domain, t('复制成功，共n条', { n: 1 }))}>
            {t('复制访问地址')}
          </bk-button>
        </>
      ),
      showOverflowTooltip: true,
      width: 180,
    },
  ];

  watch(searchValue, () => {
    fetchTableData();
    tableRef.value!.clearSelected();
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
    checked: string[];
    column: {
      field: string;
      filter: {
        list: {
          text: string;
          value: string;
        }[];
      };
      label: string;
    };
    index: number;
  }) => {
    if (data.checked.length === 0) {
      searchValue.value = searchValue.value.filter((item) => item.id !== data.column.field);
      return;
    }
    searchValue.value = [
      {
        id: data.column.field,
        name: data.column.label,
        values: data.checked.map((item) => ({
          id: item,
          name: data.column.filter.list.find((row) => row.value === item)?.text ?? '',
        })),
      },
    ];
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
      details: {
        cluster_ids: row ? [row.target_cluster.id] : selectedList.value.map((item) => item.target_cluster.id),
      },
      ticket_type: TicketTypes.MONGODB_TEMPORARY_DESTROY,
    };
    const count = row ? 1 : selectedList.value.length;
    InfoBox({
      confirmText: t('删除'),
      onConfirm: () => {
        createTicket(params).then((data) => {
          const ticketId = data.id;
          handleDeleteSuccess(ticketId);
        });
      },
      subTitle: t('销毁后将不可再恢复，请谨慎操作！'),
      title: t('确认销毁n个集群的构造记录', { n: count }),
      width: 400,
    });
  };
</script>

<style lang="less" scoped>
  .mongo-struct-ins-page {
    padding-bottom: 20px;

    :deep(.normal-color) {
      .vxe-cell {
        color: #63656e;
      }
    }

    :deep(.disable-color) {
      .vxe-cell {
        color: #c4c6cc;
      }
    }

    :deep(.operate-box) {
      cursor: pointer;
    }

    :deep(.vxe-cell) {
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
