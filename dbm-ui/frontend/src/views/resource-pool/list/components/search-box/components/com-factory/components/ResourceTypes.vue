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
    filterable
    :input-search="false"
    :loading="isDbTypeListLoading"
    :model-value="defaultValue"
    multiple
    :placeholder="t('请选择专用 DB')"
    @change="handleChange">
    <BkOption
      v-for="item in dbTypeList"
      :key="item.id"
      :label="item.name"
      :value="item.id" />
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
  </BkSelect>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchDbTypeList } from '@services/infras';

  interface Props {
    defaultValue?: string[],
    simple?: boolean;
  }
  interface Emits {
    (e: 'change', value: Props['defaultValue']): void,
    (e: 'submit'): void,
    (e: 'cancel'): void,
  }

  defineProps<Props>();
  const emits = defineEmits<Emits>();
  defineOptions({
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const {
    data: dbTypeList,
    loading: isDbTypeListLoading,
  } = useRequest(fetchDbTypeList);

  const handleSubmit = () => {
    emits('submit');
  };
  const handleCancel = () => {
    emits('cancel');
  };

  const handleChange = (value: Props['defaultValue']) => {
    emits('change', value);
  };
</script>

