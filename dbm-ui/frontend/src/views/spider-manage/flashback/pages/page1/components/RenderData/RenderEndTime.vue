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
  <div class="render-end-time">
    <TableEditDateTime
      ref="editRef"
      v-model="modelValue"
      :disabled="!startTime"
      :disabled-date="disableDate"
      :placeholder="t('请选择')"
      :rules="rules"
      type="datetime">
      <template #footer>
        <div
          style="line-height: 32px; text-align: center; cursor: pointer"
          @click.stop="handleNowTime">
          now
        </div>
      </template>
    </TableEditDateTime>
    <div
      v-if="isNowTime"
      class="value-now">
      now
    </div>
  </div>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useTimeZoneFormat } from '@hooks';

  import TableEditDateTime from '@components/render-table/columns/DateTime.vue';

  interface Props {
    startTime?: string;
  }

  interface Exposes {
    getValue: (field: string) => Promise<Record<'end_time', string>>;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    required: false,
  });

  const { t } = useI18n();
  const formatDateToUTC = useTimeZoneFormat();

  const editRef = ref();
  const isNowTime = ref(false);

  const disableDate = (date: Date) =>
    date && (date.valueOf() > Date.now() || date.valueOf() < dayjs(props.startTime).valueOf());

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('结束时间不能为空'),
    },
  ];

  watch(
    () => props.startTime,
    () => {
      modelValue.value = '';
    },
  );

  watch(modelValue, () => {
    isNowTime.value = false;
  });

  const handleNowTime = () => {
    isNowTime.value = true;
  };

  defineExpose<Exposes>({
    getValue() {
      if (isNowTime.value) {
        return Promise.resolve({
          end_time: '',
        });
      }
      return editRef.value.getValue().then(() => ({
        end_time: formatDateToUTC(modelValue.value!),
      }));
    },
  });
</script>
<style lang="less" scoped>
  .render-end-time {
    position: relative;

    .value-now {
      position: absolute;
      padding: 0 16px;
      pointer-events: none;
      cursor: pointer;
      background: #fff;
      inset: 0;
    }
  }
</style>
