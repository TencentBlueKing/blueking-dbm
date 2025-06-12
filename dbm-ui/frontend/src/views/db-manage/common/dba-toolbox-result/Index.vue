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
    class="mysql-operation-success-page"
    :loading="isLoading">
    <div style="font-size: 64px; color: #2dcb56">
      <DbIcon type="check-circle-fill" />
    </div>
    <div style="margin-top: 36px; font-size: 24px; line-height: 32px; color: #313238">
      {{ t('xx任务提交成功', { name: targetRoute.meta.navName }) }}
    </div>
    <div style="margin-top: 16px; font-size: 14px; line-height: 22px; color: #63656e">
      <I18nT
        keypath="已按业务生成n个单据_您可点击单号查看详情"
        tag="span">
        <span class="number-style">{{ taskCount }}</span>
      </I18nT>
    </div>
    <div class="operation-steps">
      <div
        v-for="(item, index) in renderSteps"
        :key="index"
        class="step-item">
        <div class="step-status">
          <div
            :class="[
              index === currentIndex ? 'status-loading' : 'status-dot',
              {
                'status-dot--success': index < currentIndex,
              },
            ]" />
        </div>
        <div>{{ item.name }}</div>
      </div>
    </div>
    <div class="action">
      <BkButton
        class="ml8"
        theme="primary"
        @click="handleStepChange">
        {{ t('再次提单') }}
      </BkButton>
    </div>
    <BkTable
      class="result-table"
      :data="tableData"
      :loading="isLoading"
      :show-overflow="false">
      <BkTableColumn
        :label="t('单号')"
        :width="250">
        <template #default="{ data: rowData }: { data: RowData }">
          <BkButton
            text
            theme="primary"
            @click="() => handleOpenBizTicket(rowData)">
            {{ rowData.id }}
          </BkButton>
        </template>
      </BkTableColumn>
      <BkTableColumn
        :label="t('业务')"
        :width="250">
        <template #default="{ data: rowData }: { data: RowData }">
          {{ getBizInfoById(rowData.bk_biz_id)?.name || '--' }}
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('集群')">
        <template #default="{ data: rowData }: { data: RowData }">
          <div v-if="rowData.related_object?.objects?.length > 0">
            <p
              v-for="item in rowData.related_object.objects"
              :key="item">
              {{ item }}
            </p>
          </div>
          <span v-else>--</span>
        </template>
      </BkTableColumn>
    </BkTable>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getTickets } from '@services/source/ticket';

  import { useGlobalBizs } from '@/stores';
  import { useTimeoutPoll } from '@vueuse/core';

  type RowData = ServiceReturnType<typeof getTickets>['results'][0];

  interface Props {
    steps?: Array<{ current?: boolean; name: string }>;
  }

  const props = withDefaults(defineProps<Props>(), {
    steps: () => [],
  });

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { getBizInfoById } = useGlobalBizs();

  const { ticketIds, ticketType } = route.params;

  const targetRoute = router.resolve({
    name: `DBA_${ticketType}` as string,
  });

  const tableData = ref<RowData[]>([]);
  const taskCount = ref(0);
  const taskPool = ref<number[]>([]);
  const isLoading = computed(() => tableData.value.length < taskCount.value);

  const renderSteps = computed(() =>
    props.steps.length > 0
      ? props.steps
      : [{ name: t('单据审批') }, { name: t('xx执行', { name: targetRoute.meta.navName }) }, { name: t('任务完成') }],
  );

  const currentIndex = computed(() => {
    const index = _.findIndex(props.steps, (item) => Boolean(item.current));
    return Math.max(index, 0);
  });

  // 轮询
  const { isActive, pause, resume } = useTimeoutPoll(() => {
    if (!taskPool.value.length) {
      return;
    }
    queryTicketDetails({
      id: taskPool.value.pop(),
    });
  }, 2000);

  const { run: queryTicketDetails } = useRequest(getTickets, {
    manual: true,
    onSuccess(data) {
      const [info] = data.results;
      tableData.value.push(info);
      if (isActive.value && tableData.value.length === taskCount.value) {
        pause();
      }
    },
  });

  const handleStepChange = () => {
    router.push({
      name: `DBA_${ticketType}`,
    });
  };

  const handleOpenBizTicket = (rowData: RowData) => {
    const path = router
      .resolve({
        name: 'bizTicketManage',
        params: {
          ticketId: rowData.id,
        },
      })
      .href.replace(/^\/(\d+)/, `${rowData.bk_biz_id}`);

    window.open(`${window.location.origin}/${path}`, '_blank');
  };

  watch(
    renderSteps,
    () => {
      taskPool.value = (ticketIds as string).split(',').map((item) => Number(item));
      taskCount.value = taskPool.value.length;
      resume();
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less">
  .mysql-operation-success-page {
    display: block;
    padding-top: 100px;
    text-align: center;

    .action {
      margin-top: 32px;
    }

    .operation-steps {
      display: flex;
      margin-top: 24px;
      margin-bottom: 32px;
      font-size: 14px;
      line-height: 22px;
      color: #63656e;
      justify-content: center;

      .step-item {
        padding: 0 22px;

        &:first-child {
          .step-status::before {
            content: none;
          }
        }

        &:last-child {
          .step-status::after {
            content: none;
          }
        }
      }

      .step-status {
        position: relative;
        display: flex;
        height: 14px;
        margin-bottom: 20px;
        justify-content: center;
        align-items: center;

        &::before,
        &::after {
          position: absolute;
          top: 50%;
          width: calc(50% + 22px);
          height: 1px;
          background: #d8d8d8;
          content: '';
        }

        &::before {
          right: 50%;
        }

        &::after {
          left: 50%;
        }
      }

      .status-loading,
      .status-dot {
        z-index: 1;
        background: #fff;

        &--success {
          background-color: rgb(45 203 86);
          border-color: rgb(45 203 86) !important;
        }
      }

      .status-loading {
        position: relative;
        display: flex;
        width: 13px;
        height: 13px;
        border: 2px solid #3a84ff;
        border-radius: 50%;
        align-items: center;
        justify-content: center;

        &::after {
          width: 5px;
          height: 5px;
          border: 1px solid #3a84ff;
          border-top-color: white;
          border-radius: 50%;
          content: '';
          opacity: 60%;
          animation: rotate-loading 1.5s linear infinite;
        }
      }

      .status-dot {
        width: 10px;
        height: 10px;
        border: 2px solid #d8d8d8;
        border-radius: 50%;
      }
    }

    .result-table {
      margin: 36px 18%;
    }

    .number-style {
      font-family: 'Microsoft YaHei', sans-serif;
      font-size: 14px;
      font-weight: 700;
      line-height: 22px;
      color: #3a84ff;
    }
  }
</style>
