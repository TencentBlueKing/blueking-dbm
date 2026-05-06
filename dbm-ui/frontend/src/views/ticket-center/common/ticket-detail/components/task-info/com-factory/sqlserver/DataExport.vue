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
    <InfoItem :label="t('集群类型')">
      {{
        ticketDetails.details.clusters?.[0]?.cluster_type === ClusterTypes.SQLSERVER_SINGLE ? t('单节点') : t('主从')
      }}
    </InfoItem>
    <InfoItem :label="t('集群')">
      <p
        v-for="cluster in ticketDetails.details.clusters"
        :key="cluster.id">
        {{ cluster.immute_domain }}
      </p>
    </InfoItem>
    <InfoItem
      v-if="ticketDetails.details?.select_role"
      :label="t('查询角色')">
      {{ ticketDetails.details.select_role === 'slave' ? 'Slave' : 'Master' }}
    </InfoItem>
    <InfoItem :label="t('查询 SQL')">
      <BkButton
        v-if="fileName"
        text
        theme="primary"
        @click="handleShowSqlContent">
        {{ fileName }}
      </BkButton>
      <span v-else>--</span>
      <BkSideslider
        v-model:is-show="isShowSqlfile"
        :title="t('查询 SQL')"
        :width="960">
        <BkLoading :loading="isContentLoading">
          <div class="editor-layout">
            <RenderFileContent
              v-if="fileInfo?.[0]?.content"
              :db-types="DBTypes.SQLSERVER"
              :model-value="fileInfo[0].content"
              readonly
              :title="fileInfo[0].path"
              :version-list="versionList" />
          </div>
        </BkLoading>
      </BkSideslider>
    </InfoItem>
    <InfoItem :label="t('目标DB')">
      <TicketInfoTable
        :data="ticketDetails.details.execute_objects"
        row-key="dbnames">
        <TicketInfoTableColumn
          col-key="dbnames"
          :title="t('查询 DB')">
          <template #default="{ row }: { row: RowData }">
            <TagBlock :data="row.dbnames" />
          </template>
        </TicketInfoTableColumn>
        <TicketInfoTableColumn
          col-key="ignore_dbnames"
          :title="t('忽略 DB')">
          <template #default="{ row }: { row: RowData }">
            <TagBlock :data="row.ignore_dbnames" />
          </template>
        </TicketInfoTableColumn>
      </TicketInfoTable>
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';
  import { batchFetchFile } from '@services/source/storage';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import RenderFileContent from '@views/ticket-center/common/ticket-detail/components/common/SqlFileContent.vue';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  type RowData = Sqlserver.DataExport['execute_objects'][number];

  interface Props {
    ticketDetails: TicketModel<Sqlserver.DataExport>;
  }

  defineOptions({
    name: TicketTypes.SQLSERVER_DATA_EXPORT,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();
  const versionList = ref<string[]>([]);
  const isShowSqlfile = ref(false);

  const fileName = computed(() => {
    return props.ticketDetails.details.execute_objects?.[0]?.sql_files?.[0];
  });

  const {
    data: fileInfo,
    loading: isContentLoading,
    run: runBatchFetchFile,
  } = useRequest(batchFetchFile, {
    manual: true,
  });

  const handleShowSqlContent = () => {
    isShowSqlfile.value = true;
    const filePath = props.ticketDetails.details.path;
    if (filePath && fileName.value) {
      versionList.value = Object.values(props.ticketDetails.details.clusters).map((item) => item.major_version);
      runBatchFetchFile({
        file_path_list: [`${filePath}/${fileName.value}`],
      });
    }
  };
</script>
<style lang="less" scoped>
  .editor-layout {
    margin: 16px 24px;
  }
</style>
