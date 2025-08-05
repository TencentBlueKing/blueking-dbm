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
  <BkPopover
    v-model:is-show="state.isShow"
    :arrow="false"
    :boundary="body"
    class="retry-selector"
    fix-on-boundary
    placement="bottom-start"
    theme="light"
    trigger="manual"
    :width="392">
    <div
      v-clickoutside:[contentRef]="handleClose"
      class="retry-selector-trigger"
      :class="[activeCls, { 'retry-selector-trigger--loading': state.loading }]"
      @click="handleToggle">
      <div class="retry-selector-display">
        {{ state.active.started_time }}
        <BkTag
          v-if="isLatest"
          theme="info"
          type="filled">
          {{ t('最新') }}
        </BkTag>
      </div>
      <DbIcon
        class="retry-selector-icon"
        type="down-big" />
      <BkLoading
        v-if="state.loading"
        class="retry-selector-loading"
        loading
        mode="spin"
        size="mini"
        theme="primary" />
    </div>
    <template #content>
      <div
        ref="contentRef"
        class="retry-selector-content">
        <strong>{{ t('执行记录') }}</strong>
        <DbOriginalTable
          :columns="columns"
          :data="state.histories"
          :head-height="34"
          :height="240"
          :is-anomalies="isAnomalies"
          :row-class="getRowClass"
          :row-height="34"
          @refresh="fetchData"
          @row-click="handleSelected" />
      </div>
    </template>
  </BkPopover>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { getRetryNodeHistories } from '@services/source/taskflow';

  import { getCostTimeDisplay } from '@utils';

  type RetryNodeItem = ServiceReturnType<typeof getRetryNodeHistories>[number];

  interface Props {
    nodeId: string;
    rootId: string;
  }

  type Emits = (e: 'change', value: RetryNodeItem) => void;

  const props = defineProps<Props>();
  const emit = defineEmits<Emits>();

  const { t } = useI18n();

  const isAnomalies = ref(false);
  const contentRef = ref<HTMLDivElement>();

  const state = reactive({
    active: {} as RetryNodeItem,
    histories: [] as RetryNodeItem[],
    isShow: false,
    latestVersion: '',
    loading: true,
  });

  const isLatest = computed(() => state.active.version === state.latestVersion);
  const activeCls = computed(() => (state.isShow ? 'retry-selector-trigger--active' : ''));

  const { body } = document;
  const columns = [
    {
      field: 'started_time',
      label: t('执行时间'),
      render: ({ data }: { data: RetryNodeItem }) => (
        <div class='started-time-column'>
          <span>{data.started_time}</span>
          {state.latestVersion === data.version ? (
            <bk-tag
              class='ml-8'
              theme='info'>
              {t('最新')}
            </bk-tag>
          ) : null}
        </div>
      ),
    },
    {
      field: 'cost_time',
      label: t('耗时'),
      render: ({ data }: { data: RetryNodeItem }) => (
        <div class='started-time-column'>
          <span>{getCostTimeDisplay(data.cost_time)}</span>
        </div>
      ),
      width: 120,
    },
  ];

  const handleToggle = () => {
    if (state.loading) {
      return;
    }

    state.isShow = !state.isShow;
  };

  const handleClose = () => {
    state.isShow = false;
  };

  /**
   * 获取节点重试列表
   */
  const fetchData = () => {
    state.loading = true;
    getRetryNodeHistories({
      node_id: props.nodeId,
      root_id: props.rootId,
    })
      .then((historyData) => {
        state.histories = historyData;
        if (historyData.length > 0) {
          state.latestVersion = historyData[0].version;
          [state.active] = historyData;
        }
        isAnomalies.value = false;
      })
      .finally(() => {
        state.loading = false;
      });
  };

  /**
   * 设置行选中样式
   */
  const getRowClass = (row: any) => (row.version === state.latestVersion ? 'active-row' : '');

  /**
   * 选中当前行
   */
  const handleSelected = (e: MouseEvent, row: any) => {
    if (state.active.version === row.version) return;

    state.active = row;
    state.isShow = false;
  };

  watch(
    () => state.active,
    () => {
      if (!_.isEmpty(state.active)) {
        emit('change', state.active);
      }
    },
    { deep: true },
  );

  watch(
    () => props.nodeId,
    () => {
      if (props.nodeId) {
        fetchData();
      }
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  .retry-selector {
    &-display {
      width: 100%;
      color: #c4c6cc;
    }

    &-icon {
      position: absolute;
      top: 6px;
      right: 6px;
      color: #c4c6cc;
      transition: all 0.2s;
    }

    &-trigger {
      position: relative;
      height: 26px;
      min-width: 170px;
      padding: 0 20px 0 8px;
      font-size: @font-size-mini;
      line-height: 24px;
      color: @default-color;
      cursor: pointer;
      background-color: #4d4d4d;
      border: 1px solid transparent;
      border-radius: 2px;

      &--active {
        border-color: @primary-color;

        .retry-selector-icon {
          transform: rotate(180deg);
        }
      }

      &--loading {
        cursor: not-allowed;
      }

      .bk-tag {
        height: 16px;
        padding: 0 4px;
        line-height: 16px;
        pointer-events: none;
      }
    }

    &-loading {
      position: absolute;
      top: 4px;
      right: 6px;
      background-color: @bg-gray;
    }

    &-content {
      padding: 9px 2px;

      strong {
        display: block;
        padding-bottom: 12px;
        color: @title-color;
      }
    }
  }
</style>
