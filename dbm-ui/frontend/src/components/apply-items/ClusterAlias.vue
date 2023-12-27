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
  <BkFormItem
    :label="$t('集群名称')"
    property="details.cluster_alias"
    :rules="rules">
    <BkInput
      class="item-input"
      :disabled="!bizId"
      :maxlength="63"
      :model-value="modelValue"
      :placeholder="$t('用于区分不同集群_可随时修改')"
      show-word-limit
      @change="handleChange" />
  </BkFormItem>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { verifyDuplicatedClusterName } from '@services/source/dbbase';

  interface Props {
    modelValue: string,
    bizId: number|'',
    clusterType: string
  }
  interface Emits {
    (e: 'update:modelValue', value: string): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const rules = [
    {
      validator: (val: string) => val === '' || /^[\u4e00-\u9fa5A-Za-z0-9-]*$/.test(val),
      message: t('只能包含中文_英文字母_数字_连字符'),
      trigger: 'blur',
    },
    {
      validator: (val: string) => {
        if (!val) {
          return true;
        }
        if (!props.bizId) {
          return false;
        }
        return verifyDuplicatedClusterName({
          name: val,
          bk_biz_id: props.bizId,
          cluster_type: props.clusterType,
        }).then(data => !data);
      },
      message: t('集群名称重复'),
      trigger: 'blur',
    },
  ];

  const handleChange = (value: string) => {
    emits('update:modelValue', value);
  };
</script>

