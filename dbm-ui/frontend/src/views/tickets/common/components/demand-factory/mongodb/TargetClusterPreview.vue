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
        v-model="searchSelectValue"
        class="mb-16"
        :data="searchSelectData"
        :placeholder="t('请输入域名_集群名称')"
        unique-select
        @change="handleChangeValues" />
      <BkLoading :loading="loading">
        <DbOriginalTable
          :columns="columns"
          :data="mongoList?.results || []"
          :height="474"
          :is-anomalies="isAnomalies"
          :is-searching="searchSelectValue.length > 0"
          :pagination="pagination"
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
  import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getMongoList } from '@services/source/mongodb';

  import { useDefaultPagination } from '@hooks';

  import RenderClusterStatus from '@components/cluster-common/RenderStatus.vue';

  import { getSearchSelectorParams } from '@utils';

  interface Props {
    title: string
    clusterIds?: number[]
  }

  const props = withDefaults(defineProps<Props>(), {
    clusterIds: () => [],
  });
  const isShow = defineModel<boolean>({
    required: true,
  });

  const { t } = useI18n();

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
      label: t('状态'),
      field: 'status',
      render: ({ cell }: { cell: 'normal' | 'abnormal' }) => <RenderClusterStatus data={cell} />,
    },
  ];

  const searchSelectData = [
    {
      name: t('域名'),
      id: 'domain',
    },
    {
      name: t('集群'),
      id: 'name',
    },
  ];

  const isAnomalies = ref(false);
  const searchSelectValue = ref<ISearchValue[]>([]);
  const pagination = ref(useDefaultPagination());

  const {
    data: mongoList,
    run: getMongoListRun,
    loading,
  } = useRequest(getMongoList, {
    manual: true,
    onSuccess(mongoList) {
      pagination.value.count = mongoList.count;
      isAnomalies.value = false;
    },
    onError() {
      pagination.value.count = 0;
      isAnomalies.value = true;
    },
  });

  watch(isShow, (newVal) => {
    if (newVal) {
      handleChangePage(1);
    }
  });

  const fetchCluster = () => {
    getMongoListRun({
      cluster_ids: props.clusterIds,
      ...pagination.value.getFetchParams(),
      ...getSearchSelectorParams(searchSelectValue.value),
    });
  };

  const handleChangePage = (value: number) => {
    pagination.value.current = value;
    fetchCluster();
  };

  const handeChangeLimit = (value: number) => {
    pagination.value.limit = value;
    handleChangePage(1);
  };

  const handleChangeValues = () => {
    nextTick(() => {
      handleChangePage(1);
    });
  };

  const handleClearSearch = () =>  {
    searchSelectValue.value = [];
    handleChangePage(1);
  };

  const handleClose = () => {
    isShow.value = false;
    searchSelectValue.value = [];
    pagination.value = useDefaultPagination();
  };
</script>

<style lang="less" scoped>
  .cluster-preview-dialog {
    width: 80%;
    max-width: 1600px;
    min-width: 1200px;
  }

  .cluster-preview-content {
    padding-bottom: 24px;
  }
</style>
