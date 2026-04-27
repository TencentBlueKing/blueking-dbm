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
  <div class="db-toolbox">
    <BkAlert
      class="mb-20"
      closable
      :title="
        t('MongoDB版本升级将按版本链逐级执行_如4_4_6_0自动拆分为4_4_5_0_6_0两阶段__同一主机上的关联集群需一并升级')
      " />
    <BkForm
      class="toolbox-form"
      form-type="vertical"
      :model="modelValue">
      <BkFormItem
        :label="t('升级策略')"
        property="strategy"
        required>
        <div class="strategy-cards">
          <CardCheckbox
            v-model="modelValue.strategy"
            :desc="t('节点逐个升级_服务不中断_RS会发生主从切换_Mongos连接短暂中断_适用于生产环境')"
            icon="bk-dbm-icon db-icon-gundongshengji"
            :title="t('滚动升级')"
            true-value="rolling" />
          <CardCheckbox
            v-model="modelValue.strategy"
            class="ml-8"
            :desc="t('所有节点同时停止_升级_启动_有服务中断_适用于测试环境或可接受停机窗口的场景')"
            icon="bk-dbm-icon db-icon-tingjishengji"
            :title="t('停机升级')"
            true-value="full_stop" />
        </div>
      </BkFormItem>
      <slot />
    </BkForm>
  </div>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  type Emits = (e: 'change') => void;

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    strategy: 'rolling' | 'full_stop';
  }>({
    required: true,
  });

  const { t } = useI18n();

  watch(
    () => modelValue.value.strategy,
    () => {
      emits('change');
    },
  );
</script>

<style lang="less" scoped>
  .db-toolbox {
    padding-bottom: 20px;
  }

  .strategy-cards {
    display: flex;
    gap: 8px;
  }
</style>
