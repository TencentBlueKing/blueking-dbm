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
  <DbCard
    v-model:collapse="isTaskInfoCardCollapse"
    mode="collapse"
    :title="t('需求信息')">
    <ComFactory
      class="ticket-details-page"
      :data="data" />
    <InfoList>
      <Item
        :label="t('备注:')"
        style="width: 100%">
        <div style="line-height: 24px; white-space: normal">
          {{ data.remark || '--' }}
        </div>
      </Item>
    </InfoList>
  </DbCard>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';

  import InfoList, { Item } from './com-factory/components/info-list/Index.vue';
  import ComFactory from './com-factory/Index.vue';

  interface Props {
    data: TicketModel;
  }

  defineProps<Props>();

  defineOptions({
    name: 'TicketTaskInfo',
  });

  const { t } = useI18n();
  const route = useRoute();

  const isTaskInfoCardCollapse = ref(true);

  watch(
    route,
    () => {
      isTaskInfoCardCollapse.value = true;
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less">
  @import '@styles/mixins.less';

  .ticket-details-page {
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
      align-items: flex-start;

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
