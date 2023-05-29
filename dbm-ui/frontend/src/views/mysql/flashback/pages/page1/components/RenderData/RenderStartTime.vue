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
  <div class="render-start-time-box">
    <TableEditDateTime
      ref="editRef"
      :disabled-date="disableDate"
      :model-value="localValue"
      :placeholder="$t('请选择')"
      :rules="rules"
      type="datetimerange"
      @change="handleChange" />
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TableEditDateTime from '@views/mysql/common/edit/DateTime.vue';

  interface Props {
    modelValue?: [string, string]
  }

  interface Exposes {
    getValue: (field: string) => Promise<Record<'start_time'|'end_time', string>>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const editRef = ref();
  const localValue = ref<Required<Props>['modelValue']>(['', '']);

  const disableDate = (date: Date) => date && date.valueOf() > Date.now();

  const rules = [
    {
      validator: (value: Required<Props>['modelValue']) => {
        if (value.length !== 2) {
          return false;
        }
        return _.filter(value, item => _.trim(item)).length > 0;
      },
      message: t('起止时间不能为空'),
    },
  ];

  watch(() => props.modelValue, () => {
    if (props.modelValue) {
      localValue.value = props.modelValue;
    } else {
      localValue.value = ['', ''];
    }
  }, {
    immediate: true,
  });

  const handleChange = (value: Required<Props>['modelValue']) => {
    localValue.value = value;
  };

  defineExpose<Exposes>({
    getValue() {
      return editRef.value.getValue()
        .then(() => ({
          start_time: localValue.value[0],
          end_time: localValue.value[1],
        }));
    },
  });
</script>
<style lang="less">
  .render-start-time-box {
    display: block;
  }
</style>
