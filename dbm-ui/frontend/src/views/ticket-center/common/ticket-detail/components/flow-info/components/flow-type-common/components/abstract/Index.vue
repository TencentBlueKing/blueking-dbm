<template>
  <FlowCollapse
    v-if="abstractList.length"
    :title="t('交付结果')">
    <div class="flow-abstract-main">
      <BkCollapse
        v-for="(item, index) in abstractList"
        :key="index"
        v-model="activeIndex"
        class="table-collapse-main">
        <BkCollapsePanel :name="String(index)">
          <template #header>
            <div class="collapse-panel-header">
              <span class="panel-title">
                {{ item.table_display_name || item.table_name }}
              </span>
              <DbIcon
                :class="{ 'active-icon': !activeIndex.includes(String(index)) }"
                type="down-big" />
            </div>
          </template>
          <template #content>
            <TicketInfoTable
              :data="item.values"
              header-row-class-name="abstract-table-header-row"
              :row-key="item.titles[0].field">
              <TicketInfoTableColumn
                v-for="titleItem in item.titles"
                :key="titleItem.field"
                :col-key="titleItem.field"
                :get-copy-value="titleItem.field === 'ip' ? (row) => row.ip : undefined"
                :title="titleItem.label">
                <template #default="{ row }">
                  <a
                    v-if="titleItem.type === 'url' && isHttpUrl(row[titleItem.field])"
                    :href="row[titleItem.field]"
                    target="_blank">
                    {{ titleItem.label }}
                  </a>
                  <span v-else-if="titleItem.type === 'url'"> -- </span>
                  <span v-else>
                    {{ row[titleItem.field] || '--' }}
                  </span>
                </template>
              </TicketInfoTableColumn>
            </TicketInfoTable>
          </template>
        </BkCollapsePanel>
      </BkCollapse>
    </div>
  </FlowCollapse>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';

  import { isHttpUrl } from '@utils';

  import FlowCollapse from '../FlowCollapse.vue';

  interface Props {
    data: FlowMode<unknown, any>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const activeIndex = ref<string[]>([]);

  const abstractList = computed(() => {
    if (!props.data.output_data.length) {
      return [];
    }

    return props.data.output_data
      .filter((item) => !item.hidden)
      .map((item) => {
        return {
          ...item,
          titles: item.titles.map((item) => ({
            field: item.id,
            label: item.display_name,
            type: item.type,
          })),
        };
      });
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
</script>
<style lang="less">
  .flow-abstract-main {
    display: flex;
    width: 100%;
    padding-left: 16px;
    background: #f5f7fa;
    flex-direction: column;
    gap: 16px;

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

    .item-main {
      width: 100%;

      .title-main {
        font-size: 14px;
        font-weight: 700;
        color: #313238;
      }

      .table-main {
        padding: 12px 10px 0;
      }
    }
  }

  .abstract-table-header-row {
    background-color: #fafbfd;
  }
</style>
