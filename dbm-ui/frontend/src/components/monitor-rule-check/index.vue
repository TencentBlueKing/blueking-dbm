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
  <div class="rule-check-box">
    <div class="title-box">
      <span class="mr-8">
        <slot />
      </span>
      <span>{{ title }}</span>
    </div>
    <div class="if-box">
      <div class="control">
        if
      </div>
      <div class="details">
        <div
          class="common-disply io-box"
          style="width:180px;">
          {{ t('主机磁盘 IO 利用率') }}
        </div>
        <template
          v-for="(item, outerIndex) in localValue.config"
          :key="outerIndex">
          <template
            v-for="(rule, innerIndex) in item"
            :key="innerIndex">
            <div class="common-disply">
              {{ signMap[rule.method] }}
            </div>
            <div class="input-box">
              <NumberInput
                v-model="rule.threshold"
                :unit="localValue.unit_prefix" />
            </div>
            <div
              v-if="innerIndex < item.length - 1"
              class="condition">
              AND
            </div>
          </template>
          <div
            v-if="outerIndex < data.config.length - 1"
            class="condition">
            OR
          </div>
        </template>
      </div>
    </div>
    <div class="else-box">
      <div class="control">
        else
      </div>
      <span>{{ t('触发告警') }}</span>
    </div>
  </div>
</template>
<script lang="tsx">
  export const signMap: Record<string, string> = {
    gt: '>',
    gte: '>=',
    lt: '<',
    lte: '<=',
    eq: '=',
    neq: '!=',
  };
</script>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';

  import NumberInput from './NumberInput.vue';

  type Data = MonitorPolicyModel['test_rules'][0];

  interface Emits {
    (e: 'change', value: Data): void;
  }

  interface Props {
    title?: string,
    data: Data,
  }

  interface Exposes {
    getValue: () => Data,
    resetValue: () => void,
  }

  const props = withDefaults(defineProps<Props>(), {
    title: '',
    data: () => ({
      config: [],
      level: 1,
      type: 'Threshold',
      unit_prefix: '%',
    }),
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const localValue = ref(_.cloneDeep(props.data));

  watch(localValue, (data) => {
    emits('change', data);
  }, {
    deep: true,
  });


  defineExpose<Exposes>({
    getValue() {
      return localValue.value;
    },
    resetValue() {
      localValue.value = _.cloneDeep(props.data);
    },
  });

</script>
<style lang="less" scoped>
.rule-check-box {
  width: 100%;
  padding: 16px;
  border: 1px solid #DCDEE5;
  border-radius: 2px;

  .title-box {
    display: flex;
    width: 100%;
    font-weight: 700;
    color: #63656E;
    align-items: center;
  }

  .if-box {
    display: flex;
    width: 100%;
    margin-top: 16px;
    margin-bottom: 16px;
    gap: 4px;

    .details {
      flex: 1;
      flex-wrap: wrap;
      display: flex;
      gap: 4px;

      .common-disply {
        width: 32px;
        height: 32px;
        font-size: 12px;
        line-height: 32px;
        text-align: center;
        background: #F0F1F5;
        border-radius: 2px 0 0 2px;
      }

      .io-box {
        padding-left: 12px;
        text-align: left;
      }

      .condition {
        width: 32px;
        height: 32px;
        line-height: 32px;
        color: #FF9C01;
        text-align: center;
        background: #FFF3E1;
        border-radius: 2px;
      }
    }


  }

  .else-box {
    display: flex;
    width: 100%;
    align-items: center;
    gap: 9px;
  }
}

.control {
  width: 46px;
  height: 32px;
  line-height: 32px;
  color: #3A84FF;
  text-align: center;
  background: #F0F5FF;
  border-radius: 3px;
}
</style>
