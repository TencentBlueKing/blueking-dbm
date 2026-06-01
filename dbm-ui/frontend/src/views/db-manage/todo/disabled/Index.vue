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
  <div class="cluster-disable-todo">
    <AssistTab
      v-model="isAssist"
      :db-type="dbType"
      :to-assist-count="toAssistCount"
      :todo-count="todoCount"
      @change="handleAssistChange" />
    <BkLoading
      class="cluster-disable-todo-content"
      :loading="isClusterDisableCountLoading">
      <template v-if="showContent">
        <DbTab
          v-model="dbType"
          :exclude="excludeDbTypes"
          :label-config="labelConfig" />
        <div class="content-wrapper">
          <div class="header-action">
            <span
              v-bk-tooltips="tooltips"
              class="inline-block">
              <BkButton
                :disabled="!tooltips.disabled"
                theme="primary"
                @click="handleBatchDelete">
                <DbIcon
                  class="mr-4"
                  type="delete" />
                {{ t('批量下架') }}
              </BkButton>
            </span>
            <!-- <span
          v-bk-tooltips="{
            content: t('请选择集群'),
            disabled: isSelected,
          }"
          class="inline-block">
          <BkButton
            :disabled="!isSelected"
            @click="handleBatchEnable">
            {{ t('批量启用') }}
          </BkButton>
        </span> -->
            <DbQuickSearch
              v-model="quickSearchValue"
              :data="quickSearchData"
              parse-url
              :placeholder="t('请输入或选择条件搜索')"
              style="width: 500px; margin-left: auto"
              @change="handleQuickSearchChange" />
          </div>
          <DbTable
            ref="table"
            :data-source="ticketClusterDisableTodo"
            :disable-select-method="disableSelectMethod"
            :filter-value="quickSearchValue"
            row-key="id"
            :selectable="selectable"
            :selected="selectedList"
            @filter-change="handleFilterChange"
            @selection="handleSelection">
            <!-- <TableColumn
              col-key="cluster_id"
              :filter="columnFilter?.cluster_id"
              fixed="left"
              title="ID"
              :width="150">
              <template #default="{ row }: { row: TicketClusterDisableTodoModel }">
                {{ row.id }}
              </template>
            </TableColumn> -->
            <TableColumn
              col-key="immute_domain"
              :filter="columnFilter?.immute_domain"
              fixed="left"
              :min-width="340"
              :title="t('集群')">
              <template #default="{ row }: { row: TicketClusterDisableTodoModel }">
                {{ row.immute_domain }}
              </template>
            </TableColumn>

            <TableColumn
              v-if="showClusterTypeColumn"
              col-key="cluster_type"
              :title="t('架构类型')"
              :width="200">
              <template #default="{ row }: { row: TicketClusterDisableTodoModel }">
                <BkTag
                  :theme="
                    [
                      ClusterTypes.TENDBSINGLE,
                      ClusterTypes.REDIS_INSTANCE,
                      ClusterTypes.MONGO_REPLICA_SET,
                      ClusterTypes.SQLSERVER_SINGLE,
                    ].includes(row.cluster_type)
                      ? 'success'
                      : 'info'
                  ">
                  {{ row.clusterTypesDisplay }}
                </BkTag>
              </template>
            </TableColumn>
            <TableColumn
              col-key="bk_biz_id"
              :filter="columnFilter?.bk_biz_id"
              :title="t('所属业务')">
              <template #default="{ row }: { row: TicketClusterDisableTodoModel }">
                {{ globalBizStore.bizIdMap.get(row.bk_biz_id)?.name || '--' }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="create_at"
              :filter="columnFilter?.create_at"
              :title="t('禁用时间')">
              <template #default="{ row }: { row: TicketClusterDisableTodoModel }">
                {{ row.distableTimeDisplay }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="disableSecondsDisplay"
              :title="t('已禁用时长')">
              <template #default="{ row }: { row: TicketClusterDisableTodoModel }">
                <span :class="{ 'disabled-time-alert': row.isDisableAlert }">{{ row.disableSecondsDisplay }}</span>
              </template>
            </TableColumn>
            <TableColumn
              col-key="disable_person"
              :filter="columnFilter?.disable_person"
              :title="t('禁用人')" />
            <TableColumn
              col-key="opration"
              fixed="right"
              :title="t('操作')"
              :width="150">
              <template #default="{ row }: { row: TicketClusterDisableTodoModel }">
                <BkButton
                  text
                  theme="primary"
                  @click="() => handleDelete(row)">
                  {{ t('下架') }}
                </BkButton>
                <BkButton
                  class="ml-8"
                  text
                  theme="primary"
                  @click="() => handleEnable(row)">
                  {{ t('启用') }}
                </BkButton>
                <BkButton
                  class="ml-8"
                  text
                  theme="primary"
                  @click="() => handleToClusterDetail(row)">
                  {{ t('查看集群') }}
                </BkButton>
              </template>
            </TableColumn>
          </DbTable>
        </div>
      </template>
      <BkException
        v-else
        class="empty-exception"
        scene="page"
        :title="t('暂无下架待办')"
        type="empty" />
    </BkLoading>
    <BatchDeleteDialog
      v-model="isBatchDeleteDialogShow"
      :db-type="dbType"
      :selected="selectedList"
      @suceess="handleBatchDeleteSuccess" />
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketClusterDisableTodoModel from '@services/model/ticket-cluster-disable-todo/TicketClusterDisableTodo';
  import { ticketClusterDisableTodo } from '@services/source/ticket';

  import { useClusterDisableCount } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, DBTypeInfos, DBTypes } from '@common/const';

  import DbTab from '@components/db-tab/Index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import { URL_CLUSTER_DETAIL_MEMO_KEY } from '@views/db-manage/common/cluster-details';
  import { clusterTypeListPageMap } from '@views/db-manage/const/clusterTypeListPageMap';
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';

  import { getBusinessHref } from '@utils';

  import AssistTab from './components/AssistTab.vue';
  import BatchDeleteDialog from './components/BatchDeleteDialog.vue';
  import { useColumnFilter } from './useColumnFilter';
  import { useOperateClusterBasic } from './useOperateClusterBasic';
  import { useQuickSearch } from './useQuickSearch';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
  const globalBizStore = useGlobalBizs();

  const { handleSelection, isSelected, selectedList } = useClusterTableSelect<TicketClusterDisableTodoModel>();
  const { quickSearchData, quickSearchValue } = useQuickSearch();
  const { data: columnFilter } = useColumnFilter();
  const {
    data: clusterDisableCountData,
    loading: isClusterDisableCountLoading,
    toAssistCount,
    todoCount,
  } = useClusterDisableCount();
  const { handleDeleteCluster, handleEnableCluster } = useOperateClusterBasic({
    onSuccess() {
      fetchData();
    },
  });

  const tableRef = useTemplateRef('table');

  const isAssist = ref(Number(route.params.assist));
  const dbType = ref((route.params.dbType || '') as DBTypes);
  const isBatchDeleteDialogShow = ref(false);

  const showContent = computed(() => {
    return (isAssist.value ? toAssistCount.value : todoCount.value) > 0;
  });

  const excludeDbTypes = computed(() => {
    if (clusterDisableCountData && clusterDisableCountData.value) {
      const { to_assist: toAssist, todo } = clusterDisableCountData.value;
      const countMap = isAssist.value ? toAssist : todo;
      return Object.keys(DBTypeInfos).reduce<DBTypes[]>((prev, dbType) => {
        if (!countMap[dbType as DBTypes]) {
          return prev.concat(dbType as DBTypes);
        }
        return prev;
      }, []);
    }
    return;
  });

  const labelConfig = computed(() => {
    if (clusterDisableCountData && clusterDisableCountData.value) {
      const { to_assist: toAssist, todo } = clusterDisableCountData.value;
      const countMap = isAssist.value ? toAssist : todo;
      return Object.keys(DBTypeInfos).reduce(
        (prev, dbType) =>
          Object.assign(prev, {
            [dbType]: `${DBTypeInfos[dbType as DBTypes].name}(${countMap[dbType as DBTypes] || 0})`,
          }),
        {} as Record<DBTypes, string>,
      );
    }
    return;
  });

  const showClusterTypeColumn = computed(() =>
    [DBTypes.MONGODB, DBTypes.MYSQL, DBTypes.REDIS, DBTypes.SQLSERVER].includes(dbType.value),
  );
  const selectable = computed(() =>
    [DBTypes.MONGODB, DBTypes.MYSQL, DBTypes.REDIS, DBTypes.SQLSERVER, DBTypes.TENDBCLUSTER].includes(dbType.value),
  );
  const tooltips = computed(() => {
    if (selectable.value) {
      return {
        content: t('请选择集群'),
        disabled: isSelected.value,
      };
    }
    return {
      content: t('该数据库类型暂不支持批量下架'),
      disabled: false,
    };
  });

  // watch(isAssist, () => {
  //   tableRef.value?.clearSelected();
  // });

  watch(dbType, () => {
    fetchData();
    router.replace({
      params: {
        dbType: dbType.value,
      },
    });
    // tableRef.value?.clearSelected();
  });

  const fetchData = () => {
    tableRef.value?.fetchData({
      db_type: dbType.value,
      is_assist: Boolean(isAssist.value),
      ...quickSearchValue.value,
    });
  };

  const handleAssistChange = () => {
    fetchData();
  };

  const handleQuickSearchChange = () => {
    fetchData();
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    quickSearchValue.value = filterValue;
    fetchData();
  };

  const disableSelectMethod = (row: TicketClusterDisableTodoModel) => {
    if (
      [
        ClusterTypes.PREDIXY_REDIS_CLUSTER,
        ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
        ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
        ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
      ].includes(row.cluster_type)
    ) {
      return t('该架构类型暂不支持批量下架');
    }
    return false;
  };

  const handleToClusterDetail = (row: TicketClusterDisableTodoModel) => {
    const routeInfo = router.resolve({
      name: clusterTypeListPageMap[row.cluster_type],
      params: {
        clusterId: row.id,
      },
      query: {
        [URL_CLUSTER_DETAIL_MEMO_KEY]: 'info',
      },
    });
    const targetPath = getBusinessHref(routeInfo.href, row.bk_biz_id);
    window.open(targetPath);
  };

  const handleDelete = (row: TicketClusterDisableTodoModel) => {
    handleDeleteCluster(row.cluster_type, [row]);
  };

  const handleEnable = (row: TicketClusterDisableTodoModel) => {
    handleEnableCluster(row.cluster_type, [row]);
  };

  const handleBatchDelete = () => {
    isBatchDeleteDialogShow.value = true;
  };

  const handleBatchDeleteSuccess = () => {
    // tableRef.value?.clearSelected();
    fetchData();
  };
</script>

<style lang="less">
  .cluster-disable-todo {
    height: 100%;

    .cluster-disable-todo-content {
      height: 100%;

      .content-wrapper {
        padding: 16px 24px;

        .header-action {
          display: flex;
          flex-wrap: wrap;
          margin-bottom: 16px;
          gap: 8px;
        }
      }

      .disabled-time-alert {
        color: #ea3636;
      }

      .empty-exception {
        display: flex;
        height: 100%;
        background-color: #fff;
        align-items: center;
        justify-content: center;
      }
    }
  }
</style>
