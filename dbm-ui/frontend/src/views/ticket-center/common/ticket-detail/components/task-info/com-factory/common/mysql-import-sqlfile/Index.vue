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
  <InfoList>
    <InfoItem :label="t('所属业务')">
      {{ ticketDetails.bk_biz_name }}
    </InfoItem>
    <InfoItem :label="t('业务英文名')">
      {{ ticketDetails.db_app_abbr }}
    </InfoItem>
    <InfoItem :label="t('字符集')">
      {{ ticketDetails.details.charset }}
    </InfoItem>
    <InfoItem
      v-if="ticketModeData"
      :label="t('执行模式')">
      <DbIcon :type="ticketModeData.icon" />
      <span v-bk-tooltips="ticketModeData.tips">{{ ticketModeData.text }}</span>
    </InfoItem>
    <InfoItem
      v-if="ticketDetails.details.ticket_mode.mode === 'timer'"
      :label="t('执行时间')">
      {{ ticketDetails.details.ticket_mode.trigger_time }}
    </InfoItem>
    <InfoItem
      :label="t('目标集群')"
      style="flex: 1 0 100%; overflow: hidden">
      <InfoTable
        :data="targetClusterData"
        row-key="id">
        <InfoTableColumn
          col-key="id"
          fixed="left"
          :get-copy-value="(item: TargerCluster) => ticketDetails.details.clusters[item.id].immute_domain"
          :title="t('集群')"
          :width="250">
          <template #default="{ row }: { row: TargerCluster }">
            <TextOverflowLayout>
              {{ ticketDetails.details.clusters[row.id].immute_domain }}
            </TextOverflowLayout>
          </template>
        </InfoTableColumn>
        <InfoTableColumn
          col-key="cluster_type_name"
          :title="t('集群类型')">
          <template #default="{ row }: { row: TargerCluster }">
            {{ ticketDetails.details.clusters[row.id].cluster_type_name }}
          </template>
        </InfoTableColumn>
        <InfoTableColumn
          col-key="major_version"
          :title="t('版本')">
          <template #default="{ row }: { row: TargerCluster }">
            {{ ticketDetails.details.clusters[row.id].major_version }}
          </template>
        </InfoTableColumn>
        <InfoTableColumn
          col-key="status"
          :title="t('状态')">
          <template #default="{ row }: { row: TargerCluster }">
            <RenderClusterStatus :data="ticketDetails.details.clusters[row.id].status" />
          </template>
        </InfoTableColumn>
      </InfoTable>
    </InfoItem>
    <InfoItem
      :label="t('变更内容')"
      style="flex: 1 0 100%; margin-top: 10px; overflow: hidden">
      <PrimaryTable
        :data="ticketDetails.details.execute_objects"
        row-key="import_mode">
        <InfoTableColumn
          col-key="dbnames"
          fixed="left"
          :min-width="100"
          :title="t('变更的 DB')">
          <template #default="{ row }: { row: TargetDbRow }">
            <TagBlock :data="row.dbnames" />
          </template>
        </InfoTableColumn>
        <InfoTableColumn
          col-key="ignore_dbnames"
          :title="t('忽略的 DB')">
          <template #default="{ row }: { row: TargetDbRow }">
            <TagBlock :data="row.ignore_dbnames" />
          </template>
        </InfoTableColumn>
        <InfoTableColumn
          col-key="sql_files"
          :title="t('执行的 SQL')">
          <template #default="{ row }: { row: TargetDbRow }">
            <BkButton
              v-if="row.sql_files"
              text
              theme="primary"
              @click="handleSelectFile(row.sql_files[0], row)">
              <template v-if="row.sql_files.length < 2">
                <DbIcon
                  style="margin-right: 4px; color: #3a84ff"
                  type="file" />
                {{ getSQLFilename(row.sql_files[0]) }}
              </template>
              <template v-else>
                {{ t('n 个 SQL 文件', { n: row.sql_files.length }) }}
              </template>
            </BkButton>
          </template>
        </InfoTableColumn>
      </PrimaryTable>
    </InfoItem>
    <InfoItem
      v-if="ticketDetails.details.backup?.length > 0"
      :label="t('备份设置')"
      style="flex: 1 0 100%; margin-top: 10px; overflow: hidden">
      <PrimaryTable
        :data="ticketDetails.details.backup"
        row-key="db_patterns">
        <InfoTableColumn
          col-key="db_patterns"
          fixed="left"
          :title="t('备份 DB')">
          <template #default="{ row }: { row: BackupDbRow }">
            <TagBlock :data="row.db_patterns" />
          </template>
        </InfoTableColumn>
        <InfoTableColumn
          col-key="backup_on"
          :title="t('备份源')"
          :width="150" />
        <InfoTableColumn
          col-key="table_patterns"
          :title="t('备份表名')">
          <template #default="{ row }: { row: BackupDbRow }">
            <TagBlock :data="row.table_patterns" />
          </template>
        </InfoTableColumn>
      </PrimaryTable>
    </InfoItem>
  </InfoList>
  <RenderSqlfile
    v-if="currentExecuteObject"
    v-model:is-show="isShowSqlfile"
    :execute-object="currentExecuteObject"
    :path="ticketDetails.details.path"
    :select-file-name="selectFileName"
    :version-list="versionList"
    :whole-file-list="uploadFileList" />
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import RenderClusterStatus from '@components/cluster-status/Index.vue';
  import TagBlock from '@components/tag-block/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { getSQLFilename } from '@utils';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';
  import InfoTable, { InfoTableColumn } from '../../components/info-table/Index.vue';

  import RenderSqlfile from './components/render-sqlfile/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.ImportSqlFile>;
  }

  type TargerCluster = Record<'id', number>;
  type TargetDbRow = Props['ticketDetails']['details']['execute_objects'][number];
  type BackupDbRow = Props['ticketDetails']['details']['backup'][number];

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { cluster_ids: clusterIds, clusters } = props.ticketDetails.details;
  const versionList = _.uniq(clusterIds.map((clusterId) => clusters[clusterId].major_version));

  const selectFileName = ref('');
  const currentExecuteObject = ref<TargetDbRow>();
  const isShowSqlfile = ref(false);

  const uploadFileList = computed(() =>
    _.flatten(props.ticketDetails.details.execute_objects.map((item) => item.sql_files)),
  );

  const targetClusterData = computed(() =>
    props.ticketDetails.details.cluster_ids.map((item) => ({
      id: item,
    })),
  );

  // 执行模式
  const ticketModeData = computed(() => {
    const ticketModeTypeMap = {
      manual: {
        icon: 'manual',
        text: t('手动执行'),
        tips: t('单据审批之后_需要人工确认方可执行'),
      },
      timer: {
        icon: 'timed-task',
        text: t('定时执行'),
        tips: t('单据审批通过之后_定时执行_无需确认'),
      },
    };

    return ticketModeTypeMap[props.ticketDetails.details.ticket_mode.mode as keyof typeof ticketModeTypeMap];
  });

  const handleSelectFile = (filename: string, executeObject: TargetDbRow) => {
    selectFileName.value = filename;
    currentExecuteObject.value = executeObject;
    isShowSqlfile.value = true;
  };
</script>

<style lang="less" scoped>
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

  :deep(.bk-sideslider-content) {
    padding: 15px;
  }

  .tip-number {
    display: inline-block;
    font-weight: 700;
  }

  .domain-header {
    &:hover {
      [class*='db-icon'] {
        display: inline !important;
      }
    }

    [class*='db-icon'] {
      display: none;
      margin-top: 1px;
      margin-left: 4px;
      color: @primary-color;
      cursor: pointer;
    }
  }
</style>
