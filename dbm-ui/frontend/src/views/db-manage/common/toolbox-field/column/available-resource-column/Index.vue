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
  <EditableColumn
    field="available_resource"
    :label="t('可用资源')"
    :min-width="150">
    <EditableBlock>
      <BkButton
        text
        theme="primary"
        @click="handleClick">
        {{ t('资源预览') }}
      </BkButton>
    </EditableBlock>
  </EditableColumn>
  <ResourcePreview
    v-model:is-show="showSlider"
    :params="params" />
</template>
<script lang="ts" setup>
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import ResourcePreview from './components/ResourcePreview.vue';

  interface Props {
    params: ComponentProps<typeof ResourcePreview>['params'];
  }

  defineProps<Props>();

  const { t } = useI18n();

  const showSlider = ref(false);

  const handleClick = () => {
    showSlider.value = true;
  };
</script>
