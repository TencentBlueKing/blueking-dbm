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
      :loading="loading"
      @export="handleExport"
      @search="handleSearch" />
    <BkLoading
      :loading="loading"
      :z-index="100">
      <Component
        :is="tableComponent"
        :data="data"
        :options="options"
        :pagination="pagination"
        :table-max-height="tableMaxHeight"
        @page-limit-change="handleTableLimitChange"
        @page-value-change="handleTablePageChange" />
    </BkLoading>
  </div>
</template>

<script setup lang="tsx">
  import { useRequest } from 'vue-request';

  import { getAccountPrivs, getDownloadPrivs } from '@services/source/mysqlPermissionAccount';

  import { useTableMaxHeight } from '@hooks';

  import { AccountTypes, ClusterTypes } from '@common/const';

  import ReusltHead from './components/head/Index.vue';
  import DomainTable from './components/table/DomainTable.vue';
  import IpTable from './components/table/IpTable.vue';

  interface Props {
    options?: {
      ips: string;
      immute_domains: string;
      users: string;
      cluster_type: ClusterTypes;
      account_type: AccountTypes;
      dbs?: string;
      is_master?: boolean;
    };
  }

  interface Emits {
    (e: 'loading-change', value: boolean): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const tableMaxHeight = useTableMaxHeight(530);

  const formatType = ref('ip');

  const pagination = reactive({
    current: 1,
    count: 0,
    limit: 10,
    limitList: [10, 20, 50, 100, 500],
  });

  const tableComponent = computed(() => (formatType.value === 'ip' ? IpTable : DomainTable));

  watch(formatType, () => {
    Object.assign(pagination, {
      current: 1,
      count: 0,
    });
  });

  const {
    run: runGetAccountPrivs,
    data,
    mutate,
    loading,
  } = useRequest(getAccountPrivs, {
    manual: true,
  });

  watch(
    () => props.options,
    () => {
      if (props.options) {
        runGetAccountPrivs(getApiParams());
      } else {
        mutate({
          match_ips_count: 0,
          results: {
            privs_for_ip: null,
            privs_for_cluster: null,
            has_priv: null,
            no_priv: null,
          },
        });
        formatType.value = 'ip';
      }
    },
  );

  watch(data, () => {
    pagination.count = data.value?.match_ips_count ?? 0;
  });

  watch(loading, () => {
    emits('loading-change', loading.value);
  });

  const getApiParams = (isPagination = true) => {
    const params = {
      ...props.options!,
      format_type: formatType.value,
    };
    if (isPagination) {
      Object.assign(params, {
        limit: pagination.limit,
        offset: pagination.limit * (pagination.current - 1),
      });
    }

    delete params.is_master;
    if (!params.dbs) {
      delete params.dbs;
    }
    return params;
  };

  const handleSearch = () => {
    if (!props.options) {
      return;
    }
    runGetAccountPrivs(getApiParams());
  };

  const handleTablePageChange = (value: number) => {
    pagination.current = value;
    handleSearch();
  };

  const handleTableLimitChange = (value: number) => {
    pagination.limit = value;
    handleTablePageChange(1);
  };

  const handleExport = () => {
    getDownloadPrivs(getApiParams(false));
  };
</script>

<style lang="less" scoped>
  .permission-retrieve-result {
    :deep(.bk-table-head) {
      .is-head-group {
        padding: 0 16px;
        font-weight: bolder;
        color: #313238;
        background: #eaebf0;

        &:hover {
          background: #dcdee5;
        }
      }

      th {
        border: none;

        .vxe-cell {
          background: #f0f1f5;

          &:hover {
            background: #eaebf0;
          }
        }
      }
    }
  }
</style>
