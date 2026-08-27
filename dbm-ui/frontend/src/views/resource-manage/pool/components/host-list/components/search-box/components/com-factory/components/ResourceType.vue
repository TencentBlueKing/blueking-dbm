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
  <DbSelect
    filterable
    :input-search="false"
    :model-value="defaultValue"
    :placeholder="t('请选择所属DB类型')"
    show-selected-icon
    @change="handleChange">
    <DbOptionGroup group-style="divider">
      <DbOption
        v-for="item in readResourceDbTypes"
        :key="item.value"
        :label="item.label"
        :value="item.value" />
    </DbOptionGroup>
    <DbOptionGroup group-style="divider">
      <DbOption
        :label="specialOptionLabelMap[SpecialOptions.PUBLIC]"
        :value="SpecialOptions.PUBLIC" />
    </DbOptionGroup>
    <template
      v-if="simple"
      #extension>
      <div class="resourece-pool-serach-item-action">
        <div
          class="action-item"
          @click="handleSubmit">
          {{ t('确认') }}
        </div>
        <div
          class="action-item"
          @click="handleCancel">
          {{ t('取消') }}
        </div>
      </div>
    </template>
  </DbSelect>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { readResourceDbTypes, specialOptionLabelMap, SpecialOptions } from '@common/const';

  interface Props {
    defaultValue?: string;
    simple?: boolean;
  }

  interface Emits {
    (e: 'change', value: Props['defaultValue']): void;
    (e: 'submit'): void;
    (e: 'cancel'): void;
  }

  defineOptions({
    inheritAttrs: false,
  });

  withDefaults(defineProps<Props>(), {
    defaultValue: '',
    simple: false,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const handleSubmit = () => {
    emits('submit');
  };
  const handleCancel = () => {
    emits('cancel');
  };

  const handleChange = (value: string) => {
    emits('change', value);
  };
</script>
