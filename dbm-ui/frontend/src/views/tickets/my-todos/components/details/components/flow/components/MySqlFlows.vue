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
    <template #content="{content}">
      <template v-if="content?.todos?.length > 0">
        <div
          v-for="item in content.todos"
          :key="item.id"
          class="flow-todo">
          <div class="flow-todo__title">
            {{ item.name }}
          </div>
          <div
            v-if="item.status === 'TODO'"
            class="operations">
            <BkPopover
              v-model:is-show="state.confirmTips"
              theme="light"
              trigger="manual"
              :width="320">
              <BkButton
                class="w-88 mr-8"
                :loading="state.isLoading"
                theme="primary"
                @click="handleConfirmToggle(true)">
                {{ getConfirmText(item) }}
              </BkButton>
              <template #content>
                <div class="todos-todos-tips-content">
                  <div class="todos-tips-content__desc">
                    {{ getConfirmTips(item) }}
                  </div>
                  <div class="todos-tips-content__buttons">
                    <BkButton
                      :loading="state.isLoading"
                      size="small"
                      theme="primary"
                      @click="handleConfirm('APPROVE', item)">
                      {{ getConfirmText(item) }}
                    </BkButton>
                    <BkButton
                      :disabled="state.isLoading"
                      size="small"
                      @click="handleConfirmToggle(false)">
                      {{ $t('取消') }}
                    </BkButton>
                  </div>
                </div>
              </template>
            </BkPopover>
            <BkPopover
              v-model:is-show="state.cancelTips"
              theme="light"
              trigger="manual"
              :width="320">
              <BkButton
                class="w-88 mr-8"
                :loading="state.isLoading"
                theme="danger"
                @click="handleCancelToggle(true)">
                {{ $t('终止单据') }}
              </BkButton>
              <template #content>
                <div class="todos-tips-content">
                  <div class="todos-tips-content__desc">
                    {{ $t('是否确认终止单据') }}
                  </div>
                  <div class="todos-tips-content__buttons">
                    <BkButton
                      :loading="state.isLoading"
                      size="small"
                      theme="danger"
                      @click="handleConfirm('TERMINATE', item)">
                      {{ $t('终止单据') }}
                    </BkButton>
                    <BkButton
                      :disabled="state.isLoading"
                      size="small"
                      @click="handleCancelToggle(false)">
                      {{ $t('取消') }}
                    </BkButton>
                  </div>
                </div>
              </template>
            </BkPopover>
          </div>
          <div
            v-else
            class="flow-todo__infos">
            {{ item.done_by }} 处理完成，
            操作：<span :class="String(item.status).toLowerCase()">{{ getOperation(item) }}</span>，
            耗时：{{ getCostTimeDisplay(item.cost_time) }}
            <template v-if="item.url">
              ，<a :href="item.url">{{ $t('查看详情') }} &gt;</a>
            </template>
            <p
              v-if="item.done_at"
              class="flow-time">
              {{ utcDisplayTime(item.done_at) }}
            </p>
          </div>
        </div>
      </template>
      <template v-if="content.flow_type === 'DELIVERY'">
        <div class="sql-risk-main">
          <I18nT
            keypath="共n个文件，含有m个高危语句"
            tag="div">
            <span style="font-weight: 700;color: #63656E">
              {{ ticketData.details.execute_sql_files.length }}
            </span>
            <span style="font-weight: 700;color: #EA3636">
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
                style="color:#3A84FF"
                type="file" />
              <span>
                <span style="color:#3A84FF">{{ fileName }}</span>，
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
              <span style="color:#3A84FF">
                {{ isShowCollapse ? t('收起') : t('更多') }}
              </span>
              <DbIcon
                class="collapse-dropdown-icon"
                :class="{'collapse-dropdown-icon-active': isShowCollapse}"
                style="color:#3A84FF"
                type="down-big" />
            </BkButton>
          </div>
        </div>
      </template>
      <template v-if="content.flow_type === 'DESCRIBE_TASK'">
        <p>
          <span
            v-if="content.status === 'SUCCEEDED'"
            style="color:#2DCB56">{{ t('执行成功') }}</span>
          <span
            v-else
            style="color:#EA3636">{{ t('执行失败') }}</span>
          , {{ t('共执行') }}
          <span class="sql-count">{{ sqlFileTotal }}</span>
          {{ t('个SQL文件_成功') }}
          <span class="sql-count success">{{ counts.success }}</span>
          {{ t('个_待执行') }}
          <span class="sql-count warning">{{ notExecutedCount }}</span>
          {{ t('个_失败') }}
          <span class="sql-count danger">{{ counts.fail }}</span>
          {{ t('个') }}
          <template v-if="content.summary">
            ，{{ t('耗时') }}：{{ getCostTimeDisplay(content.cost_time) }}，
          </template>
          <BkButton
            text
            theme="primary"
            @click="handleClickDetails">
            {{ t('查看详情') }}
          </BkButton>
        </p>
      </template>
      <template v-if="content.status !== 'RUNNING' && content.flow_type !== 'PAUSE'">
        <p v-if="content.flow_type !== 'DESCRIBE_TASK'">
          {{ content.summary }}
          <template v-if="content.summary">
            ，耗时：
            <CostTimer
              :is-timing="content.status === 'RUNNING'"
              :start-time="utcTimeToSeconds(content.start_time)"
              :value="content.cost_time" />
          </template>
          <template v-if="content.url">
            ，<a
              :href="content.url"
              target="_blank">{{ $t('任务详情') }} &gt;</a>
          </template>
        </p>
        <p
          v-if="content.end_time"
          class="flow-time">
          {{ utcDisplayTime(content.end_time) }}
        </p>
      </template>
    </template>
  </BkTimeline>
  <BkSideslider
    :is-show="isShow"
    render-directive="if"
    :title="$t('模拟执行_日志详情')"
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
    @closed="() => isShowSqlFile = false">
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
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';
  import { batchFetchFile } from '@services/source/storage';
  import { processTicketTodo } from '@services/source/ticket';
  import type {
    FlowItem,
    FlowItemTodo,
    MySQLImportSQLFileDetails,
  } from '@services/types/ticket';

  import { useMenu } from '@stores';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import RenderFileContent from '@views/tickets/common/components/demand-factory/mysql/import-sql-file/components/RenderFileContent.vue';
  import RenderFileList from '@views/tickets/common/components/demand-factory/mysql/import-sql-file/components/SqlFileList.vue';
  import SqlFileComponent from '@views/tickets/common/components/demand-factory/mysql/LogDetails.vue';
  import FlowIcon from '@views/tickets/common/components/flow-content/components/FlowIcon.vue';
  import useLogCounts from '@views/tickets/common/hooks/logCounts';

  import { getCostTimeDisplay, utcDisplayTime, utcTimeToSeconds } from '@utils';

  interface Props {
    ticketData: TicketModel<MySQLImportSQLFileDetails>,
    flows?: FlowItem[]
  }

  interface Emits {
    (e: 'processed'): void
  }

  const props = withDefaults(defineProps<Props>(), {
    flows: () => [],
  });
  const emits = defineEmits<Emits>();
  const { t } = useI18n();

  const { counts, fetchVersion } = useLogCounts();
  const menuStore = useMenu();
  const isShow = ref(false);
  const isShowCollapse = ref(false);
  const isShowSqlFile = ref(false);
  const selectFileName = ref('');

  const fileContentMap = shallowRef<Record<string, string>>({});
  const uploadFileList = shallowRef<Array<string>>([]);

  const isShowMore = computed(() => props.ticketData.details.execute_sql_files.length > 6);

  const sqlFileNames = computed(() => {
    if (isShowMore.value && !isShowCollapse.value) {
      return props.ticketData.details.execute_sql_files.slice(0, 6);
    }
    return props.ticketData.details.execute_sql_files;
  });

  const currentFileContent = computed(() => fileContentMap.value[selectFileName.value] || '');
  const notExecutedCount = computed(() => {
    const count = sqlFileTotal.value - counts.success - counts.fail;
    return count >= 0 ? count : 0;
  });

  const totalWarnCount = computed(() => Object.values(props.ticketData.details.grammar_check_info)
    .reduce((results, item) => {
      const warnCount = item.highrisk_warnings?.length ?? 0;
      return results + warnCount;
    }, 0));

  const state = reactive({
    confirmTips: false,
    cancelTips: false,
    isLoading: false,
  });

  const flowTimeline = computed(() => props.flows.map((flow: FlowItem) => ({
    tag: flow.flow_type_display,
    type: 'default',
    filled: true,
    content: flow,
    // color,
    icon: () => <FlowIcon data={flow} />,
  })));

  const sqlFileTotal = computed(() => props.ticketData.details.execute_sql_files?.length || 0);
  const rootId = computed(() => props.ticketData.details.root_id);
  const nodeId = computed(() => props.ticketData.details.semantic_node_id);

  watch([rootId, nodeId], ([rootId, nodeId]) => {
    if (rootId && nodeId) {
      fetchVersion(rootId, nodeId);
    }
  }, { immediate: true });

  const getConfirmText = (item: FlowItemTodo) => (item.type === 'RESOURCE_REPLENISH' ? t('重试') : t('确认执行'));
  const getConfirmTips = (item: FlowItemTodo) => (item.type === 'RESOURCE_REPLENISH' ? t('是否确认重试') : t('是否确认继续执行单据'));

  const handleToggleShowMore = () => {
    isShowCollapse.value = !isShowCollapse.value;
  };

  const handleFileSortChange = (list: string[]) => {
    uploadFileList.value = list;
  };

  // 查看日志详情
  const handleClickFile = (value: string) => {
    isShowSqlFile.value = true;
    selectFileName.value = value;
  };

  const handleClickDetails = () => {
    isShow.value = true;
  };

  const handleClose = () => {
    isShow.value = false;
  };

  const getOperation = (item: FlowItemTodo) => {
    const text = {
      DONE_SUCCESS: getConfirmText(item),
      DONE_FAILED: t('终止单据'),
      RUNNING: '--',
      TODO: '--',
    };
    return text[item.status];
  };

  const handleConfirmToggle = (show: boolean) => {
    state.confirmTips = show;
    state.cancelTips = false;
  };

  const handleCancelToggle = (show: boolean) => {
    state.cancelTips = show;
    state.confirmTips = false;
  };

  const handleConfirm = (action: 'APPROVE' | 'TERMINATE', item: FlowItemTodo) => {
    state.confirmTips = false;
    state.cancelTips = false;
    state.isLoading = true;
    processTicketTodo({
      action,
      todo_id: item.id,
      ticket_id: item.ticket,
      params: {},
    })
      .then(() => {
        emits('processed');
        menuStore.fetchTodosCount();
      })
      .finally(() => {
        state.isLoading = false;
      });
  };

  onMounted(() => {
    const uploadSQLFileList = props.ticketData.details.execute_objects.map(item => item.sql_file);
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
      // [selectFileName.value] = uploadSQLFileList;
    });
  });
</script>

<style lang="less" scoped>
:deep(.bk-modal-content) {
  height: 100%;
  padding: 15px;
}

.sql-risk-main{
  margin-top: 12px;
  gap: 8px;
  display: flex;
  flex-direction: column;

  .danger-count {
    color: #EA3636;
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
