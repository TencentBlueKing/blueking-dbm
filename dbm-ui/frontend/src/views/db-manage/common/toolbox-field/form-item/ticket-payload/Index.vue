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
  <BkFormItem :label="t('备注')">
    <BkInput
      v-model="modelValue.remark"
      v-test="{ type: 'input', value: 'ticketRemark' }"
      :maxlength="500"
      :placeholder="t('请提供更多有用信息申请信息_以获得更快审批')"
      :style="{ maxWidth: `${width}px` }"
      type="textarea" />
  </BkFormItem>
</template>
<script lang="ts">
  interface TicketItem {
    remark: string;
  }
  export const createTicketPayload = (data = {} as TicketItem) => ({
    remark: data.remark || '',
  });
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  withDefaults(defineProps<{ width?: number }>(), {
    width: 560,
  });

  const modelValue = defineModel<TicketItem>({
    required: true,
  });

  const { t } = useI18n();
</script>
