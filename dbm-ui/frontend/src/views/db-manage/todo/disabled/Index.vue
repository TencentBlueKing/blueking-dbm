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
    <DbTab
      v-model="dbType"
      :label-config="labelConfig" />
    <div class="content-wrapper">
      <div class="header-action">
        <!-- <span
          v-bk-tooltips="{
            content: t('请选择集群'),
            disabled: isSelected,
          }"
          class="inline-block">
          <BkButton
            :disabled="!isSelected"
            @click="handleBatchDelete">
            {{ t('批量删除') }}
          </BkButton>
        </span>
        <span
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
          style="width: 500px"
          @change="handleQuickSearchChange" />
      </div>
      <DbTable
        ref="table"
        :data-source="ticketClusterDisableTodo"
        :filter-value="quickSearchValue"
        ignore-biz
        row-key="id"
        @filter-change="handleFilterChange">
        <TableColumn
          col-key="immute_domain"
          :filter="columnFilter?.immute_domain"
          fixed="left"
          :min-width="340"
          :title="t('集群')">
          <template #default="{ row }: { row: TicketClusterDisableTodoModel }">
            <BkButton
              text
              theme="primary"
              @click="() => handleToClusterDetail(row)">
              {{ row.immute_domain }}
            </BkButton>
          </template>
        </TableColumn>
        <TableColumn
          col-key="cluster_id"
          :filter="columnFilter?.cluster_id"
          title="ID"
          :width="200">
          <template #default="{ row }: { row: TicketClusterDisableTodoModel }">
            {{ row.id }}
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
          :width="100">
          <template #default="{ row }: { row: TicketClusterDisableTodoModel }">
            <BkButton
              text
              theme="primary"
              @click="() => handleDelete(row)">
              {{ t('删除') }}
            </BkButton>
            <BkButton
              class="ml-8"
              text
              theme="primary"
              @click="() => handleEnable(row)">
              {{ t('启用') }}
            </BkButton>
          </template>
        </TableColumn>
      </DbTable>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketClusterDisableTodoModel from '@services/model/ticket-cluster-disable-todo/TicketClusterDisableTodo';
  import { ticketClusterDisableTodo } from '@services/source/ticket';

  import { useClusterDisableCount } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { DBTypeInfos, DBTypes } from '@common/const';

  import DbTab from '@components/db-tab/Index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import { URL_CLUSTER_DETAIL_MEMO_KEY } from '@views/db-manage/common/cluster-details';
  import { clusterTypeListPageMap } from '@views/db-manage/const/clusterTypeListPageMap';

  import { getBusinessHref } from '@utils';

  // import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';
  import AssistTab from './components/AssistTab.vue';
  import { useColumnFilter } from './useColumnFilter';
  import { useOperateClusterBasic } from './useOperateClusterBasic';
  import { useQuickSearch } from './useQuickSearch';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
  const globalBizStore = useGlobalBizs();

  // const { handleSelection, isSelected, selectedList } = useClusterTableSelect<TicketClusterDisableTodoModel>();
  const { quickSearchData, quickSearchValue } = useQuickSearch();
  const { data: columnFilter } = useColumnFilter();
  const { data: clusterDisableCountData, toAssistCount, todoCount } = useClusterDisableCount();
  const { handleDeleteCluster, handleEnableCluster } = useOperateClusterBasic({
    onSuccess() {
      fetchData();
    },
  });

  const tableRef = useTemplateRef('table');

  const isAssist = ref(Number(route.params.assist));
  const dbType = ref((route.params.dbType || '') as DBTypes);

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

  watch(dbType, () => {
    fetchData();
    router.replace({
      params: {
        dbType: dbType.value,
      },
    });
  });

  const fetchData = () => {
    tableRef.value!.fetchData({
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
</script>

<style lang="less">
  .cluster-disable-todo {
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
  }
</style>
