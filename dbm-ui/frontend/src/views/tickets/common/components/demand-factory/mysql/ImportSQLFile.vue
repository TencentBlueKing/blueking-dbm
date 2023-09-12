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
        <span class="ticket-details__item-label">{{ $t('所属业务') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails.bk_biz_name }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('业务英文名') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails.db_app_abbr }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('SQL来源') }}：</span>
        <span class="ticket-details__item-value">{{ importModeType }}</span>
      </div>
      <div
        class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('SQL执行内容') }}：</span>
        <BkButton
          text
          theme="primary"
          @click="handleClickFile">
          {{ $t('点击查看') }}
        </BkButton>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('字符集') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails.details.charset }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('执行前备份') }}：</span>
        <span class="ticket-details__item-value">{{ isBackup }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('执行模式') }}：</span>
        <span class="ticket-details__item-value sql-mode-execute">
          <i :class="ticketModeData.icon" />
          <span v-bk-tooltips="ticketModeData.tips">{{ ticketModeData.text }}</span>
        </span>
      </div>
      <div
        v-if="ticketDetails.details.ticket_mode.trigger_time"
        class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('执行时间') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails.details.ticket_mode.trigger_time }}</span>
      </div>
    </div>
    <div class="mysql-table">
      <div
        v-if="clusterState.tableProps.data.length > 0"
        class="mysql-table__item">
        <span>{{ $t('目标集群') }}：</span>
        <DBCollapseTable
          :show-icon="false"
          style="width: 800px;"
          :table-props="clusterState.tableProps"
          :title="clusterState.clusterType" />
      </div>
      <div class="mysql-table__item">
        <span>{{ $t('目标DB') }}：</span>
        <DbOriginalTable
          :columns="targetDB"
          :data="dataList"
          style="width: 800px;" />
      </div>
      <div
        v-if="ticketDetails?.details?.backup?.length"
        class="mysql-table__item">
        <span>{{ $t('备份设置') }}：</span>
        <DbOriginalTable
          :columns="backupConfig"
          :data="backupList"
          style="width: 800px;" />
      </div>
    </div>
    <BkSideslider
      class="sql-log-sideslider"
      :is-show="isShow"
      render-directive="if"
      :title="$t('执行SQL变更_内容详情')"
      :width="960"
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
          <Editor
            v-model="logDetailsData.content"
            readonly
            :title="selectFileName" />
        </div>
      </div>
      <template v-else>
        <Editor
          :model-value="logDetailsData.content"
          readonly
          :title="uploadFileList.toString()" />
      </template>
    </BkSideslider>
  </div>
</template>

<script setup lang="tsx">
  import type { TablePropTypes } from 'bkui-vue/lib/table/props';
  import { useI18n } from 'vue-i18n';

  import { getResources } from '@services/clusters';
  import { batchFetchFile } from '@services/mysqlCluster';
  import type { ResourceItem } from '@services/types/clusters';
  import type {
    MySQLImportSQLFileDetails,
    TicketDetails,
  } from '@services/types/ticket';

  import { useDefaultPagination } from '@hooks';

  import { DBTypes } from '@common/const';

  import DBCollapseTable from '@components/db-collapse-table/DBCollapseTable.vue';

  import Editor from '@views/mysql/sql-execute/steps/step1/components/sql-file/editor/Index.vue';
  import RenderFileList from '@views/mysql/sql-execute/steps/step1/components/sql-file/local-file/SqlFileList.vue';

  import DbIcon from '@/components/db-icon';

  interface Props {
    ticketDetails: TicketDetails<MySQLImportSQLFileDetails>
  }

  const props = defineProps<Props>();

  type targetDBItem = {
    dbnames: [],
    ignore_dbnames: [],
  }

  type backupDBItem = {
    backup_on: string,
    db_patterns: [],
    table_patterns: [],
  }

  const { t } = useI18n();
  const selectFileName = ref('');
  const uploadFileList = shallowRef<Array<string>>([]);
  const isShow = ref(false);

  const logDetailsData = reactive({
    content: '',
  });

  const clusterState = reactive({
    clusterType: '',
    tableProps: {
      data: [] as ResourceItem[],
      pagination: useDefaultPagination(),
      columns: [{
        label: t('集群'),
        field: 'master_domain',
        showOverflowTooltip: true,
        render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
      }, {
        label: t('类型'),
        field: 'cluster_type',
        render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
      }, {
        label: t('状态'),
        field: 'status',
        render: ({ cell }: { cell: string }) => {
          const text = cell === 'normal' ? t('正常') : t('异常');
          const icon = cell === 'normal' ? 'normal' : 'abnormal';
          return <span>
            <DbIcon svg type={icon} style="margin-right: 5px;" />
            {text}
          </span>;
        },
      }],
    } as unknown as TablePropTypes,
  });

  const targetDB = [{
    label: t('变更的DB'),
    field: 'dbnames',
    showOverflowTooltip: false,
    render: ({ cell }: { cell: string[] }) => (
      <div class="text-overflow" v-overflow-tips={{
          content: cell,
        }}>
        {cell.map(item => <bk-tag>{item}</bk-tag>)}
      </div>
    ),
  }, {
    label: t('忽略的DB'),
    field: 'ignore_dbnames',
    showOverflowTooltip: false,
    render: ({ cell }: { cell: string[] }) => (
      <div class="text-overflow" v-overflow-tips={{
          content: cell,
        }}>
        {cell.length > 0 ? cell.map(item => <bk-tag>{item}</bk-tag>) : '--'}
      </div>
    ),
  }];

  const backupConfig = [{
    label: t('备份DB'),
    field: 'db_patterns',
    showOverflowTooltip: false,
    render: ({ cell }: { cell: string[] }) => (
      <div class="text-overflow" v-overflow-tips={{
          content: cell,
        }}>
        {cell.map(item => <bk-tag>{item}</bk-tag>)}
      </div>
    ),
  }, {
    label: t('备份表名'),
    field: 'table_patterns',
    showOverflowTooltip: false,
    render: ({ cell }: { cell: string[] }) => (
      <div class="text-overflow" v-overflow-tips={{
          content: cell,
        }}>
        {cell.map(item => <bk-tag>{item}</bk-tag>)}
      </div>
    ),
  }];

  // SQL 文件来源
  const importModeType = computed(() => (props.ticketDetails?.details?.import_mode === 'manual' ? t('手动输入') : t('文件导入')));

  // 执行前备份
  const isBackup = computed(() => (props.ticketDetails?.details?.backup?.length ? t('是') : t('否')));

  const ticketModeType = [{
    type: 'manual',
    text: t('手动执行'),
    icon: 'db-icon-manual',
    tips: t('单据审批之后_需要人工确认方可执行'),
  }, {
    type: 'timer',
    text: t('定时执行'),
    icon: 'db-icon-timed-task',
    tips: t('单据审批通过之后_定时执行_无需确认'),
  }];

  // 执行模式
  const ticketModeData = computed(() => {
    const modeType = props.ticketDetails?.details?.ticket_mode?.mode;
    let modeItem: any = {};
    ticketModeType.forEach((item) => {
      if (item.type === modeType) {
        modeItem = item;
      }
    });
    return modeItem;
  });

  // 目标集群
  onBeforeMount(() => {
    const clustersData = props.ticketDetails?.details?.clusters || {};
    const clusterIds = props.ticketDetails?.details?.cluster_ids;
    clusterIds.forEach((id) => {
      const clusterId = clustersData[id].id;
      const clusterType = clustersData[id].cluster_type;
      clusterState.clusterType = clusterType === 'tendbha' ? t('高可用') : t('单节点');
      const { pagination } = clusterState.tableProps;
      const paginationParams = typeof pagination === 'boolean' ? {} : pagination.getFetchParams();
      const params = {
        bk_biz_id: props.ticketDetails.bk_biz_id,
        type: clusterType === 'tendbcluster' ? 'spider' : clusterType,
        cluster_ids: clusterId,
        ...paginationParams,
      };
      getResources<ResourceItem>(DBTypes.MYSQL, params)
        .then((res) => {
          res.results.forEach((item) => {
            clusterState.tableProps.data.push(Object.assign({
              cluster_type: clusterState.clusterType,
            }, item));
          });
        });
    });
  });

  // 目标DB
  const dataList = computed(() => {
    const list: targetDBItem[] = [];
    const dbList = props.ticketDetails?.details?.execute_objects || [];
    dbList.forEach((item) => {
      list.push(Object.assign({
        dbnames: item.dbnames,
        ignore_dbnames: item.ignore_dbnames,
      }));
    });
    return list;
  });

  // 备份设置
  const backupList = computed(() => {
    const list: backupDBItem[] = [];
    const tableList = props.ticketDetails?.details?.backup || [];
    tableList.forEach((item) => {
      list.push(Object.assign({
        backup_on: item.backup_on,
        db_patterns: item.db_patterns,
        table_patterns: item.table_patterns,
      }));
    });
    return list;
  });

  // 查看日志详情
  function handleClickFile() {
    isShow.value = true;
    const uploadSQLFileList = props.ticketDetails?.details?.execute_objects.map(item => item.sql_file);
    uploadFileList.value = uploadSQLFileList;
    const list: string[] = [];
    uploadSQLFileList.forEach((item) => {
      list.push(`${props.ticketDetails.details.path}/${item}`);
    });
    batchFetchFile({
      file_path_list: list,
    }).then((res) => {
      if (res.length > 1) {
        logDetailsData.content = res[0].content;
      } else {
        res.forEach((data: any) => {
          logDetailsData.content = data.content;
        });
      }
    });
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

    .sql-execute-editor {
      height: 100% !important;
    }
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
