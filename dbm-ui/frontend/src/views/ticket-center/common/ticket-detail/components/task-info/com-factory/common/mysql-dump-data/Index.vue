<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <InfoList class="dump-data-demand">
    <InfoItem :label="t('导出模式')">
      {{ details.export_mode === 'sql' ? t('按 SQL 导出') : t('按库表导出') }}
    </InfoItem>
    <InfoItem :label="t('源集群')">
      {{ details.clusters?.[details.cluster_id]?.immute_domain || '--' }}
    </InfoItem>
    <template v-if="details.export_mode === 'sql'">
      <InfoItem :label="t('查询 SQL')">
        <BkButton v-if="details.sql_filename" text theme="primary" @click="handleOpenSql">
          {{ details.sql_filename }}
        </BkButton>
        <template v-else>--</template>
      </InfoItem>
    </template>
    <template v-else>
      <InfoItem :label="t('导出范围')">
        {{ details.where ? t('条件导出') : t('整表导出') }}
      </InfoItem>
      <InfoItem :label="t('导出物')">
        <template v-if="details.dump_data && details.dump_schema">
          {{ t('数据和表结构') }}
        </template>
        <template v-else-if="details.dump_data && !details.dump_schema">
          {{ t('仅数据') }}
        </template>
        <template v-else>{{ t('仅表结构') }}</template>
      </InfoItem>
      <InfoItem :label="t('目标DB名')">
        <TagBlock :data="details.databases" />
      </InfoItem>
      <InfoItem :label="t('目标表名')">
        <TagBlock :data="details.tables" />
      </InfoItem>
      <InfoItem
        v-if="details.tables.length === 1 && details.tables[0] === '*'"
        :label="t('忽略表名')">
        <TagBlock :data="details.tables_ignore" />
      </InfoItem>
      <InfoItem v-if="details.where" :label="t('where 条件')">
        {{ details.where }}
      </InfoItem>
    </template>
    <InfoItem :label="t('备注')">
      {{ ticketDetails.remark || '--' }}
    </InfoItem>
  </InfoList>
  <BkSideslider
    v-model:is-show="isSqlShow"
    :title="t('SQL 内容')"
    :width="960">
    <div class="dump-data-sql-slider">
      <BkLoading class="dump-data-sql-loading" :loading="isContentLoading">
        <Editor
          v-if="contentLoaded && isSqlShow"
          :message-list="[]"
          :model-value="sqlContent"
          readonly
          :show-result-panel="false"
          :title="sqlFilename" />
        <div v-else-if="loadFailed" class="dump-data-sql-error">
          <span>{{ t('SQL 文件内容读取失败，请重新上传') }}</span>
          <BkButton text theme="primary" @click="fetchSqlContent">{{ t('重试') }}</BkButton>
        </div>
      </BkLoading>
    </div>
  </BkSideslider>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';
  import { getFileContent } from '@services/source/storage';

  import TagBlock from '@components/tag-block/Index.vue';

  import Editor from '@views/db-manage/common/sql-execute/mysql-execute-objects/components/components/render-sql/components/editor/Index.vue';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.DumpData>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const details = computed(() => props.ticketDetails.details);
  const sqlFilename = computed(() => details.value.export_mode === 'sql' ? details.value.sql_filename : '');
  const sqlFilePath = computed(() => details.value.export_mode === 'sql'
    ? `${details.value.sql_path}/${details.value.sql_filename}`
    : '');
  const isSqlShow = ref(false);
  const sqlContent = ref('');
  const contentLoaded = ref(false);
  const isContentLoading = ref(false);
  const loadFailed = ref(false);
  let readVersion = 0;

  const fetchSqlContent = async () => {
    if (!sqlFilePath.value || isContentLoading.value) return;
    const version = ++readVersion;
    loadFailed.value = false;
    isContentLoading.value = true;
    try {
      const { content } = await getFileContent({ file_path: sqlFilePath.value });
      if (version === readVersion) {
        sqlContent.value = content;
        contentLoaded.value = true;
      }
    } catch {
      if (version === readVersion) loadFailed.value = true;
    } finally {
      if (version === readVersion) isContentLoading.value = false;
    }
  };

  const handleOpenSql = () => {
    isSqlShow.value = true;
    if (!contentLoaded.value) fetchSqlContent();
  };

  watch(() => props.ticketDetails.id + ':' + sqlFilePath.value, () => {
    readVersion += 1;
    isSqlShow.value = false;
    sqlContent.value = '';
    contentLoaded.value = false;
    loadFailed.value = false;
    isContentLoading.value = false;
  });
  onBeforeUnmount(() => { readVersion += 1; });
</script>

<style lang="less" scoped>
  .dump-data-demand {
    font-size: 14px;
    row-gap: 12px;

    :deep(.db-ticket-info-item) {
      min-height: 20px;
      line-height: 20px;
      flex: 0 0 50%;
    }

    :deep(.db-ticket-info-item-label) {
      padding-right: 12px;
      line-height: 20px;
      color: #979ba5;
      box-sizing: border-box;
      flex: 0 0 132px;
    }

    :deep(.db-ticket-info-item-value) {
      min-width: 0;
      white-space: normal;
      word-break: break-all;
    }
  }

  .dump-data-sql-slider {
    height: calc(100vh - 52px);
    padding: 12px;
    background: #1e1e1e;
    box-sizing: border-box;

    .dump-data-sql-loading {
      height: 100%;
    }

    :deep(.sql-execute-editor) {
      height: 100%;
      border: 1px solid #3e3e42;
      border-radius: 3px;
    }

    :deep(.editor-layout-header) {
      padding: 10px 16px;
      font-size: 13px;
      color: #ccc;
      background: #252526;
      border-bottom: 1px solid #2d2d2d;
    }

    .dump-data-sql-error {
      display: flex;
      padding: 16px;
      color: #ccc;
      gap: 12px;
    }
  }
</style>
