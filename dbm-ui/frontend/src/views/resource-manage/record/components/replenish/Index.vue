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
  <div class="replenish-record-page">
    <Component
      :is="renderComponentMap[activeTab]"
      :key="activeTab" />
  </div>
</template>
<script setup lang="ts">
  import { useDebouncedRef } from '@hooks';

  import OperationView from './components/operation-view/Index.vue';
  import TicketView from './components/ticket-view/Index.vue';

  const route = useRoute();

  const renderComponentMap = {
    'operation-view': OperationView,
    'ticket-view': TicketView,
  } as Record<string, any>;

  const activeTab = useDebouncedRef('');

  watch(
    () => route.params,
    () => {
      activeTab.value = (route.params.page as string) || 'operation-view';
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less">
  .replenish-record-page {
    .bk-radio-button-label {
      font-size: 12px;
      line-height: 20px;
      display: flex;
      align-items: center;
    }

    .header-action {
      display: flex;
      align-items: center;
      padding-bottom: 16px;
      justify-content: space-between;
    }

    .forward-btn {
      font-size: 12px;
      position: relative;
      top: 2px;

      .db-icon-bk-dbm-icon {
        position: relative;
        top: 2px;
      }
    }

    .header-filters {
      display: flex;
      align-items: center;

      .date-time-picker {
        width: 320px !important;
      }
    }

    .replenish-record-list {
      font-family: MicrosoftYaHei;
      background: #fff;
      box-shadow: 0 2px 4px 0 rgba(25, 25, 41, 0.05);

      .bold-number {
        font-family: MicrosoftYaHei-Bold;
        font-weight: 700;
        font-size: 12px;
        color: #4d4f56;
        letter-spacing: 0;
        line-height: 20px;
        margin: 0px 2px;
      }

      .green-number {
        color: #2caf5e;
      }

      .red-number {
        color: #ea3636;
      }

      .table-footer {
        padding: 14px 16px;
        position: relative;
        z-index: 1;
        display: flex;
        height: 60px;
        padding: 0 16px;
        margin-top: -1px;
        background: #fff;
        border-top: 1px solid var(--td-component-border);
        align-items: center;

        .bk-pagination {
          width: 100%;

          & > .is-last {
            margin-left: auto;
          }
        }
      }
    }
  }
</style>
