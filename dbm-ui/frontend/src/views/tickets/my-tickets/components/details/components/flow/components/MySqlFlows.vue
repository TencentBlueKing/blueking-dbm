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
            v-for="fileName in renderSqlFileList"
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
            :style="{
              color: content.status === 'SUCCEEDED' ? '#2dcb56' : 'inherit',
            }">
            {{ content.summary }}
          </span>
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
    class="sql-log-sideslider"
    :is-show="isShowSqlFile"
    :width="960"
    @closed="() => (isShowSqlFile = false)">
    <template
      v-if="currentFileExecuteObject"
      #header>
      <span>{{ t('SQL 内容') }}</span>
      <span style="margin-left: 30px; font-size: 12px; font-weight: normal; color: #63656e">
        <span>{{ t('变更的 DB:') }}</span>
        <span class="ml-4">
          <BkTag
            v-for="item in currentFileExecuteObject.dbnames"
            :key="item">
            {{ item }}
          </BkTag>
          <template v-if="currentFileExecuteObject.dbnames.length < 1">--</template>
        </span>
        <span class="ml-25">{{ t('忽略的 DB:') }}</span>
        <span class="ml-4">
          <BkTag
            v-for="item in currentFileExecuteObject.ignore_dbnames"
            :key="item">
            {{ item }}
          </BkTag>
          <template v-if="currentFileExecuteObject.ignore_dbnames.length < 1">--</template>
        </span>
      </span>
    </template>
    <div class="editor-layout">
      <div class="editor-layout-left">
        <RenderFileList
          v-model="selectFileName"
          :data="executeSqlFileList" />
      </div>
      <div class="editor-layout-right">
        <RenderFileContent
          :model-value="currentFileContent"
          readonly
          :title="selectFileName" />
      </div>
    </div>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import _ from 'lodash'
  import { useI18n } from 'vue-i18n';
  import { useRouter} from 'vue-router'

  import type { MySQLImportSQLFileDetails } from '@services/model/ticket/details/mysql';
  import TicketModel from '@services/model/ticket/ticket';
  import { batchFetchFile } from '@services/source/storage';
  import type { FlowItem } from '@services/types/ticket';

  import RenderFileContent from '@views/tickets/common/components/demand-factory/mysql/import-sql-file/components/RenderFileContent.vue';
  import RenderFileList from '@views/tickets/common/components/demand-factory/mysql/import-sql-file/components/SqlFileList.vue';
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

  const router = useRouter();
  const { t } = useI18n();

  const isShowCollapse = ref(false);
  const isShowSqlFile = ref(false);
  const selectFileName = ref('');

  const fileContentMap = shallowRef<Record<string, string>>({});
  const executeSqlFileList = computed(() => _.flatten(props.ticketData.details.execute_objects.map(item => item.sql_files)))

  const isShowMore = computed(() => executeSqlFileList.value.length > 6);

  const renderSqlFileList = computed(() => {
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

  const currentFileExecuteObject = computed(() => _.find(props.ticketData.details.execute_objects, item => item.sql_files.includes(selectFileName.value)));


  const flowTimeline = computed(() => props.flows.map((flow: FlowItem) => ({
    tag: flow.flow_type === 'PAUSE' ? `${t('确认是否执行')}“${flow.flow_type_display}”` : flow.flow_type_display,
    type: 'default',
    filled: true,
    content: flow,
    icon: () => <FlowIcon data={flow} />,
  })));

  const handleToggleShowMore = () => {
    isShowCollapse.value = !isShowCollapse.value;
  };

  // 查看日志详情
  const handleClickFile = (value: string) => {
    isShowSqlFile.value = true;
    selectFileName.value = value;
  };

  const handleFetchData = () => {
    emits('fetch-data');
  };

  const handleClickDetails = () => {
    const {href} = router.resolve({
      name: 'MySQLExecute',
      params: {
        step: 'result'
      },
      query: {
        rootId: props.ticketData.details.root_id,
      }
    })
    window.open(href)
  };

  onMounted(() => {
    const filePathList = executeSqlFileList.value.reduce((result, item) => {
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
      [selectFileName.value] = executeSqlFileList.value;
    });
  });
</script>

<style lang="less" scoped>
  :deep(.bk-modal-content) {
    height: 100%;
    padding: 15px;
  }

  .sql-risk-main {
    display: flex;
    margin-bottom: 10px;
    gap: 8px;
    flex-direction: column;

    .danger-count {
      display: inline-block;
      font-weight: 700;
      color: #ea3636;
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
