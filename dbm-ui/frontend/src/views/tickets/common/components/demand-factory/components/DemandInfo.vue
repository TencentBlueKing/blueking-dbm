<template>
  <div class="ticket-details">
    <div
      v-for="(dataItem, dataKey) in config"
      :key="dataKey"
      class="ticket-details-info"
      :class="{ 'ticket-details-info-no-title': !dataItem.title }">
      <strong
        v-if="dataItem.title"
        class="ticket-details-info-title">{{ dataItem.title }}</strong>
      <div class="ticket-details-list">
        <template
          v-for="(listItem, listKey) in dataItem.list"
          :key="listKey">
          <div
            v-if="listItem.key || listItem.render"
            class="ticket-details-item"
            :class="{
              'whole': listItem.iswhole,
              'table': listItem.isTable
            }">
            <span class="ticket-details-item-label">{{ listItem.label }}：</span>
            <span class="ticket-details-item-value">
              <Component
                :is="listItem.render"
                v-if="listItem.render" />
              <template v-else>{{ getValue(listItem.key as string) }} </template>
            </span>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="tsx" generic="T extends TicketDetailTypes">
  import _ from 'lodash';

  import type { TicketDetails } from '@services/types/ticket';

  import type { TicketDetailTypes } from '../common/types';

  export interface DemandInfoConfig {
    title?: string,
    list: {
      label: string,
      key?: string,
      iswhole?: boolean
      isTable?: boolean
      render?: () => VNode | string | null
    }[]
  }

  interface Props {
    data: TicketDetails<T>
    config: DemandInfoConfig[]
  }

  const props = defineProps<Props>();

  const getValue = (key: string) => {
    const { data } = props;

    // 扁平化 aaa.bbb 的形式
    if (key.includes('.')) {
      const keys = key.split('.');
      const value = keys.reduce((prevValue, key) => (prevValue as {[key: string]})[key], data);
      return _.isNil(value) ? '--' : value;
    }
    return _.isNil(data[key]) ? '--' : data[key];
  };
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .ticket-details {
    .ticket-details-info {
      padding-left: 82px;
      font-size: @font-size-mini;

      .ticket-details-info-title {
        color: @title-color;
      }
    }

    .ticket-details-info-no-title {
      padding-left: 0;
    }

    .ticket-details-list {
      .flex-center();

      max-width: 1000px;
      padding: 8px 0 16px;
      flex-wrap: wrap;
    }

    .ticket-details-item {
      .flex-center();

      overflow: hidden;
      line-height: 32px;
      flex: 0 0 50%;

      .ticket-details-item-label {
        flex-shrink: 0;
        min-width: 160px;
        text-align: right;
      }

      .ticket-details-item-value {
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

        .ticket-details-item-value {
          padding-top: 8px;
        }
      }
    }
  }
</style>
