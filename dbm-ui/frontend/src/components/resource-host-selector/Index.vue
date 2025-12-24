<template>
  <BkDialog
    v-test="{ type: 'dialog', value: 'resourceHostSelector' }"
    class="resource-host-selector"
    :close-icon="false"
    :is-show="isShow"
    :width="dialogWidth">
    <template #header>
      <PanelTab v-model="currentPanelTab" />
    </template>
    <div>
      <DbQuickSearch
        v-model="quickSearchValue"
        :data="quickSearchData" />
      <div class="mt-16 host-list-wrapper">
        <PrimaryTable
          :data="tableData"
          :height="contentHeight"
          :loading="isLoading"
          row-key="ip"
          title-ellipsis
          @filter-change="handleFilterChange">
          <TableColumn
            col-key="ip"
            fixed="left"
            title="IP"
            width="180">
            <template #title>
              <span class="ml-40">IP</span>
            </template>
            <template #default="{ row }: { row: DbResourceModel }">
              <BkCheckbox
                v-bk-tooltips="{
                  content: disableHostMethod(row) || t('已选够n台', { n: limit }),
                  disabled: !disableHostMethod(row) && (isInfinity || selectedNum < limit),
                }"
                v-test="{ type: 'checkbox', value: 'resourceHostSelectorRow' }"
                class="host-list-checkbox"
                :disabled="
                  !!disableHostMethod(row) || (!isInfinity && selectedNum === limit && !Boolean(rowSelectMemo[row.ip]))
                "
                label
                :model-value="Boolean(rowSelectMemo[row.ip])"
                @change="() => handleSelectChange(row)" />
              <span class="ml-20">{{ row.ip }}</span>
            </template>
          </TableColumn>
          <TableColumn
            col-key="bk_cloud_name"
            :title="t('管控区域')"
            width="120" />
          <TableColumn
            col-key="agent_status"
            :title="t('Agent 状态')"
            width="120">
            <template #default="{ row }: { row: DbResourceModel }">
              <HostAgentStatus :data="row.agent_status" />
            </template>
          </TableColumn>
          <TableColumn
            col-key="bk_cpu"
            :title="t('资源归属')"
            width="300">
            <template #default="{ row }: { row: DbResourceModel }">
              <ResourceHostOwner :data="row" />
            </template>
          </TableColumn>
          <TableColumn
            col-key="city"
            :filter="filterOption.city"
            :title="t('地域')"
            width="120" />
          <TableColumn
            col-key="subzone_ids"
            :filter="filterOption.subzone_ids"
            :title="t('园区')"
            width="120">
            <template #default="{ row }: { row: DbResourceModel }">
              {{ row.sub_zone || '--' }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="rack_id"
            :title="t('机架')"
            width="120" />
          <TableColumn
            col-key="os_name"
            :title="t('操作系统名称')"
            width="180">
            <template #default="{ row }: { row: DbResourceModel }">
              {{ row.os_name || '--' }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="device_class"
            :filter="filterOption.device_class"
            :title="t('机型')"
            width="120" />
        </PrimaryTable>
        <div class="table-footer">
          <BkPagination
            v-bind="pagination"
            :layout="['total', 'limit', 'list']"
            @change="handlePageValueChange"
            @limit-change="handlePageLimitChange" />
        </div>
      </div>
    </div>
    <template #footer>
      <I18nT
        v-if="!isInfinity"
        class="mr-20"
        keypath="需n台_已选n台"
        style="font-size: 14px; color: #63656e"
        tag="span">
        <span style="font-weight: bold; color: #2dcb56"> {{ limit }} </span>
        <span style="font-weight: bold; color: #3a84ff"> {{ selectedNum }} </span>
      </I18nT>
      <BkButton
        v-bk-tooltips="{
          content: t('还差n台_请先勾选足够的IP', { n: limit - selectedNum }),
          disabled: isInfinity || selectedNum === limit,
        }"
        v-test="{ type: 'button', value: 'resourceHostSelectorConfirm' }"
        :disabled="!isInfinity && selectedNum !== limit"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="ml-8"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import type { HostInfo } from '@services/types';

  import HostAgentStatus from '@components/host-agent-status/Index.vue';
  import ResourceHostOwner from '@components/resource-host-owner/Index.vue';

  import PanelTab from './components/PanelTab.vue';
  import useFetchData from './hooks/use-fetch-data';
  import usequickSearchData from './hooks/use-search-select-data';

  export interface IHost {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    dedicated_biz?: number;
    ip: string;
  }

  export type IValue = DbResourceModel;

  interface Props {
    disableHostMethod?: (params: IValue) => string | boolean;
    limit?: number;
    params?: {
      bk_cloud_ids?: string;
      for_biz?: number;
      for_bizs?: number[];
      hosts?: HostInfo[];
      os_names?: string[];
      os_type?: string;
      resource_type?: string;
      resource_types?: string[];
    };
  }

  type Emits = (e: 'change', value: DbResourceModel[]) => void;

  const props = withDefaults(defineProps<Props>(), {
    disableHostMethod: () => '',
    limit: -1,
    params: () => ({}),
  });

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });
  const modelValue = defineModel<IHost[]>({
    default: () => [],
  });
  const dialogWidth = Math.max(window.innerWidth * 0.8, 800);
  const contentHeight = window.innerHeight * 0.8 - 200;

  const { t } = useI18n();
  const { filterOption, quickSearchData, quickSearchValue } = usequickSearchData(props);
  const {
    fetchData,
    handlePageLimitChange,
    handlePageValueChange,
    loading: isLoading,
    pagination,
    tableData,
  } = useFetchData(props.params);
  const currentPanelTab = ref('host');
  const rowSelectMemo = shallowRef<Record<string, DbResourceModel>>({});

  const selectedNum = computed(() => Object.keys(rowSelectMemo.value).length);
  const isInfinity = computed(() => props.limit === -1);

  const handleFilterChange = (filterValue: Record<string, string>) => {
    // 剔除空值，剔除多余逗号
    const formatFilterValue = Object.fromEntries(
      Object.entries(filterValue)
        .map(([key, value]) => [key, value.replace(/^,+|,+$/g, '').trim()])
        .filter(([, value]) => value !== ''),
    );
    fetchData({
      ...quickSearchValue.value,
      ...formatFilterValue,
    });
  };

  watch(quickSearchValue, () => {
    fetchData(quickSearchValue.value);
  });

  watch(isShow, () => {
    if (!isShow.value) {
      return;
    }
    rowSelectMemo.value = modelValue.value.reduce(
      (result, item) =>
        Object.assign(result, {
          [item.ip]: item,
        }),
      {},
    );
  });

  const handleSelectChange = (data: DbResourceModel) => {
    const latestSelectMemo = { ...rowSelectMemo.value };
    if (latestSelectMemo[data.ip]) {
      delete latestSelectMemo[data.ip];
    } else {
      latestSelectMemo[data.ip] = data;
    }
    rowSelectMemo.value = latestSelectMemo;
  };

  const handleConfirm = () => {
    isShow.value = false;
    const latestValue = Object.values(rowSelectMemo.value);
    modelValue.value = latestValue;
    emits('change', latestValue);
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .resource-host-selector {
    .bk-dialog-header {
      padding: 0;
    }

    .host-title {
      display: flex;
      height: 32px;
      margin: 0 16px;
      color: #3a84ff;
      background: #e1ecff;
      align-items: center;
    }

    .host-list-wrapper {
      border: 1px solid var(--td-component-border);

      .host-list-checkbox {
        transform: translateY(2px);
      }
    }

    .table-footer {
      position: relative;
      z-index: 1;
      display: flex;
      height: 60px;
      padding: 0 16px;
      margin-top: -1px;
      background: #fff;
      border-top: 1px solid var(--td-component-border);
      align-items: center;

      .bk-pagination {
        width: 100%;

        & > .is-last {
          margin-left: auto;
        }
      }
    }
  }
</style>
