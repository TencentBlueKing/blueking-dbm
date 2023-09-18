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
  <div class="biz-database">
    <div class="biz-database-operations mb-16">
      <BkInput
        v-model="state.search"
        clearable
        :placeholder="$t('名称_数据库版本_更新人')"
        style="width: 500px;"
        type="search" />
      <BkButton
        v-bk-tooltips="$t('刷新')"
        @click="fetchBusinessConfigList">
        <i class="db-icon-refresh" />
      </BkButton>
    </div>
    <BkLoading
      :loading="state.loading"
      :z-index="12">
      <DbOriginalTable
        class="biz-database__table"
        :columns="columns"
        :data="displayData"
        :is-anomalies="state.isAnomalies"
        :is-searching="!!state.search"
        @clear-search="handleClearSearch"
        @refresh="fetchBusinessConfigList" />
    </BkLoading>
  </div>
</template>

<script setup lang="tsx">
  import type { Column } from 'bkui-vue/lib/table/props';
  import type { ComputedRef, Ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getBusinessConfigList } from '@services/configs';
  import type { ConfigListItem } from '@services/types/configs';

  import { useGlobalBizs } from '@stores';

  import type { TreeData } from '../common/types';

  interface Props {
    confType: string
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const activeTab = inject<Ref<string>>('activeTab');
  const treeNode = inject<ComputedRef<TreeData>>('treeNode');

  /**
   * table 设置
   */
  const columns: Column[] = [{
    label: t('名称'),
    field: 'name',
    render: ({ cell, data }: { cell: string, data: ConfigListItem }) => (
      <a href="javascript:" onClick={() => handleToDetails(data)}>{cell}</a>
    ),
  }, {
    label: t('数据库版本'),
    field: 'version',
    sort: true,
  }, {
    label: t('更新时间'),
    field: 'updated_at',
    sort: true,
  }, {
    label: t('更新人'),
    field: 'updated_by',
    render: ({ cell }: { cell: string }) => cell || '--',
    sort: true,
  }, {
    label: t('操作'),
    field: 'operation',
    render: ({ data }: { data: ConfigListItem }) => (
      <div class="operation">
        <bk-button text theme="primary" class="mr-24" onClick={() => handleToEdit(data)}>{ t('编辑') }</bk-button>
      </div>
    ),
  }];

  const state = reactive({
    loading: false,
    data: [] as ConfigListItem[],
    search: '',
    isAnomalies: false,
  });

  const searchValue = (value: string) => value.toLowerCase().includes(state.search);
  const displayData = computed(() => {
    if (state.search === '') return state.data;

    return state.data.filter((item) => {
      const { name, version, updated_by: updatedBy } = item;
      return searchValue(name) || searchValue(version) || searchValue(updatedBy);
    });
  });

  /**
   * 获取业务配置列表
   */
  const fetchBusinessConfigList = () => {
    if (!activeTab?.value) return;

    state.loading = true;
    const params = {
      meta_cluster_type: activeTab?.value as string,
      conf_type: props.confType,
      bk_biz_id: globalBizsStore.currentBizId,
    };
    getBusinessConfigList(params)
      .then((res) => {
        state.data = res;
        state.isAnomalies = false;
      })
      .catch(() => {
        state.data = [];
        state.isAnomalies = true;
      })
      .finally(() => {
        state.loading = false;
      });
  };
  fetchBusinessConfigList();

  const handleClearSearch = () => {
    state.search = '';
  };

  const changeViewParams = computed(() => ({
    clusterType: activeTab?.value,
    confType: props.confType,
    treeId: treeNode?.value.treeId,
    parentId: treeNode?.value.parentId,
  }));

  /**
   * 查看详情
   */
  const handleToDetails = (row: ConfigListItem) => {
    router.push({
      name: 'DatabaseConfigDetails',
      params: {
        version: row.version,
        ...changeViewParams.value,
      },
    });
  };

  /**
   * 编辑配置
   */
  const handleToEdit = (row: ConfigListItem) => {
    router.push({
      name: 'DatabaseConfigEdit',
      params: {
        version: row.version,
        ...changeViewParams.value,
      },
    });
  };
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .biz-database {
    .biz-database-operations {
      .flex-center();

      justify-content: space-between;

      .bk-button {
        padding: 5px 8px;
      }
    }
  }

  :deep(.biz-database__column-name) {
    display: flex;
    align-items: center;

    .bk-button {
      position: relative;
      padding: 4px 6px;

      &.is-update {
        &::after {
          position: absolute;
          top: 0;
          right: 0;
          width: 6px;
          height: 6px;
          background-color: @bg-danger;
          border-radius: 50%;
          content: "";
        }
      }
    }

    .bk-tag {
      height: 18px;
      margin: 0;
      line-height: 18px;
      flex-shrink: 0;
    }
  }
</style>

