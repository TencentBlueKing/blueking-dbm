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
  <div class="redis-hot-key-list">
    <div class="header-action">
      <!-- <span
        v-bk-tooltips="{
          disabled: selected.length > 0,
          content: t('请选择任务'),
        }">
        <BkButton
          :disabled="selected.length === 0"
          @click="() => handleExport()">
          {{ t('批量导出') }}
        </BkButton>
      </span> -->
      <BkDatePicker
        v-model="daterange"
        :placeholder="t('选择日期范围')"
        style="width: 350px; margin-left: auto"
        type="datetimerange"
        @change="fetchTableData" />
      <DbSearchSelect
        class="ml-8"
        :data="searchData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px"
        @change="handleSearchValueChange" />
    </div>
    <DbTable
      ref="tableRef"
      :data-source="queryAnalysisRecords"
      releate-url-query
      :show-overflow="false"
      @clear-search="handleClearSearch"
      @column-filter="columnFilterChange">
      <BkTableColumn
        field="root_id"
        fixed="left"
        :label="t('任务 ID')"
        :min-width="180">
        <template #default="{data}: {data: RedisHotKeyModel}">
          <div
            v-if="data.root_id"
            class="hot-key-task-id">
            <BkButton
              text
              theme="primary"
              @click="handleShowDetail(data)">
              {{ data.root_id }}
            </BkButton>
            <BkButton
              v-bk-tooltips="t('跳转查看任务')"
              class="link-icon ml-4"
              text
              theme="primary"
              @click="handleToTaskDetail(data)">
              <DbIcon type="link" />
            </BkButton>
          </div>
          <span v-else>--</span>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="ins_list"
        :label="t('目标实例')"
        min-width="200"
        :show-overflow="false">
        <template #default="{ data }: { data: RedisHotKeyModel }">
          <div
            v-if="data.ins_list"
            style="line-height: 20px">
            <div
              v-for="item in data.ins_list.slice(0, 6)"
              :key="item">
              {{ item }}
            </div>
            <div v-if="data.ins_list.length > 6">
              <span>...</span>
              <BkTag
                v-bk-tooltips="{
                  content: data.ins_list.join('\n'),
                }"
                class="ml-4"
                size="small">
                <I18nT
                  keypath="共n个"
                  scope="global">
                  {{ data.ins_list.length }}
                </I18nT>
              </BkTag>
            </div>
          </div>
          <template v-if="data.ins_list.length < 1"> -- </template>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="root_id"
        :label="t('所属集群')"
        :min-width="200">
        <template #default="{data}: {data: RedisHotKeyModel}">
          <BkButton
            text
            theme="primary"
            @click="handleToClusterList(data)">
            {{ data.immute_domain }}
          </BkButton>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="status"
        :filterss="{
          list: Object.keys(RedisHotKeyModel.STATUS_TEXT_MAP).map((id) => ({
            label: t(RedisHotKeyModel.STATUS_TEXT_MAP[id]),
            value: id,
          })),
          checked: columnCheckedMap.status,
        }"
        :label="t('任务状态')"
        :width="120">
        <template #default="{data}: {data: RedisHotKeyModel}">
          <DbStatus
            :theme="data.statusTheme"
            type="linear">
            {{ t(data.statusText) }}
          </DbStatus>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="analysis_time"
        :label="t('分析时长')"
        :width="80">
        <template #default="{data}: {data: RedisHotKeyModel}">
          {{ `${data.analysis_time}s` }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="creator"
        :label="t('创建人')"
        show-overflow
        :width="150">
      </BkTableColumn>
      <BkTableColumn
        field="ticket_id"
        :label="t('关联单据')"
        :width="100">
        <template #default="{data}: {data: RedisHotKeyModel}">
          <BkButton
            text
            theme="primary"
            @click="handleGoTicketDetail(data)">
            {{ data.ticket_id }}
          </BkButton>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="createAtDisplay"
        :label="t('开始时间')"
        :width="180">
      </BkTableColumn>
      <BkTableColumn
        field="updateAtDisplay"
        :label="t('结束时间')"
        :width="180">
      </BkTableColumn>
      <BkTableColumn
        fixed="right"
        :label="t('操作')"
        :width="100">
        <template #default="{data}: {data: RedisHotKeyModel}">
          <template v-if="data.status === 'FINISHED'">
            <BkButton
              text
              theme="primary"
              @click="handleShowDetail(data)">
              {{ t('查看') }}
            </BkButton>
            <BkButton
              class="ml-12"
              text
              theme="primary"
              @click="handleExport(data)">
              {{ t('导出') }}
            </BkButton>
          </template>
          <template v-else>--</template>
        </template>
      </BkTableColumn>
    </DbTable>
    <Detail
      v-model:current-index="currentDetailIndex"
      v-model:is-show="isDetailShow"
      :record-list="recordList"
      @refresh="fetchTableData" />
  </div>
</template>

<script setup lang="tsx">
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { format } from 'date-fns';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import RedisHotKeyModel from '@services/model/redis/redis-hot-key';
  import { exportHotKeyAnalysis, queryAnalysisRecords } from '@services/source/redisAnalysis';
  import { getTicketTypes } from '@services/source/ticket';
  import { getUserList } from '@services/source/user';

  import { useLinkQueryColumnSerach } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';

  import { getBusinessHref, getMenuListSearch, getSearchSelectorParams } from '@utils';

  import Detail from './components/detail/Index.vue';

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();

  const { clearSearchValue, columnCheckedMap, columnFilterChange, handleSearchValueChange, searchValue } =
    useLinkQueryColumnSerach({
      attrs: [],
      fetchDataFn: () => fetchTableData(),
      isCluster: false,
      isQueryAttrs: false,
      searchType: 'resource_record',
    });

  /**
   * 近 15 天
   */
  const initDate = () => {
    const end = new Date();
    const start = new Date();
    start.setTime(start.getTime() - 3600 * 1000 * 24 * 15);
    return [start.toISOString(), end.toISOString()] as [string, string];
  };

  const tableRef = useTemplateRef('tableRef');

  const isDetailShow = ref(false);
  const currentDetailIndex = ref(0);
  const daterange = ref(initDate());

  const ticketTypes = ref<{ id: string; name: string }[]>([]);
  // const selected = shallowRef<RedisHotKeyModel[]>([]);
  const recordList = shallowRef<RedisHotKeyModel[]>([]);

  const searchData = computed(() => [
    {
      id: 'instance_addresses',
      multiple: true,
      name: t('目标实例'),
    },
    {
      id: 'immute_domain',
      multiple: true,
      name: t('所属集群'),
    },
    {
      id: 'operator',
      name: t('创建人'),
    },
  ]);

  useRequest(getTicketTypes, {
    onSuccess(data) {
      ticketTypes.value = data.map((item) => ({
        id: item.key,
        name: item.value,
      }));

      const ticketTypeItem = searchValue.value.find((item) => item.id === 'ticket_type__in');
      if (ticketTypeItem) {
        const ticketTypeMap = data.reduce<Record<string, string>>(
          (result, item) => Object.assign(result, { [item.key]: item.value }),
          {},
        );
        ticketTypeItem.values?.forEach((valueItem) => Object.assign(valueItem, { name: ticketTypeMap[valueItem.id] }));
      }
    },
  });

  const fetchTableData = () => {
    const dateParams =
      daterange.value.filter((item) => item).length === 0
        ? {}
        : {
            create_at__gte: format(new Date(daterange.value[0]), 'yyyy-MM-dd HH:mm:ss'),
            create_at__lte: format(new Date(daterange.value[1]), 'yyyy-MM-dd HH:mm:ss'),
          };
    tableRef.value!.fetchData({
      ...dateParams,
      ...getSearchSelectorParams(searchValue.value),
    });
  };

  const getMenuList = async (item: ISearchItem | undefined, keyword: string) => {
    if (item?.id !== 'operator' && keyword) {
      return getMenuListSearch(item, keyword, searchData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map((value) => value.id);
      return searchData.value.filter((item) => !selected.includes(item.id));
    }

    // 远程加载执行人
    if (item.id === 'operator') {
      if (!keyword) {
        return [];
      }
      return getUserList({
        fuzzy_lookups: keyword,
      }).then((res) =>
        res.results.map((item) => ({
          id: item.username,
          name: item.username,
        })),
      );
    }

    // 不需要远层加载
    return searchData.value.find((set) => set.id === item.id)?.children || [];
  };

  // const handleSelection = (key: any, list: Record<number, RedisHotKeyModel>[]) => {
  //   selected.value = list as unknown as RedisHotKeyModel[];
  // };

  const handleClearSearch = () => {
    daterange.value = ['', ''];
    clearSearchValue();
  };

  const handleShowDetail = (data: RedisHotKeyModel) => {
    if (data.status !== 'FINISHED') {
      return;
    }
    isDetailShow.value = true;
    recordList.value = tableRef.value!.getData<RedisHotKeyModel>().filter((item) => item.status === 'FINISHED');
    currentDetailIndex.value = recordList.value.findIndex((item) => item.id === data.id);
  };

  const handleGoTicketDetail = (data: RedisHotKeyModel) => {
    const { href } = router.resolve({
      name: 'bizTicketManage',
      params: {
        ticketId: data.ticket_id,
      },
    });

    window.open(getBusinessHref(href), '_blank');
  };

  const handleToClusterList = (data: RedisHotKeyModel) => {
    const routeName = data.cluster_type === ClusterTypes.REDIS_INSTANCE ? 'DatabaseRedisHaList' : 'DatabaseRedisList';
    const { href } = router.resolve({
      name: routeName,
      query: {
        domain: data.immute_domain,
      },
    });

    window.open(getBusinessHref(href), '_blank');
  };

  const handleToTaskDetail = (row: RedisHotKeyModel) => {
    const { href } = router.resolve({
      name: 'taskHistoryDetail',
      params: {
        root_id: row.root_id,
      },
      query: {
        from: route.name as string,
      },
    });

    window.open(getBusinessHref(href), '_blank');
  };

  // const handleExport = (row?: RedisHotKeyModel) => {
  //   const data = row ? [row] : selected.value;
  //   exportHotKeyAnalysis({ record_ids: data.map((item) => item.id).join(',') }).then(() => {
  //     tableRef.value!.clearSelected();
  //   });
  // };

  const handleExport = (row: RedisHotKeyModel) => {
    exportHotKeyAnalysis({ record_ids: `${row.id}` });
  };
</script>

<style lang="less">
  .redis-hot-key-list {
    .header-action {
      display: flex;
      padding-bottom: 16px;
    }

    .hot-key-task-id {
      .link-icon {
        display: none;
      }

      &:hover {
        .link-icon {
          display: inline;
        }
      }
    }
  }
</style>
