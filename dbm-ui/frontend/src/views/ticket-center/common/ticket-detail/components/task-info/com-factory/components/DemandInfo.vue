<template>
  <div
    v-for="(dataItem, dataKey) in config"
    :key="dataKey"
    class="demand-info"
    :class="{ 'demand-info-no-title': !dataItem.title }">
    <strong
      v-if="dataItem.title"
      class="demand-info-title">
      {{ dataItem.title }}
    </strong>
    <div class="demand-info-list">
      <template
        v-for="(listItem, listKey) in dataItem.list"
        :key="listKey">
        <div
          v-if="!listItem.isHidden && (listItem.key || listItem.render)"
          class="demand-info-item"
          :class="{
            whole: listItem.iswhole,
            table: listItem.isTable,
          }">
          <span class="demand-info-item-label">{{ listItem.label }}：</span>
          <span class="demand-info-item-value">
            <Component
              :is="listItem.render"
              v-if="listItem.render" />
            <template v-else>{{ getValue(listItem.key as string) }} </template>
          </span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import _ from 'lodash';

  import TicketModel from '@services/model/ticket/ticket';

  export interface DemandInfoConfig {
    title?: string;
    list: {
      label: string;
      key?: string;
      iswhole?: boolean;
      isTable?: boolean;
      isHidden?: boolean;
      render?: () => VNode | string | null;
    }[];
  }

  interface Props {
    data: TicketModel;
    config: DemandInfoConfig[];
  }

  const props = defineProps<Props>();

  const getValue = (key: string) => {
    const { data } = props;

    // 扁平化 aaa.bbb 的形式
    if (key.includes('.')) {
      const keys = key.split('.');
      const value = keys.reduce((prevValue, key) => (prevValue as { [key: string] })[key], data);
      return _.isNil(value) ? '--' : value;
    }
    return _.isNil(data[key]) ? '--' : data[key];
  };
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .demand-info {
    font-size: @font-size-mini;

    .demand-info-title {
      color: @title-color;
    }

    .demand-info-no-title {
      padding-left: 0;
    }

    .demand-info-list {
      .flex-center();

      max-width: 1000px;
      padding: 8px 0 16px;
      flex-wrap: wrap;
    }

    .demand-info-item {
      .flex-center();

      overflow: hidden;
      line-height: 32px;
      flex: 0 0 50%;
      align-items: flex-start;

      .demand-info-item-label {
        flex-shrink: 0;
        min-width: 160px;
        text-align: right;
      }

      .demand-info-item-value {
        overflow: hidden;
        color: @title-color;
        text-overflow: ellipsis;
        white-space: nowrap;
        flex: 1;

        .host-nums {
          cursor: pointer;

          a {
            font-weight: bold;
          }
        }
      }

      &.whole {
        align-items: flex-start;
        flex: 0 0 100%;
      }

      &.table {
        align-items: flex-start;
        flex: 0 0 100%;

        .demand-info-item-value {
          padding-top: 8px;
        }
      }
    }
  }
</style>
