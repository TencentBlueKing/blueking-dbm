<template>
  <div
    v-if="abstractList.length"
    class="deliver-results-main">
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
  </div>
</template>
<script setup lang="ts">
  import { h } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getTicketFlows } from '@services/source/ticketFlow';

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

        .db-icon-down-shape {
          color: #979ba5;
          transform: rotateZ(0deg);
          transition: all 0.5s;
        }

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
