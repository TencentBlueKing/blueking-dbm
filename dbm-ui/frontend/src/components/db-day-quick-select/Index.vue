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
  <BkSelect
    v-model="modelValue"
    class="db-day-quick-select"
    :clearable="clearable"
    :filterable="false"
    :placeholder="t('请选择时间范围')">
    <BkOption
      v-for="item in selectOptionList"
      :id="item.value"
      :key="item.value"
      :name="item.label" />
  </BkSelect>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    clearable?: boolean;
  }

  withDefaults(defineProps<Props>(), {
    clearable: false,
  });

  // v-model 绑定 time_range 相对时间表达式，默认最近 24 小时，支持清空为空值
  const modelValue = defineModel<string>({
    default: 'now -1d',
  });

  const { t } = useI18n();

  const selectOptionList = computed(() => [
    {
      label: t('最近 24 小时'),
      value: 'now -1d',
    },
    {
      label: t('最近 3 天'),
      value: 'now -3d',
    },
    {
      label: t('最近 7 天'),
      value: 'now -7d',
    },
    {
      label: t('最近 30 天'),
      value: 'now -30d',
    },
  ]);
</script>

<style lang="less" scoped>
  .db-day-quick-select {
    width: 150px;
  }
</style>
