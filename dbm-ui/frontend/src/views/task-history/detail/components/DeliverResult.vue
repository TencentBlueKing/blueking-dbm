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
    v-if="abstractList.length"
    class="deliver-results-main">
    <div class="tip-display">
      {{ t('根据任务执行情况，输出以下任务执行结果摘要：') }}
    </div>
    <div class="table-list">
      <TableCollapse
        v-for="(item, index) in abstractList"
        :key="index"
        :title="item.table_name">
        <PrimaryTable
          :columns="item.titles"
          :data="item.values" />
      </TableCollapse>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { h } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getTicketFlows } from '@services/source/ticketFlow';

  import TableCollapse from '@components/table-collapse/Index.vue';

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

  const { run: fetchTicketFlows } = useRequest(getTicketFlows, {
    manual: true,
    onSuccess: (data) => {
      const currentFlow = data.find((item) => item.flow_obj_id === props.rootId);
      if (!currentFlow) {
        emits('requestFinish', []);
        return;
      }
      if (Array.isArray(currentFlow.output_data) && currentFlow.output_data.length) {
        abstractList.value = currentFlow.output_data
          .filter((item) => !item.hidden)
          .map((item) => ({
            ...item,
            titles: item.titles.map((item) => ({
              cell:
                item.type === 'url'
                  ? (_, { row }) => {
                      const value = row[item.id];
                      if (isHttpUrl(value)) {
                        return h(
                          'a',
                          {
                            href: value,
                            rel: 'noreferrer',
                            target: '_blank',
                          },
                          item.display_name,
                        );
                      }
                      return '--';
                    }
                  : '--',
              colKey: item.id,
              title: item.display_name,
            })),
          }));
      }
      emits('requestFinish', abstractList.value);
    },
  });

  watch(
    () => props.ticketId,
    () => {
      if (props.ticketId) {
        fetchTicketFlows({
          id: props.ticketId,
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less">
  .deliver-results-main {
    padding: 0 24px;

    .tip-display {
      margin-bottom: 16px;
    }
  }
</style>
