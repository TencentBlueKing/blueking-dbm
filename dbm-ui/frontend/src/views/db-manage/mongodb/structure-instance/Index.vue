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
      <DbQuickSearch
        v-model="searchValue"
        class="input-box"
        :data="searchSelectList"
        :placeholder="t('请选择条件搜索')" />
    </div>
    <BkLoading
      :loading="isTableDataLoading"
      :z-index="2">
      <DbTable
        ref="tableRef"
        :bk-ui-settings="settings"
        class="mongo-record-table"
        :data-source="queryRestoreRecord"
        :filter-value="searchValue"
        row-key="id"
        selectable
        @clear-search="handleClearFilters"
        @filter-change="handleFilterChange"
        @selection="handleSelection">
        <TableColumn
          col-key="target_cluster"
          fixed="left"
          :min-width="140"
          :title="t('构造的集群')"
          :width="140">
          <template #default="{ row: data }: { row: MongodbRollbackRecordModel }">
            <TextOverflowLayout>
              <span>{{ data.target_cluster.immute_domain }}</span>
              <template #append>
                <RenderOperationTag
                  v-for="(item, index) in data.operationTagTips"
                  :key="index"
                  class="cluster-tag"
                  :data="item" />
                <DbIcon
                  v-bk-tooltips="t('复制n', { n: t('构造的集群') })"
                  type="copy"
                  @click="execCopy(data.target_cluster.immute_domain, t('复制成功，共n条', { n: 1 }))" />
              </template>
            </TextOverflowLayout>
          </template>
        </TableColumn>
        <TableColumn
          col-key="source_cluster"
          :min-width="150"
          :title="t('源集群')">
          <template #default="{ row: data }: { row: MongodbRollbackRecordModel }">
            <TextOverflowLayout>
              <span>{{ data.sourceClusteText }}</span>
              <template #append>
                <DbIcon
                  v-bk-tooltips="t('复制n', { n: t('源集群') })"
                  type="copy"
                  @click="execCopy(data.sourceClusteText, t('复制成功，共n条', { n: 1 }))" />
              </template>
            </TextOverflowLayout>
          </template>
        </TableColumn>
        <TableColumn
          col-key="cluster_type"
          :ellipsis="false"
          :filter="{
            list: clusterTypeFilterList,
            showConfirmAndReset: true,
            type: 'multiple',
          }"
          :min-width="100"
          :title="t('集群类型')"
          :width="100">
          <template #default="{ row: data }: { row: MongodbRollbackRecordModel }">
            {{ data.sourceClusterTypeText }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="target_nodes"
          :min-width="130"
          :title="t('构造的主机')">
          <template #default="{ row: data }: { row: MongodbRollbackRecordModel }">
            <div class="struct-host">
              <RenderRow
                :data="data.target_nodes"
                show-all />
              <DbIcon
                v-bk-tooltips="t('复制n', { n: t('构造的主机') })"
                type="copy"
                @click="execCopy(data.target_nodes.join(','), t('复制成功，共n条', { n: 1 }))" />
            </div>
          </template>
        </TableColumn>
        <TableColumn
          col-key="instance_per_host"
          :min-width="140"
          :title="t('每台主机Shard数')"
          :width="140">
        </TableColumn>
        <TableColumn
          col-key="struct_type"
          :min-width="120"
          :title="t('构造类型')"
          :width="200">
          <template #default="{ row: data }: { row: MongodbRollbackRecordModel }">
            {{ data.rollbackTypeText }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="ticket_id"
          :min-width="100"
          :title="t('关联单据')"
          :width="100">
          <template #default="{ row: data }: { row: MongodbRollbackRecordModel }">
            <RouterLink
              v-if="data.ticket_id"
              target="_blank"
              :to="{
                name: 'bizTicketManage',
                params: {
                  ticketId: data.ticket_id,
                },
              }">
              {{ data.ticket_id }}
            </RouterLink>
            <span v-else>--</span>
          </template>
        </TableColumn>
        <TableColumn
          col-key="db_patterns"
          :ellipsis="false"
          :title="t('构造DB名')">
          <template #default="{ row: data }: { row: MongodbRollbackRecordModel }">
            <template v-if="data.ns_filter.db_patterns.length > 0">
              <BkTag
                v-for="item in data.ns_filter.db_patterns"
                :key="item">
                {{ item }}
              </BkTag>
            </template>
            <span v-else>--</span>
          </template>
        </TableColumn>
        <TableColumn
          col-key="ignore_dbs"
          :ellipsis="false"
          :title="t('忽略DB名')">
          <template #default="{ row: data }: { row: MongodbRollbackRecordModel }">
            <template v-if="data.ns_filter.ignore_dbs.length > 0">
              <BkTag
                v-for="item in data.ns_filter.ignore_dbs"
                :key="item">
                {{ item }}
              </BkTag>
            </template>
            <span v-else>--</span>
          </template>
        </TableColumn>
        <TableColumn
          col-key="table_patterns"
          :ellipsis="false"
          :title="t('构造表名')">
          <template #default="{ row: data }: { row: MongodbRollbackRecordModel }">
            <template v-if="data.ns_filter.table_patterns.length > 0">
              <BkTag
                v-for="item in data.ns_filter.table_patterns"
                :key="item">
                {{ item }}
              </BkTag>
            </template>
            <span v-else>--</span>
          </template>
        </TableColumn>
        <TableColumn
          col-key="ignore_tables"
          :ellipsis="false"
          :title="t('忽略表名')">
          <template #default="{ row: data }: { row: MongodbRollbackRecordModel }">
            <template v-if="data.ns_filter.ignore_tables.length > 0">
              <BkTag
                v-for="item in data.ns_filter.ignore_tables"
                :key="item">
                {{ item }}
              </BkTag>
            </template>
            <span v-else>--</span>
          </template>
        </TableColumn>
        <TableColumn
          col-key="operation"
          fixed="right"
          :min-width="140"
          :title="t('操作')"
          :width="180">
          <template #default="{ row: data }: { row: MongodbRollbackRecordModel }">
            <OperationBtnStatusTips :data="data">
              <BkButton
                :disabled="data.operationDisabled"
                text
                theme="primary"
                @click="() => handleDestroyCluster(data)">
                {{ t('销毁') }}
              </BkButton>
            </OperationBtnStatusTips>
            <BkButton
              style="margin-left: 10px"
              text
              theme="primary"
              @click="execCopy(data.target_cluster.immute_domain, t('复制成功，共n条', { n: 1 }))">
              {{ t('复制访问地址') }}
            </BkButton>
          </template>
        </TableColumn>
      </DbTable>
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

  import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';
  import RenderRow from '@components/render-row/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import RenderOperationTag from '@views/db-manage/common/RenderOperationTagNew.vue';

  import { execCopy, transfromDataToQuery } from '@utils';

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const handleDeleteSuccess = useTicketMessage();

  const searchValue = ref<Record<string, string>>({});
  const selectedList = ref<MongodbRollbackRecordModel[]>([]);
  const isTableDataLoading = ref(false);
  const tableRef = ref();

  const searchSelectList = computed<QuickSearchProps['data']>(() => [
    {
      id: 'immute_domain',
      name: t('集群'),
      type: 'multiple-input',
    },
    {
      id: 'cluster_type',
      list: [
        {
          label: t('副本集集群'),
          value: 'MongoReplicaSet',
        },
        {
          label: t('分片集群'),
          value: 'MongoShardedCluster',
        },
      ],
      name: t('集群类型'),
      type: 'multiple',
    },
    {
      id: 'ips',
      name: 'IP',
      type: 'multiple-input',
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
  };

  const clusterTypeFilterList = [
    {
      label: t('副本集集群'),
      value: 'MongoReplicaSet',
    },
    {
      label: t('分片集群'),
      value: 'MongoShardedCluster',
    },
  ];

  watch(searchValue, () => {
    fetchTableData();
  });

  const fetchTableData = () => {
    tableRef.value?.fetchData(transfromDataToQuery(searchValue.value));
  };

  onMounted(() => {
    fetchTableData();
  });

  const handleSelection = (_keys: string[], list: MongodbRollbackRecordModel[]) => {
    selectedList.value = list;
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    searchValue.value = filterValue;
  };

  const handleClearFilters = () => {
    searchValue.value = {};
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
      td {
        color: #63656e;
      }
    }

    :deep(.disable-color) {
      td {
        color: #c4c6cc;
      }
    }

    :deep(.operate-box) {
      cursor: pointer;
    }

    :deep(td) {
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
