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
  <div class="bk-diff">
    <div class="bk-diff__info">
      <strong class="pr-24">{{ $t('请确认以下差异变化') }}</strong>
      <div class="bk-diff__status bk-diff__status--create">
        <i class="bk-diff__status-square" />
        <span class="bk-diff__status-name">{{ $t('新增') }}</span>
        <strong class="bk-diff__status-count">{{ count.create ?? 0 }}</strong>
      </div>
      <div class="bk-diff__status bk-diff__status--delete">
        <i class="bk-diff__status-square" />
        <span class="bk-diff__status-name">{{ $t('删除') }}</span>
        <strong class="bk-diff__status-count">{{ count.delete ?? 0 }}</strong>
      </div>
      <div class="bk-diff__status bk-diff__status--update">
        <i class="bk-diff__status-square" />
        <span class="bk-diff__status-name">{{ $t('更新') }}</span>
        <strong class="bk-diff__status-count">{{ count.update ?? 0 }}</strong>
      </div>
    </div>

    <DbOriginalTable
      class="bk-diff__table mt-16"
      :columns="columns"
      :data="data"
      :max-height="maxHeight"
      :show-overflow-tooltip="false" />
  </div>
</template>

<script setup lang="tsx">
  import type { Column } from 'bkui-vue/lib/table/props';
  import { useI18n } from 'vue-i18n';

  import type { TableColumnRender } from '@/types/bkui-vue';

  interface Props {
    data?: Record<string, any>[],
    count?: {
      create: number,
      update: number,
      delete: number,
    },
    labels?: {
      label: string,
      key: string,
      render: (row: any, columnKey: string) => any
    }[],
    maxHeight?: string | number,
  }

  const props = withDefaults(defineProps<Props>(), {
    data: () => [],
    count: () => ({} as NonNullable<Props['count']>),
    labels: () => [],
    maxHeight: 'auto',
  });

  const { t } = useI18n();

  const columns: Column[] = [{
    label: t('参数名'),
    field: 'name',
    render: ({ cell, data }: TableColumnRender) => (
      <strong class={['bk-diff__parameter', `bk-diff__parameter--${data.status}`]} v-overflow-tips>{cell}</strong>
    ),
  }, {
    label: t('更新前'),
    field: 'before',
    render: ({ data }: TableColumnRender) => (
      <>
        {props.labels.map((label) => {
      const itemData = data.before;
      const displayValue = label.render ? label.render(data, 'before') : itemData[label.key];
      return (
        <div class="bk-diff__item">
          <span class="bk-diff__item-label">{label.label}</span>
          <span class="bk-diff__item-value text-overflow" v-overflow-tips>{displayValue}</span>
        </div>
      );
    })}
      </>
    ),
  }, {
    label: t('更新后'),
    field: 'after',
    render: ({ data }: TableColumnRender) => (
      <>
        {props.labels.map((label) => {
        const itemData = data.after;
        const displayValue = label.render ? label.render(data, 'after') : itemData[label.key];

        let { status } = data;
        if (status === 'update') {
          status = data.after[label.key] === data.before[label.key] ? '' : 'update';
        }
        const statusCls = status ? `bk-diff__item--${data.status}` : '';

        return (
          <div class={['bk-diff__item', statusCls]}>
            <span class="bk-diff__item-label">{label.label}</span>
            <span class="bk-diff__item-value text-overflow" v-overflow-tips>{displayValue}</span>
          </div>
        );
      })}
      </>
    ),
  }];
</script>

<style lang="less">
  @import '@styles/mixins.less';

  .bk-diff {
    padding: 24px;
    background-color: @bg-white;

    &__info {
      .flex-center();
    }

    &__status {
      .flex-center();

      margin-right: 16px;

      &-square {
        width: 12px;
        height: 12px;
        border: 1px solid transparent;
      }

      &-name {
        padding: 0 6px;
      }

      &--create {
        .bk-diff__status-square {
          background-color: #f2fff4;
          border-color: #b3ffc1;
        }

        .bk-diff__status-count {
          color: @success-color;
        }
      }

      &--delete {
        .bk-diff__status-square {
          background-color: #ffeded;
          border-color: #ffd2d2;
        }

        .bk-diff__status-count {
          color: @danger-color;
        }
      }

      &--update {
        .bk-diff__status-square {
          background-color: #fff4e2;
          border-color: #ffdfac;
        }

        .bk-diff__status-count {
          color: @warning-color;
        }
      }
    }

    &__table {
      .bk-table-head {
        th {
          &:nth-child(1),
          &:nth-child(1):hover {
            background-color: #f5f7fb;
          }

          &:nth-child(2),
          &:nth-child(2):hover {
            background-color: @bg-dark-gray;
            border-right: 1px solid @border-disable;
            border-left: 1px solid @border-disable;
          }

          &:nth-child(3),
          &:nth-child(3):hover {
            background-color: #eaebf0;
          }
        }
      }

      .bk-table-body {
        td {
          border-bottom: 1px solid @border-disable;
        }

        tr:hover td {
          background-color: transparent !important;
        }

        .cell {
          height: auto !important;
          padding: 12px !important;
          line-height: normal !important;
          border-bottom: none !important;
        }
      }
    }

    &__parameter {
      &--create {
        color: @success-color;
      }

      &--delete {
        color: @danger-color;
        text-decoration: line-through;
      }
    }

    &__item {
      .flex-center();

      padding: 0 16px;
      margin-bottom: 8px;
      line-height: 30px;
      background-color: #f5f7fa;

      &:last-child {
        margin-bottom: 0;
      }

      &-label {
        flex-shrink: 0;
      }

      &-value {
        flex: 1;
        font-weight: bold;
      }

      &--create {
        background-color: #f0fcf4;

        .bk-diff__item-value {
          color: @success-color;
        }
      }

      &--delete {
        background-color: #fef2f2;

        .bk-diff__item-value {
          color: @danger-color;
        }
      }

      &--update {
        background-color: #fff9ef;

        .bk-diff__item-value {
          color: @warning-color;
        }
      }
    }
  }
</style>
