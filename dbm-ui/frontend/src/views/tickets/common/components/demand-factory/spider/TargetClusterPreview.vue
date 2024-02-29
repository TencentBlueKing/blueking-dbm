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
  <BkDialog
    class="cluster-preview-dialog"
    :is-show="isShow"
    :title="title"
    @closed="handleClose">
    <div class="cluster-preview-content">
      <DbSearchSelect
        v-model="listState.filters.search"
        class="mb-16"
        :data="searchSelectData"
        :placeholder="t('请输入域名_集群名称_所属DB模块')"
        unique-select
        @change="handleChangeValues" />
      <BkLoading :loading="listState.isLoading">
        <DbOriginalTable
          :columns="columns"
          :data="listState.data"
          :height="474"
          :is-anomalies="listState.isAnomalies"
          :is-searching="listState.filters.search.length > 0"
          @clear-search="handleClearSearch"
          @page-limit-change="handeChangeLimit"
          @page-value-change="handleChangePage"
          @refresh="fetchCluster" />
      </BkLoading>
    </div>
    <template #footer>
      <BkButton @click="handleClose">
        {{ t('关闭') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getModules } from '@services/source/cmdb';
  import type {
    MysqlAuthorizationDetails,
    TicketDetails,
  } from '@services/types/ticket';

  import { useDefaultPagination } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';

  import { useTargetClusterData } from '@views/tickets/common/hooks/useTargetClusterData';

  interface Props {
    title: string
    ticketDetails: TicketDetails<MysqlAuthorizationDetails>
  }

  const props = defineProps<Props>();
  const isShow = defineModel<boolean>({
    required: true,
  });

  const { t } = useI18n();

  const {
    listState,
    searchSelectData,
    fetchCluster,
    handleChangePage,
    handeChangeLimit,
    handleChangeValues,
  } = useTargetClusterData(props.ticketDetails);

  const globalBizsStore = useGlobalBizs();

  const columns = [
    {
      label: t('域名'),
      field: 'master_domain',
      showOverflowTooltip: true,
    },
    {
      label: t('集群'),
      field: 'cluster_name',
      showOverflowTooltip: true,
    },
    {
      label: t('所属DB模块'),
      field: 'db_module_name',
      showOverflowTooltip: true,
    },
    {
      label: t('状态'),
      field: 'status',
      filter: true,
      render: ({ cell }: { cell: 'normal' | 'abnormal' }) => {
        const text = {
          normal: t('正常'),
          abnormal: t('异常'),
        };
        return <DbStatus theme={cell === 'normal' ? 'success' : 'danger'}>{ text[cell] }</DbStatus>;
      },
    },
  ];

  watch(isShow, (newVal) => {
    if (newVal) {
      handleChangePage(1);
    }
  });

  const handleClearSearch = () =>  {
    listState.filters.search = [];
    handleChangePage(1);
  };

  const handleClose = () => {
    isShow.value = false;
    listState.filters.search = [];
    listState.pagination = useDefaultPagination();
  };

  useRequest(getModules, {
    defaultParams: [
      {
        bk_biz_id: globalBizsStore.currentBizId,
        cluster_type: ClusterTypes.TENDBCLUSTER,
      },
    ],
    onSuccess(res) {
      listState.dbModuleList = res.map(item => ({
        id: item.db_module_id,
        name: item.name,
      }));
    },
  });
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .cluster-preview-dialog {
    width: 80%;
    max-width: 1600px;
    min-width: 1200px;
  }

  .cluster-preview-content {
    padding-bottom: 24px;
  }
</style>
