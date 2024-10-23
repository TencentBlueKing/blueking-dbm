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
  <div class="permission-retrieve-result">
    <ReusltHead
      v-model="formatType"
      :data="data"
      @export="handleExport"
      @search="handleSearch" />
    <Component
      :is="tableComponent"
      :data="data"
      :db-memo="dbMemo"
      :is-master="isMaster"
      :pagination="pagination"
      :table-max-height="tableMaxHeight"
      @page-limit-change="handleTableLimitChange"
      @page-value-change="handleTablePageChange" />
  </div>
</template>

<script setup lang="tsx">
  import { getAccountPrivs } from '@services/source/mysqlPermissionAccount';

  import { useTableMaxHeight } from '@hooks';

  import ReusltHead from './components/head/Index.vue';
  import DomainTable from './components/table/DomainTable.vue';
  import IpTable from './components/table/IpTable.vue';

  interface Props {
    data?: ServiceReturnType<typeof getAccountPrivs>;
    isMaster: boolean;
    dbMemo: string[];
  }

  interface Emits {
    (e: 'search'): void;
    (e: 'export'): void;
  }

  interface Expose {
    getPaginationParams: () => {
      limit: number;
      offset: number;
    };
    resetPagination: () => void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const formatType = defineModel<string>({
    default: '',
  });

  const tableMaxHeight = useTableMaxHeight(530);

  const pagination = reactive({
    current: 1,
    count: 0,
    limit: 10,
    limitList: [10, 20, 50, 100, 500],
  });

  const tableComponent = computed(() => (formatType.value === 'ip' ? IpTable : DomainTable));

  watch(
    () => props.data?.match_ips_count,
    () => {
      pagination.count = props.data?.match_ips_count ?? 0;
    },
  );

  const handleTablePageChange = (value: number) => {
    pagination.current = value;
    emits('search');
  };

  const handleTableLimitChange = (value: number) => {
    pagination.limit = value;
    handleTablePageChange(1);
  };

  const handleSearch = () => {
    emits('search');
  };

  const handleExport = () => {
    emits('export');
  };

  defineExpose<Expose>({
    getPaginationParams() {
      return {
        limit: pagination.limit,
        offset: pagination.limit * (pagination.current - 1),
      };
    },
    resetPagination() {
      Object.assign(pagination, {
        current: 1,
        count: 0,
      });
    },
  });
</script>

<style lang="less" scoped>
  .permission-retrieve-result {
    :deep(.bk-table-head) {
      .is-head-group {
        padding: 0 16px;
        font-weight: bolder;
        background: #eaebf0;
        color: #313238;

        &:hover {
          background: #dcdee5;
        }
      }

      th {
        border: none;

        .cell {
          background: #f0f1f5;

          &:hover {
            background: #eaebf0;
          }
        }
      }
    }
  }
</style>
