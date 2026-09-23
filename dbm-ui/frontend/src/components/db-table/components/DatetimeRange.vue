<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <ElConfigProvider :locale="elementLocale">
    <ElDatePickerPanel
      :key="refreshKey"
      v-model="localValue"
      :border="false"
      :default-time="defaultTime"
      :shortcuts="shortcuts"
      type="datetimerange"
      @update:model-value="handleChange" />
  </ElConfigProvider>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { ElConfigProvider, ElDatePickerPanel } from 'element-plus';
  import en from 'element-plus/es/locale/lang/en';
  import zhCn from 'element-plus/es/locale/lang/zh-cn';
  import { useI18n } from 'vue-i18n';

  export interface Props {
    shortcuts?: {
      text: string;
      value: () => [Date, Date];
    }[];
    value?: string;
  }

  defineOptions({
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  type Emits = (e: 'change', value: string) => void;

  const { locale } = useI18n();

  const elementLocale = computed(() => (locale.value === 'en' ? en : zhCn));

  const defaultTime: [Date, Date] = [new Date(2000, 1, 1, 0, 0, 0), new Date(2000, 2, 1, 23, 59, 59)];

  const refreshKey = ref(0);
  const localValue = ref<[string, string]>(['', '']);

  watch(
    () => props.value,
    () => {
      if (!props.value) {
        return;
      }
      const [startTime = '', endTime = ''] = props.value.split(',');
      localValue.value = [startTime, endTime];
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: (string | number | Date)[] | null) => {
    refreshKey.value = Date.now();

    // 面板底部「清空」会传 null
    if (!value) {
      emits('change', '');
      return;
    }
    const startDatetimeFormat = dayjs(value[0]).format('YYYY-MM-DD HH:mm:ss');
    const endDatetimeFormat = dayjs(value[1]).format('YYYY-MM-DD HH:mm:ss');
    emits('change', `${startDatetimeFormat},${endDatetimeFormat}`);
  };
</script>
