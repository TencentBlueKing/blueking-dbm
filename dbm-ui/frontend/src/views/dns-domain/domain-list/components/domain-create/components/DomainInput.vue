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
  <BkInput
    v-model="modelValue"
    class="dns-domain-input"
    :placeholder="t('请输入域名前缀，如 api.game')">
    <template #suffix>
      <span class="dns-domain-input-suffix">{{ DOMAIN_SUFFIX }}</span>
    </template>
  </BkInput>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { DOMAIN_SUFFIX } from '@views/dns-domain/utils';

  // 域名前缀，不含固定后缀 .db
  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();
</script>
<style lang="less">
  .dns-domain-input {
    .dns-domain-input-suffix {
      display: inline-flex;
      height: 100%;
      padding: 0 8px;
      color: #63656e;
      background: #f5f7fa;
      border-left: 1px solid #dcdee5;
      align-items: center;
    }
  }
</style>
