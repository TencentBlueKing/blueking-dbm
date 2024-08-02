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
  <BkTimeline :list="flowTimeline">
    <template #content="{ content }">
      <template v-if="content.flow_type === 'DELIVERY'">
        <div class="sql-risk-main">
          <I18nT
            keypath="共n个文件，含有m个高危语句"
            tag="div">
            <span style="font-weight: 700; color: #63656e">
              {{ executeSqlFileList.length }}
            </span>
            <span style="font-weight: 700; color: #ea3636">
              {{ totalWarnCount }}
            </span>
          </I18nT>
          <div
            v-for="fileName in sqlFileNames"
            :key="fileName">
            <BkButton
              text
              @click="() => handleClickFile(fileName)">
              <DbIcon
                style="color: #3a84ff"
                type="file" />
              <span>
                <span style="color: #3a84ff">
                  {{ fileName?.replace(/[^_]+_/, '') }}
                </span>
                ，
                <span v-if="ticketData.details.grammar_check_info[fileName].highrisk_warnings?.length > 0">
                  <I18nT
                    keypath="含有n个高危语句"
                    tag="span">
                    <span class="danger-count">
                      {{ ticketData.details.grammar_check_info[fileName].highrisk_warnings.length }}
                    </span>
                  </I18nT>
                </span>
                <span v-else>{{ t('无高危语句') }}</span>
              </span>
            </BkButton>
          </div>
          <div v-if="isShowMore">
            <BkButton
              text
              @click="handleToggleShowMore">
              <span style="color: #3a84ff">
                {{ isShowCollapse ? t('收起') : t('更多') }}
              </span>
              <DbIcon
                class="collapse-dropdown-icon"
                :class="{ 'collapse-dropdown-icon-active': isShowCollapse }"
                style="color: #3a84ff"
                type="down-big" />
            </BkButton>
          </div>
        </div>
      </template>
      <template v-if="content.flow_type === 'DESCRIBE_TASK'">
        <p>
          <span
            v-if="counts.fail === 0"
            style="color: #2dcb56">
            {{ t('执行成功') }}
          </span>
          <span
            v-else
            style="color: #ea3636">
            {{ t('执行失败') }}
          </span>
          , {{ t('共执行') }}
          <span class="sql-count">{{ sqlFileTotal }}</span>
          {{ t('个SQL文件_成功') }}
          <span class="sql-count success">{{ counts.success }}</span>
          {{ t('个_待执行') }}
          <span class="sql-count warning">{{ notExecutedCount }}</span>
          {{ t('个_失败') }}
          <span class="sql-count danger">{{ counts.fail }}</span>
          {{ t('个') }}
          <template v-if="content.summary"> ，{{ t('耗时') }}：{{ getCostTimeDisplay(content.cost_time) }}， </template>
          <BkButton
            text
            theme="primary"
            @click="handleClickDetails">
            {{ t('查看详情') }}
          </BkButton>
        </p>
      </template>

      <FlowContent
        v-else
        :content="content"
        :flows="flows"
        :ticket-data="ticketData"
        @fetch-data="handleFetchData" />
    </template>
  </BkTimeline>
  <BkSideslider
    :is-show="isShow"
    render-directive="if"
    :title="t('模拟执行_日志详情')"
    :width="960"
    @closed="handleClose">
    <SqlFileComponent
      :node-id="nodeId"
      :root-id="rootId" />
  </BkSideslider>
  <BkSideslider
    class="sql-log-sideslider"
    :is-show="isShowSqlFile"
    render-directive="if"
    :title="t('执行SQL变更_内容详情')"
    :width="960"
    :z-index="99999"
    @closed="() => (isShowSqlFile = false)">
    <div
      v-if="uploadFileList.length > 1"
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
</template>

<script setup lang="tsx">
  import _ from 'lodash'
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type { MySQLImportSQLFileDetails } from '@services/model/ticket/details/mysql';
  import TicketModel from '@services/model/ticket/ticket';
  import { semanticCheckResultLogs } from '@services/source/sqlImport';
  import { batchFetchFile } from '@services/source/storage';
  import type { FlowItem } from '@services/types/ticket';

  import RenderFileContent from '@views/tickets/common/components/demand-factory/mysql/import-sql-file/components/RenderFileContent.vue';
  import RenderFileList from '@views/tickets/common/components/demand-factory/mysql/import-sql-file/components/SqlFileList.vue';
  import SqlFileComponent from '@views/tickets/common/components/demand-factory/mysql/LogDetails.vue';
  import FlowIcon from '@views/tickets/common/components/flow-content/components/FlowIcon.vue';
  import FlowContent from '@views/tickets/common/components/flow-content/Index.vue';

  import { getCostTimeDisplay } from '@utils';

  interface Props {
    ticketData: TicketModel<MySQLImportSQLFileDetails>,
    flows?: FlowItem[]
  }

  interface Emits {
    (e: 'fetch-data'): void
  }

  const props = withDefaults(defineProps<Props>(), {
    flows: () => [],
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isShow = ref(false);
  const isShowCollapse = ref(false);
  const isShowSqlFile = ref(false);
  const selectFileName = ref('');

  const fileContentMap = shallowRef<Record<string, string>>({});
  const uploadFileList = shallowRef<Array<string>>([]);

  const counts = reactive({
    success: 0,
    fail: 0,
  });

  const executeSqlFileList = computed(() => _.flatten(props.ticketData.details.execute_objects.map(item => item.sql_files)))

  const isShowMore = computed(() => executeSqlFileList.value.length > 6);

  const sqlFileNames = computed(() => {
    if (isShowMore.value && !isShowCollapse.value) {
      return executeSqlFileList.value.slice(0, 6);
    }
    return executeSqlFileList.value;
  });

  const totalWarnCount = computed(() => Object.values(props.ticketData.details.grammar_check_info)
    .reduce((results, item) => {
      const warnCount = item.highrisk_warnings?.length ?? 0;
      return results + warnCount;
    }, 0));

  const currentFileContent = computed(() => fileContentMap.value[selectFileName.value] || '');

  const notExecutedCount = computed(() => {
    const count = sqlFileTotal.value - counts.success - counts.fail;
    return count >= 0 ? count : 0;
  });

  const flowTimeline = computed(() => props.flows.map((flow: FlowItem) => ({
    tag: flow.flow_type_display,
    type: 'default',
    filled: true,
    content: flow,
    // color,
    icon: () => <FlowIcon data={flow} />,
  })));

  const sqlFileTotal = computed(() => executeSqlFileList.value?.length || 0);
  const rootId = computed(() => props.ticketData.details.root_id);
  const nodeId = computed(() => props.ticketData.details.semantic_node_id);

  const { run: fetchSemanticCheckResultLogs } = useRequest(semanticCheckResultLogs, {
    manual: true,
    onSuccess(logData) {
      logData.forEach((item) => {
        if (item.status === 'SUCCEEDED') {
          counts.success += 1;
        }
        if (item.status === 'FAILED') {
          counts.fail += 1;
        }
      });
    },
  });

  watch([rootId, nodeId], ([rootId, nodeId]) => {
    if (rootId && nodeId) {
      fetchSemanticCheckResultLogs({
        cluster_type: 'mysql',
        root_id: rootId,
        node_id: nodeId,
      });
    }
  }, { immediate: true });

  const handleToggleShowMore = () => {
    isShowCollapse.value = !isShowCollapse.value;
  };

  // 查看日志详情
  const handleClickFile = (value: string) => {
    isShowSqlFile.value = true;
    selectFileName.value = value;
  };


  const handleFileSortChange = (list: string[]) => {
    uploadFileList.value = list;
  };

  const handleFetchData = () => {
    emits('fetch-data');
  };

  const handleClickDetails = () => {
    isShow.value = true;
  };

  const handleClose = () => {
    isShow.value = false;
  };

  onMounted(() => {
    const uploadSQLFileList = executeSqlFileList.value;
    uploadFileList.value = uploadSQLFileList;

    const filePathList = uploadSQLFileList.reduce((result, item) => {
      result.push(`${props.ticketData.details.path}/${item}`);
      return result;
    }, [] as string[]);

    batchFetchFile({
      file_path_list: filePathList,
    }).then((result) => {
      fileContentMap.value = result.reduce((result, fileInfo) => {
        const fileName = fileInfo.path.split('/').pop() as string;
        return Object.assign(result, {
          [fileName]: fileInfo.content,
        });
      }, {} as Record<string, string>);
      [selectFileName.value] = uploadSQLFileList;
    });
  });
</script>

<style lang="less" scoped>
  :deep(.bk-modal-content) {
    height: 100%;
    padding: 15px;
  }

  .sql-risk-main {
    margin-bottom: 10px;
    gap: 8px;
    display: flex;
    flex-direction: column;

    .danger-count {
      color: #ea3636;
      font-weight: 700;
      display: inline-block;
    }

    .collapse-dropdown-icon {
      transform: rotate(0);
      transition: all 0.5s;
    }

    .collapse-dropdown-icon-active {
      transform: rotate(-180deg);
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

  .sql-count {
    font-weight: 700;

    &.success {
      color: @success-color;
    }

    &.warning {
      color: @warning-color;
    }

    &.danger {
      color: @danger-color;
    }
  }
</style>
