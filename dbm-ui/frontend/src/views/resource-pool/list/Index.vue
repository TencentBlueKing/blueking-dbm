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
  <div class="resource-pool-list-page">
    <SearchBox
      style="margin-bottom: 25px;"
      @change="handleSearch" />
    <div class="action-box mt-24 mb-16">
      <BkButton
        class="w88"
        theme="primary"
        @click="handleExportHost">
        {{ t('导入') }}
      </BkButton>
      <BkButton class="ml-8">
        {{ t('批量设置') }}
      </BkButton>
      <BkButton class="ml-8">
        {{ t('批量移除') }}
      </BkButton>
      <div class="quick-search">
        <BkInput
          :placeholder="t('请选择收藏的条件')"
          style="width: 395px;" />
        <div class="quick-serch-btn">
          <DbIcon type="history-2" />
        </div>
      </div>
    </div>
    <DbTable
      ref="tableRef"
      :columns="tableColumn"
      :data-source="dataSource" />
    <ExportHost :is-show="isShowExportHost" />
  </div>
</template>
<script setup lang="ts">
  import {
    onMounted,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { fetchList } from '@services/dbResource';

  import ExportHost from './components/export-host/Index.vue';
  import SearchBox from './components/search-box/Index.vue';

  const { t } = useI18n();

  const dataSource = fetchList;

  const tableRef = ref();

  const tableColumn = [
    {
      label: 'IP',
      field: 'ip',
      fixed: 'left',
      width: 100,
    },
    {
      label: t('云区域'),
      field: 'id',
    },
    {
      label: t('Agent 状态'),
      field: 'id',
      width: 100,
    },
    {
      label: t('专用业务'),
      field: 'id',
      width: 170,
    },
    {
      label: t('专用 DB'),
      field: 'id',
      width: 190,
    },
    {
      label: t('机型'),
      field: 'id',
      width: 150,
    },
    {
      label: t('地域'),
      field: 'id',
      width: 100,
    },
    {
      label: t('园区'),
      field: 'id',
      width: 100,
    },
    {
      label: t('CPU(核)'),
      field: 'id',
      width: 100,
    },
    {
      label: t('内存(G)'),
      field: 'id',
      width: 100,
    },
    {
      label: t('磁盘容量(G)'),
      field: 'id',
      width: 100,
    },
    {
      label: t('机架'),
      field: 'id',
      width: 100,
    },
    {
      label: t('操作'),
      field: 'id',
      width: 100,
    },
  ];

  const isShowExportHost = ref(false);

  const handleSearch = (params: Record<string, any>) => {
    console.log('start search: = ', params);
  };

  const handleExportHost = () => {
    isShowExportHost.value = true;
  };

  onMounted(() => {
    tableRef.value.fetchData();
  });
</script>
<style lang="less">
.resource-pool-list-page {
  .action-box {
    display: flex;

    .quick-search {
      display: flex;
      margin-left: auto;
    }

    .quick-serch-btn {
      display: flex;
      width: 32px;
      height: 32px;
      margin-left: 8px;
      cursor: pointer;
      background: #fff;
      border: 1px solid #c4c6cc;
      border-radius: 2px;
      align-items: center;
      justify-content: center;

      &:hover {
        border-color: #979ba5;
      }
    }
  }
}
</style>
