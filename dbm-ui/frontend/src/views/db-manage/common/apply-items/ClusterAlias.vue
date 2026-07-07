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
  <FormItemWithHint
    :label="t('集群别名')"
    property="details.cluster_alias"
    :required="required"
    :rules="rules">
    <DbInput
      v-model="modelValue"
      class="item-input"
      clearable
      :disabled="!bizId"
      :maxlength="100"
      :placeholder="t('请输入集群别名')"
      show-word-limit />
    <template #hint>
      {{ t('支持中文、字母、数字、连字符、下划线、点号，') }}
      <span class="hint-warning">{{ t('创建后可改') }}</span>
    </template>
  </FormItemWithHint>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  // import { verifyDuplicatedClusterName } from '@services/source/dbbase';
  import FormItemWithHint from '@components/form-item-with-hint/Index.vue';

  interface Props {
    bizId: number | '';
    // clusterType: ClusterTypes;
    required?: boolean;
  }

  defineProps<Props>();

  const modelValue = defineModel<string>();

  const { t } = useI18n();

  const rules = [
    {
      message: t('格式不正确，请勿使用特殊符号'),
      trigger: 'blur',
      validator: (val: string) => val === '' || /^[\u4e00-\u9fa5A-Za-z0-9_.-]*$/.test(val),
    },
    // {
    //   message: t('集群别名重复'),
    //   trigger: 'blur',
    //   validator: (val: string) => {
    //     if (!val) {
    //       return true;
    //     }
    //     if (!props.bizId) {
    //       return false;
    //     }
    //     return verifyDuplicatedClusterName({
    //       bk_biz_id: props.bizId,
    //       cluster_type: props.clusterType,
    //       name: val,
    //     }).then((data) => !data);
    //   },
    // },
  ];
</script>
