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
  <BkLoading :loading="isLoading">
    <DateTimePicker
      ref="editRef"
      append-to-body
      class="render-box"
      clearable
      :model-value="dateValue"
      :placeholder="$t('请输入')"
      :rules="rules"
      type="datetime"
      @change="handleDatetimeChange" />
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DateTimePicker from '@views/redis/common/edit/DateTime.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    data?: IDataRow['targetDateTime'];
    isLoading?: boolean;
  }

  interface Exposes {
    getValue: () => Promise<string>
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    isLoading: false,
  });

  const { t } = useI18n();
  const editRef = ref();
  const dateValue = ref(props.data);

  const rules = [
    {
      validator: (value: string) => value !== '',
      message: t('请指定时间'),
    },
  ];

  const handleDatetimeChange = (date: string) => {
    dateValue.value = date;
  };

  defineExpose<Exposes>({
    getValue() {
      return editRef.value
        .getValue()
        .then(() => (dateValue.value));
    },
  });

</script>
<style lang="less" scoped>
.render-box {
  :deep(.icon-wrapper) {
    left: 10px;
    display: block;
    width: 32px;
  }

  :deep(input) {
    padding-left: 40px;
  }
}
</style>
