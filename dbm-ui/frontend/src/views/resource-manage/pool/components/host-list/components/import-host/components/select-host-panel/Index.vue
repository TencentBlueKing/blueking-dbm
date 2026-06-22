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
  <div class="export-host-select-panel">
    <div class="title">
      {{ t('导入主机') }}
      <span style="font-size: 12px; color: #979ba5">
        （
        <I18nT
          keypath="从「source」业务 CMDB 空闲机模块导入，导入完成后 CMDB 位置将转移至「defalut」业务"
          tag="span">
          <template #source>
            {{ globalBizsStore.bizIdMap.get(bizId)?.name }}
          </template>
          <template #defalut>
            {{ globalBizsStore.bizIdMap.get(defaultBizId)?.name }}
          </template>
        </I18nT>
        ）
      </span>
    </div>
    <div class="search-input">
      <IpSearch
        v-model="searchContent"
        class="mr-8"
        style="flex: 1"
        @clear="fetchData"
        @search="fetchData" />
      <DbQuickSearch
        v-model="quickSearchValue"
        :data="quickSearchData"
        :placeholder="t('搜索主要负责人 、机型 、Agent 状态、地域、园区、操作系统名称')"
        style="width: 635px; margin-left: auto"
        @change="handleQuickSearchChange" />
    </div>
    <DbTable
      ref="tableRef"
      :container-height="contentHeight - 110"
      :data-source="fetchListDbaHost"
      :disable-select-method="disableSelectMethod"
      row-key="host_id"
      selectable
      :selected="modelValue"
      @clear-search="handleClearSearch"
      @selection="handleSelection">
      <TableColumn
        col-key="ip"
        fixed="left"
        title="IP"
        :width="150" />
      <TableColumn
        col-key="cloud_area.name"
        :title="t('管控区域')" />
      <TableColumn
        col-key="agent"
        :title="t('Agent 状态')">
        <template #default="{ row }: { row: HostInfo }">
          <DbStatus :theme="row.alive === 1 ? 'success' : 'danger'">
            {{ row.alive === 1 ? t('正常') : t('异常') }}
          </DbStatus>
        </template>
      </TableColumn>
      <TableColumn
        col-key="operator"
        :title="t('主要负责人')"
        :width="150" />
      <TableColumn
        col-key="bk_idc_city_name"
        :title="t('地域')">
        <template #default="{ row }: { row: HostInfo }">
          {{ row.bk_idc_city_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_sub_zone"
        :title="t('园区')">
        <template #default="{ row }: { row: HostInfo }">
          {{ row.bk_sub_zone || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_rack_id"
        :title="t('机架')">
        <template #default="{ row }: { row: HostInfo }">
          {{ row.bk_rack_id || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="os_name"
        :title="t('操作系统名称')">
        <template #default="{ row }: { row: HostInfo }">
          {{ row.os_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_svr_device_class_name"
        :title="t('机型')">
        <template #default="{ row }: { row: HostInfo }">
          {{ row.bk_svr_device_class_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_cpu"
        :title="t('CPU（核）')">
        <template #default="{ row }: { row: HostInfo }">
          {{ row.bk_cpu || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_mem"
        :title="t('内存（G）')">
        <template #default="{ row }: { row: HostInfo }">
          {{ row.bk_mem ? (row.bk_mem / 1024).toFixed(2) : '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_disk"
        :title="t('磁盘总容量（G）')"
        width="120">
        <template #default="{ row }: { row: HostInfo }">
          {{ row.bk_disk ? (row.bk_disk / 1024).toFixed(2) : '--' }}
        </template>
      </TableColumn>
      <template #empty>
        <HostEmpty :bk-biz-id="bizId" />
      </template>
    </DbTable>
  </div>
</template>
<script setup lang="tsx">
  import { onMounted, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { fetchListDbaHost } from '@services/source/dbresourceResource';
  import type { HostInfo } from '@services/types';

  import { useGlobalBizs, useSystemEnviron } from '@stores';

  import { batchSplitRegex } from '@common/regex';

  import DbStatus from '@components/db-status/index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import IpSearch from '@views/resource-manage/common/components/ip-search/Index.vue';

  import HostEmpty from './components/HostEmpty.vue';
  import { useQuickSearch } from './useQuickSearch';

  interface Props {
    contentHeight: number;
    modelValue: HostInfo[];
  }

  type Emits = (e: 'update:modelValue', value: Props['modelValue']) => void;

  interface Expose {
    getValue: () => Promise<{ bk_biz_id: number }>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();
  const systemEnvironStore = useSystemEnviron();
  const { quickSearchData, quickSearchValue } = useQuickSearch();

  const isBusiness = route.name === 'BizResourcePool';
  const defaultBizId = systemEnvironStore.urls.RESOURCE_INDEPENDENT_BIZ;

  const { t } = useI18n();

  const tableRef = ref();
  const searchContent = ref('');
  const bizId = ref(isBusiness ? globalBizsStore.currentBizId : defaultBizId);

  // 同步外部的删除操作
  watch(
    () => props.modelValue,
    (newModleValue, oldModleValue) => {
      if (newModleValue.length >= oldModleValue.length) {
        return;
      }
      const newValueIdMap = newModleValue.reduce<Record<HostInfo['host_id'], boolean>>(
        (result, item) => ({
          ...result,
          [item.host_id]: true,
        }),
        {},
      );
      oldModleValue.forEach((hostData) => {
        if (!newValueIdMap[hostData.host_id]) {
          tableRef.value.removeSelectByKey(hostData.host_id);
        }
      });
    },
  );

  // watch(bizId, () => {
  //   fetchData();
  // });

  const fetchData = () => {
    tableRef.value.fetchData({
      bk_biz_id: bizId.value,
      search_content: searchContent.value.split(batchSplitRegex).join(','),
      ...quickSearchValue.value,
    });
  };

  const disableSelectMethod = (data: HostInfo) => {
    if (data.alive !== 1) {
      return t('异常主机不可用');
    }
    if (data.occupancy) {
      return t('主机已被导入');
    }
    return false;
  };

  const handleQuickSearchChange = () => {
    fetchData();
  };

  const handleClearSearch = () => {
    searchContent.value = '';
    quickSearchValue.value = {};
    fetchData();
  };

  const handleSelection = (_key: string[], dataList: HostInfo[]) => {
    emits('update:modelValue', dataList);
  };

  onMounted(() => {
    fetchData();
  });

  defineExpose<Expose>({
    getValue() {
      return Promise.resolve({
        bk_biz_id: bizId.value,
      });
    },
  });
</script>
<style lang="less">
  .export-host-select-panel {
    padding: 16px 24px;

    .title {
      display: flex;
      font-size: 20px;
      line-height: 28px;
      color: #313238;
      align-items: center;
    }

    .search-input {
      display: flex;
      align-items: center;
      margin: 14px 0 12px;
    }
  }
</style>
