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
      <span style="font-size: 12px; color: #979ba5;">
        {{ t('（从 CMDB 的 DBA 业务空闲机导入）') }}
      </span>
    </div>
    <BkInput
      v-model="searchContent"
      class="search-input"
      :placeholder="t('请输入 IP/IPv6/主机名称 或 选择条件搜索')"
      @change="handleSearch" />
    <div
      :style="{
        position: 'relative',
        height: `${contentHeight - 110}px`,
      }">
      <DbTable
        ref="tableRef"
        :columns="tableColumn"
        :container-height="contentHeight - 110"
        :data-source="fetchListDbaHost"
        :disable-select-method="disableSelectMethod"
        primary-key="host_id"
        :releate-url-query="false"
        selectable
        @clear-search="handleClearSearch"
        @selection="handleSelection">
        <template
          v-if="!searchContent"
          #empty>
          <HostEmpty />
        </template>
      </DbTable>
    </div>
  </div>
</template>
<script setup lang="tsx">
  import {
    onMounted,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type ImportHostModel from '@services/model/db-resource/import-host';
  import { fetchListDbaHost } from '@services/source/dbresourceResource';

  import DbStatus from '@components/db-status/index.vue';

  import HostEmpty from './components/HostEmpty.vue';

  interface Props {
    modelValue: ImportHostModel[],
    contentHeight: number
  }
  interface Emits {
    (e: 'update:modelValue', value: Props['modelValue']): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const tableRef = ref();
  const searchContent = ref('');

  const tableColumn = [
    {
      label: 'IP',
      field: 'ip',
      fixed: 'left',
      width: 150,
    },
    {
      label: 'IPV6',
      field: 'ipv6',
      render: ({ data }: { data: ImportHostModel}) => data.ipv6 || '--',
    },
    {
      label: t('管控区域'),
      field: 'cloud_area.name',
    },
    {
      label: t('Agent 状态'),
      field: 'agent',
      render: ({ data }: { data: ImportHostModel}) => {
        const info = data.alive === 1 ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      label: t('主机名称'),
      field: 'host_name',
    },
    {
      label: 'OS 名称',
      field: 'os_name',
    },
  ];

  // 同步外部的删除操作
  watch(() => props.modelValue, (newModleValue, oldModleValue) => {
    if (newModleValue.length >= oldModleValue.length) {
      return;
    }
    const newValueIdMap = newModleValue.reduce((result, item) => ({
      ...result,
      [item.host_id]: true,
    }), {} as Record<ImportHostModel['host_id'], boolean>);
    oldModleValue.forEach((hostData) => {
      if (!newValueIdMap[hostData.host_id]) {
        tableRef.value.removeSelectByKey(hostData.host_id);
      }
    });
  });

  const disableSelectMethod = (data: ImportHostModel) => {
    if (data.alive !== 1) {
      return t('异常主机不可用');
    }
    if (data.occupancy) {
      return t('主机已被导入');
    }
    return false;
  };
  const fetchData = () => {
    tableRef.value.fetchData({
      search_content: searchContent.value,
    });
  };

  const handleSearch = () => {
    fetchData();
  };

  const handleClearSearch = () => {
    searchContent.value = '';
    fetchData();
  };

  const handleSelection = (key: number[], dataList: ImportHostModel[]) => {
    emits('update:modelValue', dataList);
  };

  onMounted(() => {
    fetchData();
  });
</script>
<style lang="less">
  .export-host-select-panel {
    padding: 16px 24px;

    .title {
      font-size: 20px;
      line-height: 28px;
      color: #313238;
    }

    .search-input {
      margin: 14px 0 12px;
    }
  }
</style>
