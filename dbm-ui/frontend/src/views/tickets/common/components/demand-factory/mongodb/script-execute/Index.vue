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
  <div
    class="ticket-details__info">
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('脚本来源') }}：</span>
        <span class="ticket-details__item-value">
          {{ ticketDetails.details.mode === 'file' ? t('脚本文件') : t('手动输入') }}
        </span>
      </div>
      <div
        class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('脚本执行内容') }}：</span>
        <BkButton
          text
          theme="primary"
          @click="handleClickFile">
          {{ t('点击查看') }}
        </BkButton>
      </div>
    </div>
    <div class="mysql-table">
      <div
        v-if="clusterState.tableProps.data.length > 0"
        class="mysql-table__item">
        <span>{{ t('目标集群') }}：</span>
        <DBCollapseTable
          :show-icon="false"
          style="width: 800px;"
          :table-props="clusterState.tableProps"
          :title="clusterState.clusterType" />
      </div>
    </div>
    <BkSideslider
      class="sql-log-sideslider"
      :is-show="isShow"
      render-directive="if"
      :title="t('执行脚本变更_内容详情')"
      :width="960"
      :z-index="99999"
      @closed="handleClose">
      <div
        v-if="(uploadFileList.length > 1)"
        class="editor-layout">
        <div class="editor-layout-left">
          <RenderFileList
            v-model="selectFileName"
            :data="uploadFileList"
            @sort="handleFileSortChange" />
        </div>
        <div class="editor-layout-right">
          <RenderFileContent
            :model-value="currentFileContent"
            readonly
            :title="selectFileName" />
        </div>
      </div>
      <template v-else>
        <RenderFileContent
          :model-value="currentFileContent"
          readonly
          :title="uploadFileList.toString()" />
      </template>
    </BkSideslider>
  </div>
</template>

<script setup lang="tsx">
  import type { TablePropTypes } from 'bkui-vue/lib/table/props';
  import { useI18n } from 'vue-i18n';

  import type { ResourceItem } from '@services/types';
  import type { TicketDetails } from '@services/types/ticket';

  import { useDefaultPagination } from '@hooks';

  import DBCollapseTable from '@components/db-collapse-table/DBCollapseTable.vue';

  import RenderFileContent from './components/RenderFileContent.vue';
  import RenderFileList from './components/SqlFileList.vue';

  interface MongoScriptExecuteDetails {
    clusters: Record<string, {
      id: number;
      tag: {
        name: string;
        type: string;
        bk_biz_id: number;
      }[];
      name: string;
      alias: string;
      phase: string;
      region: string;
      status: string;
      creator: string;
      updater: string;
      bk_biz_id: number;
      time_zone: string;
      bk_cloud_id: number;
      cluster_type: string;
      db_module_id: number;
      immute_domain: string;
      major_version: string;
      cluster_type_name: string;
      disaster_tolerance_level: string;
    }>;
    cluster_ids: number[];
    mode: string;
    scripts: {
      name: string,
      content: string,
    }[];
  }

  interface Props {
    ticketDetails: TicketDetails<MongoScriptExecuteDetails>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const selectFileName = ref('');
  const isShow = ref(false);

  const fileContentMap = shallowRef<Record<string, string>>({});
  const uploadFileList = shallowRef<Array<string>>([]);

  const clusterState = reactive({
    clusterType: '',
    tableProps: {
      data: [] as ResourceItem[],
      pagination: useDefaultPagination(),
      columns: [
        {
          label: t('集群'),
          field: 'immute_domain',
          showOverflowTooltip: true,
          render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
        },
        {
          label: t('类型'),
          field: 'cluster_type_name',
          render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
        },
        {
          label: t('状态'),
          field: 'status',
          render: ({ cell }: { cell: string }) => {
            const text = cell === 'normal' ? t('正常') : t('异常');
            const icon = cell === 'normal' ? 'normal' : 'abnormal';
            return <span>
            <db-icon svg type={icon} style="margin-right: 5px;" />
            {text}
          </span>;
          },
        },
      ],
    } as unknown as TablePropTypes,
  });

  const currentFileContent = computed(() => fileContentMap.value[selectFileName.value] || '');

  const {
    clusters,
    cluster_ids: clusterIds,
    scripts,
  } = props.ticketDetails.details;

  Object.assign(clusterState.tableProps, {
    data: clusterIds.map(id => clusters[id]),
  });

  // 查看日志详情
  function handleClickFile() {
    isShow.value = true;
    uploadFileList.value = scripts.map(item => item.name);

    fileContentMap.value = scripts.reduce((result, fileInfo) => Object.assign(result, {
      [fileInfo.name]: fileInfo.content,
    }), {} as Record<string, string>);

    selectFileName.value = scripts[0].name;
  }

  function handleClose() {
    isShow.value = false;
  }

  const handleFileSortChange = (list: string[]) => {
    uploadFileList.value = list;
  };

</script>

<style lang="less" scoped>
  @import "@views/tickets/common/styles/ticketDetails.less";

  .sql-mode-execute {
    i {
      font-size: 16px;
      vertical-align: middle;
    }

    span {
      margin: 0 0 2px 2px;
      border-bottom: 1px dashed #313238;

      &:hover {
        cursor: pointer;
      }
    }
  }

  .mysql-table {
    &__item {
      display: flex;
      margin-bottom: 20px;
    }

    span {
      display: inline;
      min-width: 160px;
      text-align: right;
    }
  }

  :deep(.bk-modal-content) {
    height: 100%;
    padding: 15px;
  }

  .sql-log-sideslider {
    .editor-layout {
      display: flex;
      width: 100%;
      height: 100%;
      background: #2e2e2e;

      .editor-layout-left {
        width: 238px;
      }

      .editor-layout-right {
        position: relative;
        height: 100%;
        flex: 1;
      }
    }
  }

</style>
