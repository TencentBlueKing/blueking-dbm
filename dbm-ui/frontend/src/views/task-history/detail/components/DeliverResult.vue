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
  <div class="deliver-results-main">
    <!-- ticketId 未就绪或请求进行中都算加载中，避免页签下先出现一片空白 -->
    <BkLoading
      class="deliver-results-loading"
      :loading="isLoading"
      :z-index="2">
      <template v-if="abstractList.length">
        <div class="tip-display">
          {{ t('根据任务执行情况，输出以下任务执行结果摘要：') }}
        </div>
        <div class="table-list">
          <BkCollapse
            v-for="(item, index) in abstractList"
            :key="index"
            v-model="activeIndex"
            class="table-collapse-main">
            <BkCollapsePanel :name="String(index)">
              <template #header>
                <div class="collapse-panel-header">
                  <span class="panel-title">
                    {{ item.table_name }}
                  </span>
                  <DbIcon
                    :class="{ 'active-icon': !activeIndex.includes(String(index)) }"
                    type="down-big" />
                </div>
              </template>
              <template #content>
                <PrimaryTable
                  :columns="item.titles"
                  :data="item.values" />
              </template>
            </BkCollapsePanel>
          </BkCollapse>
        </div>
      </template>
      <!-- 请求异常时保留页签并给出重试入口，不能再像以前一样留下无法恢复的空白 -->
      <EmptyStatus
        v-else-if="!isLoading"
        :is-anomalies="!!error"
        :is-searching="false"
        @refresh="fetchTicketFlows" />
    </BkLoading>
  </div>
</template>
<script setup lang="ts">
  import { h } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getTicketFlows } from '@services/source/ticketFlow';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import { isHttpUrl } from '@utils';

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  export type AbstractItem = {
    titles: {
      colKey: string;
      title: string;
    }[];
  } & Omit<ServiceReturnType<typeof getTicketFlows>[number]['output_data'][number], 'titles'>;

  interface Props {
    rootId: string;
    ticketId: number;
  }

  type Emits = (e: 'requestFinish', value: AbstractItem[]) => void;

  const { t } = useI18n();

  const abstractList = ref<AbstractItem[]>([]);
  const activeIndex = ref<string[]>([]);

  // 请求失败或 onSuccess 抛错都会落到 error，此时不发空列表，页签保留并给出重试入口
  const {
    error,
    loading,
    run: requestTicketFlows,
  } = useRequest(getTicketFlows, {
    manual: true,
    onSuccess: (data) => {
      const currentFlow = data.find((item) => item.flow_obj_id === props.rootId);
      if (currentFlow && Array.isArray(currentFlow.output_data) && currentFlow.output_data.length) {
        abstractList.value = currentFlow.output_data
          // titles 缺失的条目直接跳过，不能让单条脏数据把整个页签打空
          .filter((item) => !item.hidden && Array.isArray(item.titles))
          .map((item) => ({
            ...item,
            titles: item.titles.map((title) => ({
              cell:
                title.type === 'url'
                  ? (_h: unknown, { row }: { row: Record<string, unknown> }) => {
                      const value = row[title.id];
                      if (isHttpUrl(value)) {
                        return h(
                          'a',
                          {
                            href: value,
                            rel: 'noreferrer',
                            target: '_blank',
                          },
                          title.display_name,
                        );
                      }
                      return '--';
                    }
                  : undefined,
              colKey: title.id,
              title: title.display_name,
            })),
          }));
      }
      // 只有请求成功、拿到确定的空结果才通知父层移除页签
      emits('requestFinish', abstractList.value);
    },
  });

  // 请求还没发起时 loading 仍是 false，用 ticketId 兜住，避免未加载就渲染成空态
  const isLoading = computed(() => loading.value || !props.ticketId);

  const fetchTicketFlows = () => {
    if (!props.ticketId) {
      return;
    }
    requestTicketFlows({
      id: props.ticketId,
    });
  };

  watch(
    abstractList,
    (list) => {
      activeIndex.value = list.map((_, index) => String(index));
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.ticketId,
    () => {
      fetchTicketFlows();
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less">
  .deliver-results-main {
    padding: 0 24px;

    // 加载中没有内容撑高，需要给个高度，否则 loading 图标看不见
    .deliver-results-loading {
      min-height: 200px;
    }

    .tip-display {
      margin-bottom: 16px;
    }

    .table-collapse-main {
      .collapse-panel-header {
        position: relative;
        display: flex;
        height: 28px;
        padding: 0 12px 0 16px;
        color: #313238;
        cursor: pointer;
        background: #f0f1f5;
        align-items: center;
        justify-content: space-between;

        .panel-title {
          font-size: 12px;
          font-weight: 700;
        }

        .active-icon {
          transform: rotateZ(-90deg);
          transition: all 0.5s;
        }
      }

      .bk-collapse-content {
        padding: 0;
      }
    }
  }
</style>
