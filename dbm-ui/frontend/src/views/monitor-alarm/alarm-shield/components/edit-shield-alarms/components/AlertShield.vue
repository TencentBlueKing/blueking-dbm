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
  <BkFormItem
    :label="t('屏蔽范围')"
    required>
    <BkRadioGroup
      v-model="shieldRange"
      disabled>
      <BkRadio
        v-for="item in alarmRangeList"
        :key="item.label"
        :label="item.value">
        {{ item.label }}
      </BkRadio>
    </BkRadioGroup>
  </BkFormItem>
  <BkFormItem :label="t('告警内容')">
    <BkAlert
      v-if="isCurrentEvent"
      theme="info"
      :title="t('屏蔽的是告警内容的该类事件，不仅仅当前的事件还包括后续屏蔽时间内产生的事件')" />
    <BkAlert
      v-else
      theme="info"
      :title="t('屏蔽的是这个 IP 或实例产生的所有事件，不仅仅当前的事件还包括后续屏蔽时间内产生的事件')" />
    <div class="alarm-content-main">
      <div class="alarm-item">
        <div class="item-title">{{ t('策略名称') }}:</div>
        <div class="item-content">
          <span>{{ strategyInfo?.name || '--' }}</span>
        </div>
      </div>
      <div class="alarm-item">
        <div class="item-title">{{ t('告警级别') }}:</div>
        <div class="item-content">
          {{ data?._severity ? severityMap[data._severity] : '--' }}
        </div>
      </div>
      <div class="alarm-item">
        <div class="item-title">{{ t('所属业务') }}:</div>
        <div class="item-content">{{ bizDisplayName }}</div>
      </div>
      <div class="alarm-item">
        <div class="item-title">{{ t('所属集群') }}:</div>
        <div class="item-content">{{ clusterDisplay }}</div>
      </div>
      <div class="alarm-item">
        <div class="item-title">{{ t('触发条件') }}:</div>
        <div class="item-content">{{ data?._alert_message || '--' }}</div>
      </div>
    </div>
  </BkFormItem>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import AlarmShieldModel from '@services/model/monitor/alarm-shield';
  import { getPolicyList } from '@services/source/monitor';

  import { useGlobalBizs } from '@stores';

  interface Props {
    data?: AlarmShieldModel['dimension_config'];
  }

  type PolicyItem = ServiceReturnType<typeof getPolicyList>['results'][number];

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { bizs } = useGlobalBizs();

  const shieldRange = ref('alert');
  const strategyInfo = ref<PolicyItem>();

  const isCurrentEvent = computed(() => shieldRange.value === 'alert');
  const bizsMap = computed(() =>
    bizs.reduce<Record<number, string>>((results, item) => {
      Object.assign(results, {
        [item.bk_biz_id]: item.name,
      });
      return results;
    }, {}),
  );
  const bizDisplayName = computed(() => {
    if (props.data) {
      if (!props.data['tags.appid']) {
        return '--';
      }

      return bizsMap.value[Number(props.data['tags.appid'])];
    }

    return '--';
  });
  const clusterDisplay = computed(() => {
    if (props.data?.['tags.cluster_domain']) {
      return props.data['tags.cluster_domain'];
    }

    return '--';
  });

  const { run: fetchPolicyList } = useRequest(getPolicyList, {
    manual: true,
    onSuccess(data) {
      [strategyInfo.value] = data.results;
    },
  });

  const alarmRangeList = [
    {
      label: t('当前事件'),
      value: 'alert',
    },
    {
      label: t('整个集群'),
      value: 'strategy',
    },
  ];

  const severityMap: Record<number, string> = {
    1: t('致命'),
    2: t('告警'),
    3: t('提醒'),
  };

  watchEffect(() => {
    if (props.data) {
      shieldRange.value = props.data['tags.instance_role'] ? 'strategy' : 'alert';
    }
  });

  watch(
    () => props.data,
    () => {
      if (props.data?.strategy_id) {
        fetchPolicyList({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          monitor_policy_ids: `${props.data.strategy_id as number}`,
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less">
  .shiled-alarm-page {
    .bk-modal-content {
      padding: 20px 24px;

      .bk-form-label {
        font-weight: 700;
      }
    }

    .alarm-content-main {
      padding: 8px 25px;
      margin-top: 8px;
      font-size: 12px;
      background: #f5f7fa;
      border-radius: 2px;

      .alarm-item {
        display: flex;
        width: 100%;
        padding: 6px 0;
        line-height: 20px;

        .item-title {
          width: 60px;
        }

        .item-content {
          flex: 1;
          flex-wrap: wrap;

          .link-icon {
            margin-left: 5px;
            color: #3a84ff;
            cursor: pointer;
          }
        }
      }
    }
  }

  .quick-input-main {
    display: flex;
    margin-top: 8px;
    font-size: 12px;
    align-items: center;

    .quick-choose-item {
      margin-right: 4px;
      cursor: pointer;
    }
  }

  .shield-date-subtitle {
    position: absolute;
    top: -32px;
    left: 65px;
    font-size: 12px;
    color: #979ba5;
  }
</style>
