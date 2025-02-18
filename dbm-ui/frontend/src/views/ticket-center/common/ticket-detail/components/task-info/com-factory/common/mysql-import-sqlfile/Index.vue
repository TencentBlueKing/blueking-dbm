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
    <InfoItem :label="t('所属业务:')">
      {{ ticketDetails.bk_biz_name }}
    </InfoItem>
    <InfoItem :label="t('业务英文名:')">
      {{ ticketDetails.db_app_abbr }}
    </InfoItem>
    <InfoItem :label="t('字符集:')">
      {{ ticketDetails.details.charset }}
    </InfoItem>
    <InfoItem
      v-if="ticketModeData"
      :label="t('执行模式:')">
      <DbIcon :type="ticketModeData.icon" />
      <span v-bk-tooltips="ticketModeData.tips">{{ ticketModeData.text }}</span>
    </InfoItem>
    <InfoItem
      v-if="ticketDetails.details.ticket_mode.mode === 'timer'"
      :label="t('执行时间:')">
      {{ ticketDetails.details.ticket_mode.trigger_time }}
    </InfoItem>
    <InfoItem
      :label="t('目标集群:')"
      style="flex: 1 0 100%">
      <BkTable :data="targetClusterData">
        <BkTableColumn :label="t('集群')">
          <template #default="{ data }: { data: TargerCluster }">
            {{ ticketDetails.details.clusters[data.id].immute_domain }}
          </template>
        </BkTableColumn>
        <BkTableColumn :label="t('集群类型')">
          <template #default="{ data }: { data: TargerCluster }">
            {{ ticketDetails.details.clusters[data.id].cluster_type_name }}
          </template>
        </BkTableColumn>
        <BkTableColumn :label="t('版本')">
          <template #default="{ data }: { data: TargerCluster }">
            {{ ticketDetails.details.clusters[data.id].major_version }}
          </template>
        </BkTableColumn>
        <BkTableColumn :label="t('状态')">
          <template #default="{ data }: { data: TargerCluster }">
            <RenderClusterStatus :data="ticketDetails.details.clusters[data.id].status" />
          </template>
        </BkTableColumn>
      </BkTable>
    </InfoItem>
    <InfoItem
      :label="t('目标DB:')"
      style="flex: 1 0 100%; margin-top: 10px">
      <BkTable :data="ticketDetails.details.execute_objects">
        <BkTableColumn :label="t('变更的 DB')">
          <template #default="{ data }: { data: TargetDbRow }">
            <TagBlock :data="data.dbnames" />
          </template>
        </BkTableColumn>
        <BkTableColumn :label="t('忽略的 DB')">
          <template #default="{ data }: { data: TargetDbRow }">
            <TagBlock :data="data.ignore_dbnames" />
          </template>
        </BkTableColumn>
        <BkTableColumn :label="t('执行的 SQL')">
          <template #default="{ data }: { data: TargetDbRow }">
            <BkButton
              v-if="data.sql_files"
              text
              theme="primary"
              @click="handleSelectFile(data.sql_files[0], data)">
              <template v-if="data.sql_files.length < 2">
                <DbIcon
                  style="margin-right: 4px; color: #3a84ff"
                  type="file" />
                {{ getSQLFilename(data.sql_files[0]) }}
              </template>
              <template v-else>
                {{ t('n 个 SQL 文件', { n: data.sql_files.length }) }}
              </template>
            </BkButton>
          </template>
        </BkTableColumn>
      </BkTable>
    </InfoItem>
  </InfoList>
  <RenderSqlfile
    v-if="currentExecuteObject"
    v-model:is-show="isShowSqlfile"
    :execute-object="currentExecuteObject"
    :path="ticketDetails.details.path"
    :select-file-name="selectFileName"
    :whole-file-list="uploadFileList" />
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import RenderClusterStatus from '@components/cluster-status/Index.vue';
  import TagBlock from '@components/tag-block/Index.vue';

  import { getSQLFilename } from '@utils';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  import RenderSqlfile from './components/render-sqlfile/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.ImportSqlFile>;
  }

  type TargerCluster = Record<'id', number>;
  type TargetDbRow = Props['ticketDetails']['details']['execute_objects'][number];

  const props = defineProps<Props>();

  const { t } = useI18n();

  const selectFileName = ref('');
  const currentExecuteObject = ref<Props['ticketDetails']['details']['execute_objects'][number]>();
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
        text: t('手动执行'),
        icon: 'manual',
        tips: t('单据审批之后_需要人工确认方可执行'),
      },
      timer: {
        text: t('定时执行'),
        icon: 'timed-task',
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
</style>
