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
  <div class="permission-retrieve">
    <BkCard
      is-collapse
      :title="t('查询条件')">
      <Options
        :account-type="accountType"
        class="ml-8"
        :loading="loading"
        @change="handleOptionsChange" />
    </BkCard>
    <BkCard
      class="mt-16"
      is-collapse
      :title="t('查询结果')">
      <Result
        ref="resultRef"
        class="ml-8"
        :options="options"
        @loading-change="handleLoadingChange" />
    </BkCard>
  </div>
</template>

<script setup lang="tsx">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import Options from './components/options/Index.vue';
  import Result from './components/result/Index.vue';

  import type { AccountTypes } from '@/common/const';

  interface Props {
    accountType: AccountTypes;
  }

  defineProps<Props>();

  const { t } = useI18n();

  const resultRef = ref<InstanceType<typeof Result>>();
  const loading = ref<boolean>(false);

  const options = shallowRef<ComponentProps<typeof Result>['options']>();

  const handleOptionsChange = (value: ComponentProps<typeof Result>['options']) => {
    options.value = value;
  };

  const handleLoadingChange = (value: boolean) => {
    loading.value = value;
  };
</script>

<style lang="less" scoped>
  .permission-retrieve {
    .bk-card {
      border: none;
      box-shadow: 0 2px 4px 0 #1919290d;

      :deep(.bk-card-head) {
        border-bottom: none;

        .title {
          margin-left: 8px;
          color: #313238;
        }
      }
    }
  }
</style>
