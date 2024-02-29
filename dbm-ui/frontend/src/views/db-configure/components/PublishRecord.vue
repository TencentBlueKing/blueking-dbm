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
  <div class="publish-record">
    <BkLoading
      :loading="state.loading"
      :z-index="12">
      <DbOriginalTable
        :columns="columns"
        :data="state.data.versions"
        :is-anomalies="state.isAnomalies"
        :max-height="tableMaxHeight"
        @refresh="fetchConfigVersionList" />
    </BkLoading>

    <BkSideslider
      v-model:isShow="sideState.isShow"
      quick-close
      :width="960">
      <template #header>
        <div class="custom-slider-header">
          <span>{{ $t('发布记录详情') }}</span>
          <BkSelect
            v-model="sideState.title"
            :clearable="false"
            filterable
            :input-search="false">
            <BkOption
              v-for="item of state.data.versions"
              :key="item.created_at"
              :label="item.created_at"
              :value="item.created_at" />
          </BkSelect>
        </div>
      </template>
      <BkLoading
        :loading="sideState.loading"
        :z-index="12">
        <DbCard :title="$t('基本信息')">
          <EditInfo
            :columns="baseColumns"
            :data="sideState.data"
            readonly />
        </DbCard>
        <DbCard
          class="params-card"
          :title="$t('参数配置')">
          <ReadonlyTable
            :data="sideState.data.configs"
            :is-anomalies="sideState.isAnomalies"
            is-record
            :level="props.fetchParams.level_name"
            @refresh="fetchVersionDetails(sideState.title)" />
        </DbCard>
      </BkLoading>
    </BkSideslider>
  </div>
</template>

<script setup lang="tsx">
  import type { Column } from 'bkui-vue/lib/table/props';
  import { useI18n } from 'vue-i18n';

  import {
    getConfigVersionDetails,
    getConfigVersionList,
  } from '@services/source/configs';

  import { useTableMaxHeight } from '@hooks';

  import EditInfo, {
    type InfoColumn,
  } from '@components/editable-info/index.vue';

  import ReadonlyTable from './ReadonlyTable.vue';

  import type { TableColumnRender } from '@/types/bkui-vue';

  type ConfigVersionDetails = ServiceReturnType<typeof getConfigVersionDetails>
  type ConfigVersionListResult = ServiceReturnType<typeof getConfigVersionList>

  interface Props {
    fetchParams: ServiceParameters<typeof getConfigVersionDetails>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableMaxHeight = useTableMaxHeight(194);

  const state = reactive({
    data: {
      versions: [] as ConfigVersionListResult['versions'],
    } as ConfigVersionListResult,
    loading: false,
    isAnomalies: false,
  });

  /**
   * table columns
   */
  const columns: Column[] = [{
    label: t('发布时间'),
    field: 'created_at',
    render: ({ cell, data }: TableColumnRender) => (
      <bk-button text theme="primary" onClick={handleToDetails.bind(this, data)}>{cell}</bk-button>
    ),
  }, {
    label: t('发布人'),
    field: 'created_by',
  }, {
    label: t('数据库版本'),
    field: 'conf_file',
  }, {
    label: t('修改项'),
    field: 'rows_affected',
  }, {
    label: t('备注'),
    field: 'description',
  }];

  /**
   * 设置 side slider
   */
  const sideState = reactive({
    isShow: false,
    loading: false,
    isAnomalies: false,
    data: {
      configs: [] as any[],
    } as ConfigVersionDetails,
    title: '',
  });
  const handleToDetails = (row: ConfigVersionListResult['versions'][number]) => {
    sideState.isShow = true;
    sideState.title = row.created_at;
  };

  /**
   * slider base info
   */
  const baseColumns: InfoColumn[][] = [
    [{
      label: t('配置名称'),
      key: 'name',
    }, {
      label: t('描述'),
      key: 'description',
    }, {
      label: t('数据库版本'),
      key: 'version',
    }, {
      label: t('发布备注'),
      key: 'publish_description',
    }],
    [{
      label: t('发布时间'),
      key: 'created_at',
    }, {
      label: t('发布人'),
      key: 'created_by',
    }],
  ];

  /**
   * 查询配置发布历史记录
   */
  const fetchConfigVersionList = () => {
    state.loading = true;
    getConfigVersionList(props.fetchParams)
      .then((res) => {
        state.data = res;
        state.isAnomalies = false;
      })
      .catch(() => {
        state.data.versions = [];
        state.isAnomalies = true;
      })
      .finally(() => {
        state.loading = false;
      });
  };

  watch(() => props.fetchParams, () => {
    fetchConfigVersionList();
  }, { immediate: true, deep: true });

  const fetchVersionDetails = (createdAt: string) => {
    const versionInfo = state.data.versions.find(item => item.created_at === createdAt);
    if (versionInfo) {
      sideState.data = {
        configs: [] as any[],
      } as ConfigVersionDetails;
      fetchConfigVersionDetails(versionInfo.revision);
    }
  };

  /**
   *  查询配置发布记录详情
   */
  watch(() => sideState.title, (value, old) => {
    if (value && value !== old) {
      fetchVersionDetails(value);
    }
  }, { immediate: true });

  const fetchConfigVersionDetails = (revision: string) => {
    if (!revision) return;

    sideState.loading = true;
    const params = {
      ...props.fetchParams,
      revision,
    };
    getConfigVersionDetails(params)
      .then((res) => {
        sideState.data = res;
        sideState.isAnomalies = false;
      })
      .catch(() => {
        sideState.data = {
          configs: [] as any[],
        } as ConfigVersionDetails;
        sideState.isAnomalies = true;
      })
      .finally(() => {
        sideState.loading = false;
      });
  };
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .publish-record {
    height: 100%;

    .bk-nested-loading {
      height: 100%;
    }

    .bk-table {
      height: var(--height);
    }
  }

  :deep(.db-card) {
    box-shadow: none;
  }

  .params-card {
    padding: 0 24px;
  }

  .custom-slider-header {
    padding-top: 14px;
    line-height: normal;
    .flex-center();

    .bk-select {
      margin-left: 8px;

      :deep(.bk-input) {
        border-color: transparent;

        input {
          background-color: #f5f7fa;
        }
      }
    }
  }
</style>
