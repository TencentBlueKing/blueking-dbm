<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div class="platform-config-list-table">
    <div class="mb-16">
      <DbQuickSearch
        v-model="searchValue"
        :data="quickSearchData"
        :placeholder="t('搜索配置名称_配置文件_更新人_描述')"
        style="width: 500px"
        @change="handleQuickSearchChange" />
    </div>
    <DbTable
      ref="tableRef"
      :data-source="dataSource"
      fixed-pagination
      row-key="name"
      @clear-search="handleQuickSearchChange">
      <TableColumn
        col-key="name"
        ellipsis
        :title="t('配置名称')">
        <template #default="{ row }">
          <BkButton
            text
            theme="primary"
            @click="handleToDetail(row)">
            {{ row.name }}
          </BkButton>
        </template>
      </TableColumn>
      <TableColumn
        col-key="version"
        ellipsis
        :title="t('配置文件')" />
      <TableColumn
        col-key="description"
        ellipsis
        :title="t('描述')">
        <template #default="{ row }">
          {{ row.description || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="updated_by"
        :title="t('更新人')">
        <template #default="{ row }">
          {{ row.updated_by || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="updated_at"
        :title="t('更新时间')" />
    </DbTable>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { getPlatformConfigList } from '@services/source/configs';

  import DbTable from '@components/db-table/IndexNew.vue';

  interface Props {
    clusterType: string;
    confType: string;
  }

  const props = defineProps<Props>();

  const router = useRouter();
  const { t } = useI18n();

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const searchValue = ref<Record<string, any>>({});

  const quickSearchData = [
    {
      id: 'name',
      name: t('配置名称'),
      type: 'input' as const,
    },
    {
      id: 'version',
      name: t('配置文件'),
      type: 'input' as const,
    },
    {
      id: 'updated_by',
      name: t('更新人'),
      type: 'input' as const,
    },
    {
      id: 'description',
      name: t('描述'),
      type: 'input' as const,
    },
  ];

  type ConfigItem = ServiceReturnType<typeof getPlatformConfigList>[number];

  const dataSource = (params: { limit: number; offset: number }) => {
    return getPlatformConfigList(
      {
        conf_type: props.confType,
        meta_cluster_type: props.clusterType,
      },
      { permission: 'catch' },
    ).then((res) => {
      let filteredData = res;
      const filters = searchValue.value;
      if (Object.keys(filters).length > 0) {
        filteredData = res.filter((item) =>
          Object.entries(filters).every(([key, val]) => {
            if (!val) return true;
            const search = String(val).toLowerCase();
            const fieldValue = String((item as Record<string, any>)[key] ?? '').toLowerCase();
            return fieldValue.includes(search);
          }),
        );
      }
      const start = params.offset;
      const end = start + params.limit;
      return {
        count: filteredData.length,
        results: filteredData.slice(start, end),
      };
    });
  };

  const handleQuickSearchChange = () => {
    tableRef.value?.fetchData({}, true);
  };

  const handleToDetail = (row: ConfigItem) => {
    router.push({
      name: 'PlatformDbConfigureDetail',
      params: {
        clusterType: props.clusterType,
        confType: props.confType,
        version: row.version,
      },
    });
  };
</script>

<style lang="less" scoped>
  .platform-config-list-table {
    padding: 0 16px;
  }
</style>
