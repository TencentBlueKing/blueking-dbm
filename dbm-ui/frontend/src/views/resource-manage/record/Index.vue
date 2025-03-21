<template>
  <div class="resource-pool-operation-record-page">
    <div class="header-action mb-16">
      <BkDatePicker
        v-model="operationDateTime"
        append-to-body
        clearable
        :placeholder="t('请选择操作时间')"
        type="datetimerange"
        @change="handleDateChange" />
      <DbSearchSelect
        class="ml-8"
        :data="searchSelectData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px"
        unique-select
        :validate-values="validateSearchValues"
        value-behavior="need-key"
        @change="handleSearchValueChange" />
    </div>
    <DbTable
      ref="tableRef"
      :data-source="dataSource"
      releate-url-query
      :show-overflow="false"
      :show-settings="false"
      @clear-search="handleClearSearch"
      @column-filter="columnFilterChange"
      @column-sort="columnSortChange">
      <BkTableColumn
        field="ip"
        fixed="left"
        label="IP"
        :width="150">
      </BkTableColumn>
      <BkTableColumn
        field="events"
        :filters="operationTypeFilters"
        :label="t('操作类型')"
        :width="130">
        <template #default="{ data }: { data: MachineEventModel }">
          {{ data.eventDisplay }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="updater"
        :label="t('操作人')"
        show-overflow="tooltip"
        :width="120">
      </BkTableColumn>
      <BkTableColumn
        field="updateAtDisplay"
        :label="t('操作时间')"
        :width="200">
      </BkTableColumn>
      <BkTableColumn
        field="bk_biz_name"
        :label="t('所属业务')"
        :min-width="180">
      </BkTableColumn>
      <BkTableColumn
        field="ticket"
        :label="t('关联单据')"
        :min-width="200">
        <template #default="{ data }: { data: MachineEventModel }">
          <RouterLink
            v-if="data.ticket"
            target="_blank"
            :to="{
              name: 'bizTicketManage',
              params: {
                ticketId: data.ticket,
              },
            }">
            {{ data.ticket_type_display }}
          </RouterLink>
          <span v-else>--</span>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="clusters"
        :label="t('集群')"
        :min-width="300"
        show-overflow="tooltip">
        <template #default="{ data }: { data: MachineEventModel }">
          {{ data.clusters.length ? data.clusters.map((item) => item.immute_domain).join(', ') : '--' }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="event"
        :label="t('操作明细')"
        :min-width="300">
        <template #default="{ data }: { data: MachineEventModel }">
          <OperationDetail :data="data" />
        </template>
      </BkTableColumn>
    </DbTable>
  </div>
</template>
<script setup lang="tsx">
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MachineEventModel from '@services/model/db-resource/machineEvent';
  import { getMachineEvents } from '@services/source/dbdirty';
  import { getTicketTypes } from '@services/source/ticket';

  import { useLinkQueryColumnSerach } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { machineEventsDisplayMap } from '@common/const/machineEvents';

  import OperationDetail from '@views/resource-manage/common/components/operation-detail/Index.vue';

  import { getMenuListSearch, getSearchSelectorParams } from '@utils';

  const { t } = useI18n();
  const globalBizStore = useGlobalBizs();
  const {
    clearSearchValue,
    // columnCheckedMap,
    columnFilterChange,
    columnSortChange,
    handleSearchValueChange,
    searchValue,
    sortValue,
    validateSearchValues,
  } = useLinkQueryColumnSerach({
    attrs: [],
    fetchDataFn: () => fetchData(),
    searchType: 'resource_record',
  });

  const dataSource = getMachineEvents;

  const tableRef = ref();
  const operationDateTime = ref<[string, string]>([
    dayjs().subtract(7, 'day').format('YYYY-MM-DD HH:mm:ss'),
    dayjs().format('YYYY-MM-DD HH:mm:ss'),
  ]);
  const ticketTypes = ref<Array<{ id: string; name: string }>>([]);

  const searchSelectData = computed(
    () =>
      [
        {
          id: 'ips',
          multiple: true,
          name: 'IP',
        },
        {
          children: Object.entries(machineEventsDisplayMap).map(([key, value]) => ({ id: key, name: value })),
          id: 'events',
          multiple: true,
          name: t('操作类型'),
        },
        {
          id: 'operator',
          name: t('操作人'),
        },
        {
          // multiple: true,
          children: globalBizStore.bizs.map((item) => ({ id: item.bk_biz_id, name: item.name })),
          id: 'bk_biz_id',
          name: t('所属业务'),
        },
        {
          id: 'domain',
          multiple: true,
          name: t('集群'),
        },
        // {
        //   name: t('单据类型'),
        //   id: 'ticket_types',
        //   multiple: true,
        //   children: ticketTypes.value,
        // },
        // {
        //   name: t('关联单据'),
        //   id: 'ticket',
        // },
      ] as ISearchItem[],
  );

  const operationTypeFilters = Object.entries(machineEventsDisplayMap).map(([key, value]) => ({
    label: value,
    value: key,
  }));

  useRequest(getTicketTypes, {
    defaultParams: [
      {
        is_apply: 1,
      },
    ],
    onSuccess(data) {
      ticketTypes.value = data.map((item) => ({
        id: item.key,
        name: item.value,
      }));
    },
  });

  const getMenuList = async (item: ISearchItem | undefined, keyword: string) => {
    if (item?.id !== 'operator' && keyword) {
      return getMenuListSearch(item, keyword, searchSelectData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map((value) => value.id);
      return searchSelectData.value.filter((item) => !selected.includes(item.id));
    }

    // 不需要远层加载
    return searchSelectData.value.find((set) => set.id === item.id)?.children || [];
  };

  // 获取数据
  const fetchData = () => {
    const searchParams = getSearchSelectorParams(searchValue.value);
    const [beginTime, endTime] = operationDateTime.value;
    tableRef.value.fetchData({
      bk_biz_id: searchParams.bk_biz_id,
      ...searchParams,
      ...sortValue,
      create_at__gte: beginTime ? dayjs(beginTime).format('YYYY-MM-DD HH:mm:ss') : '',
      create_at__lte: endTime ? dayjs(endTime).format('YYYY-MM-DD HH:mm:ss') : '',
    });
  };

  // 切换时间
  const handleDateChange = () => {
    fetchData();
  };

  // 清空搜索条件
  const handleClearSearch = () => {
    operationDateTime.value = ['', ''];
    clearSearchValue();
  };
</script>

<style lang="less">
  .resource-pool-operation-record-page {
    .header-action {
      display: flex;
    }
  }
</style>
