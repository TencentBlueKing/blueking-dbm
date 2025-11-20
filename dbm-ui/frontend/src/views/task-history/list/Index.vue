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
  <div class="task-history-list-page">
    <div class="header-action">
      <DbQuickSearch
        v-model="quickSearchValue"
        :data="quickSearchData"
        parse-url
        :placeholder="quickSerachPlaceholder"
        style="width: 500px"
        @change="handleQuickSearchChange" />
    </div>
    <DbTable
      ref="tableRef"
      :data-source="dataSource"
      :filter-value="quickSearchValue"
      releate-url-query
      row-key="root_id"
      @clear-search="handleClearSearch"
      @filter-change="handleFilterChange">
      <TableColumn
        col-key="root_id__in"
        :filter="tableFilter['root_id__in']"
        fixed="left"
        title="ID"
        :width="180">
        <template #default="{ row }: { row: TaskFlowModel }">
          <AuthRouterLink
            action-id="flow_detail"
            :permission="row.permission.flow_detail"
            :resource="row.root_id"
            target="_blank"
            :to="{
              name: 'taskHistoryDetail',
              params: {
                root_id: row.root_id,
              },
              query: {
                from: route.name as string,
              },
            }">
            {{ row.root_id }}
          </AuthRouterLink>
        </template>
      </TableColumn>
      <TableColumn
        col-key="flow_alias"
        :filter="tableFilter['flow_alias']"
        :title="t('任务名')"
        :width="200">
        <template #default="{ row }: { row: TaskFlowModel }">
          {{ row.nameText }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_biz_id__in"
        :filter="isPlatformManage ? tableFilter['bk_biz_id__in'] : undefined"
        :title="t('业务')"
        :width="150">
        <template #default="{ row }: { row: TaskFlowModel }">
          {{ row.bk_biz_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="status__in"
        :filter="tableFilter['status__in']"
        :title="t('状态')"
        :width="160">
        <template #default="{ row }: { row: TaskFlowModel }">
          <DbStatus
            :theme="row.statusTheme"
            type="linear">
            {{ t(row.statusText) }}
          </DbStatus>
        </template>
      </TableColumn>
      <TableColumn
        col-key="ticket_type_search"
        :filter="tableFilter['ticket_type_search']"
        :title="t('关联单据类型')">
        <template #default="{ row }: { row: TaskFlowModel }">
          {{ row.ticket_type_display || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="uid__in"
        :filter="tableFilter['uid__in']"
        :title="t('关联单据')"
        :width="120">
        <template #default="{ row }: { row: TaskFlowModel }">
          <AuthButton
            v-if="row.uid"
            action-id="ticket_view"
            :permission="row.permission.ticket_view"
            :resource="row.uid"
            text
            theme="primary"
            @click="handleGoTicketDetail(row)">
            {{ row.uid }}
          </AuthButton>
          <span v-else>--</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="created_by__in"
        :filter="tableFilter['created_by__in']"
        :title="t('执行人')"
        :width="120">
        <template #default="{ row }: { row: TaskFlowModel }">
          {{ row.created_by }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="created_at"
        :filter="tableFilter['created_at']"
        :title="t('执行时间')"
        :width="250">
        <template #default="{ row }: { row: TaskFlowModel }">
          {{ row.createAtDisplay }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="cost_time"
        :title="t('耗时')"
        :width="150">
        <template #default="{ row }: { row: TaskFlowModel }">
          {{ getCostTimeDisplay(row.cost_time) }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="row-operation"
        :title="t('操作')"
        :width="120">
        <template #default="{ row }: { row: TaskFlowModel }">
          <AuthRouterLink
            action-id="flow_detail"
            :permission="row.permission.flow_detail"
            :resource="row.root_id"
            target="_blank"
            :to="{
              name: 'taskHistoryDetail',
              params: {
                root_id: row.root_id,
              },
              query: {
                from: route.name as string,
              },
            }">
            {{ t('查看详情') }}
          </AuthRouterLink>
          <BkButton
            v-if="
              [TicketTypes.REDIS_KEYS_EXTRACT, TicketTypes.REDIS_KEYS_DELETE].includes(row.ticket_type) &&
              row.status === 'FINISHED'
            "
            class="ml-6"
            text
            theme="primary"
            @click="handleShowResultFiles(row.root_id)">
            {{ t('查看结果文件') }}
          </BkButton>
        </template>
      </TableColumn>
    </DbTable>
  </div>
  <!-- 结果文件功能 -->
  <RedisResultFiles
    :id="resultFileState.rootId"
    v-model="resultFileState.isShow" />
</template>

<script setup lang="ts">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import TaskFlowModel from '@services/model/taskflow/taskflow';
  import { getTaskflow } from '@services/source/taskflow';
  import { getTicketGroupTypes } from '@services/source/ticket';
  import { getUserList } from '@services/source/user';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';
  import DbStatus from '@components/db-status/index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import { getBusinessHref, getCostTimeDisplay, transfromDataToQuery } from '@utils';

  import RedisResultFiles from '../components/RedisResultFiles.vue';

  import useTableFilter from './use-table-filter';

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();
  const tableFilter = useTableFilter();
  const globalBizsStore = useGlobalBizs();

  const isPlatformManage = route.name === 'platformTaskHistoryList';
  const quickSerachPlaceholder = isPlatformManage
    ? t('搜索ID_业务_任务类型_状态_关联单据_执行人_执行时间')
    : t('搜索ID_任务类型_状态_关联单据_执行人_执行时间');

  const dataSource = (params: Parameters<typeof getTaskflow>[0]) => {
    const realParams = {
      ...params,
    };
    if (!isPlatformManage) {
      Object.assign(realParams, { bk_biz_id: window.PROJECT_CONFIG.BIZ_ID });
    }
    return getTaskflow(realParams);
  };

  const quickSearchData = [
    {
      id: 'root_id__in',
      name: 'ID',
      type: 'multiple-input',
    },
    isPlatformManage && {
      id: 'bk_biz_id__in',
      list: globalBizsStore.bizs.map((item) => ({
        label: item.name,
        value: `${item.bk_biz_id}`,
      })),
      name: t('业务'),
      type: 'multiple',
    },
    {
      id: 'ticket_type_search',
      name: t('关联单据类型'),
      props: {
        checkStrictly: true,
        showAllLevels: true,
      },
      remoteMethod: () =>
        getTicketGroupTypes().then((data) =>
          data.map((item) => {
            return {
              children: item.children.map((child) => {
                return {
                  label: child.label,
                  value: `ticket_type__in#${child.value}`,
                };
              }),
              label: item.label,
              value: `db_type#${item.value}`,
            };
          }),
        ),
      type: 'multiple-cascader',
    },
    {
      id: 'status__in',
      list: Object.keys(TaskFlowModel.STATUS_TEXT_MAP).map((value: string) => ({
        label: t(TaskFlowModel.STATUS_TEXT_MAP[value]),
        value,
      })),
      name: t('状态'),
      type: 'multiple',
    },
    {
      id: 'uid__in',
      name: t('关联单据'),
      type: 'multiple-input',
    },
    {
      id: 'created_by__in',
      name: t('执行人'),
      remoteMethod: (params: { defaultValue?: string; keyword?: string }) => {
        const requestParams = {};
        if (params.defaultValue) {
          Object.assign(requestParams, { exact_lookups: params.defaultValue });
        }
        if (params.keyword) {
          Object.assign(requestParams, { fuzzy_lookups: params.keyword });
        }

        return getUserList(requestParams).then((data) =>
          data.results.map((item) => ({
            label: `${item.username} (${item.display_name})`,
            value: item.username,
          })),
        );
      },
      remoteSearch: true,
      type: 'multiple',
    },
    {
      id: 'created_at',
      name: t('执行时间'),
      props: {
        shortcuts: [
          {
            text: t('近 1 小时'),
            value: () => [dayjs().subtract(1, 'hour').toDate(), dayjs().toDate()],
          },
          {
            text: t('近 12 小时'),
            value: () => [dayjs().subtract(12, 'hour').toDate(), dayjs().toDate()],
          },
          {
            text: t('今天'),
            value: () => [dayjs().startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
          {
            text: t('近 7 天'),
            value: () => [dayjs().subtract(6, 'day').startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
          {
            text: t('近 1 个月'),
            value: () => [dayjs().subtract(1, 'month').startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
          {
            text: t('近 3 个月'),
            value: () => [dayjs().subtract(3, 'month').startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
          {
            text: t('近 6 个月'),
            value: () => [dayjs().subtract(6, 'month').startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
        ],
      },
      type: 'datetime-range',
    },
  ].filter((item) => item) as QuickSearchProps['data'];

  const tableRef = ref();
  const quickSearchValue = ref<Record<string, any>>({
    created_at: `${dayjs().subtract(6, 'day').startOf('day').format('YYYY-MM-DD HH:mm:ss')},${dayjs().endOf('day').format('YYYY-MM-DD HH:mm:ss')}`,
  });

  /** 查看结果文件功能 */
  const resultFileState = reactive({
    isShow: false,
    rootId: '',
  });

  const fetchData = () => {
    tableRef.value.fetchData(transfromDataToQuery(quickSearchValue.value));
  };

  const handleQuickSearchChange = () => {
    fetchData();
    tableRef.value!.clearSelected();
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    quickSearchValue.value = filterValue;
  };

  const handleClearSearch = () => {
    quickSearchValue.value = {};
    fetchData();
  };

  const handleShowResultFiles = (id: string) => {
    resultFileState.isShow = true;
    resultFileState.rootId = id;
  };

  const handleGoTicketDetail = (data: TaskFlowModel) => {
    const { href } = router.resolve({
      name: 'bizTicketManage',
      params: {
        ticketId: data.uid,
      },
    });

    window.open(getBusinessHref(href, data.bk_biz_id), '_blank');
  };
</script>

<style lang="less">
  .task-history-list-page {
    .header-action {
      display: flex;
      padding-bottom: 16px;
    }
  }
</style>
