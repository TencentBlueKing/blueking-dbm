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
    <div class="render-switch-box">
      <TableEditSelect
        ref="selectRef"
        v-model="localValue"
        :list="selectList"
        :placeholder="$t('请选择')"
        :rules="rules"
        @change="(value) => handleChange(value as string)" />
    </div>
  </BkLoading>
</template>
<script lang="ts">
  export enum OnlineSwitchType {
    USER_CONFIRM = 'user_confirm',
    NO_CONFIRM = 'no_confirm'
  }
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TableEditSelect from '@views/redis/common/edit/Select.vue';

  interface Props {
    isLoading?: boolean;
  }

  interface Exposes {
    getValue: () => Promise<string>
  }

  defineProps<Props>();

  const { t } = useI18n();

  const selectRef = ref();
  const localValue = ref(OnlineSwitchType.USER_CONFIRM);

  const selectList = [
    {
      id: OnlineSwitchType.USER_CONFIRM,
      name: t('需人工确认'),
    },
    {
      id: OnlineSwitchType.NO_CONFIRM,
      name: t('无需确认'),
    },
  ];

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('请选择切换模式'),
    },
  ];

  const handleChange = (value: string) => {
    localValue.value = value as OnlineSwitchType;
  };

  defineExpose<Exposes>({
    getValue() {
      return selectRef.value
        .getValue()
        .then(() => (localValue.value));
    },
  });
</script>
<style lang="less" scoped>
  .render-switch-box {
    padding: 0;
    color: #63656e;

    :deep(.bk-input--text) {
      border: none;
      outline: none;
    }
  }
</style>
