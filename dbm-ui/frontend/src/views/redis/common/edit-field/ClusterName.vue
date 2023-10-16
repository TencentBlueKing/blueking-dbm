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
  <TableEditInput
    ref="editRef"
    v-model="localValue"
    :placeholder="$t('请输入或选择集群')"
    :rules="rules"
    @submit="handleInputFinish" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { listClusterList } from '@services/redis/toolbox';

  import { useGlobalBizs } from '@stores';

  import { domainRegex } from '@common/regex';

  import TableEditInput from '@components/tools-table-input/index.vue';

  interface Props {
    data?: string;
    inputed?: string[];
  }

  interface Emits {
    (e: 'change', value: string): void
    (e: 'onInputFinish', value: string): void
  }

  interface Exposes {
    getValue: () => Promise<string>
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    inputed: () => ([]),
  });
  const emits = defineEmits<Emits>();

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const localValue = ref(props.data);
  const editRef = ref();

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('目标集群不能为空'),
    },
    {
      validator: (value: string) =>  domainRegex.test(value),
      message: t('目标集群输入格式有误'),
    },
    {
      validator: async (value: string) => {
        const r = await listClusterList(currentBizId, { domain: value });
        return r.length > 0;
      },
      message: t('目标集群不存在'),
    },
    {
      validator: (value: string) => props.inputed.filter(item => item === value).length < 2,
      message: t('目标集群重复'),
    },
  ];

  watch(() => props.data, (data) => {
    localValue.value = data;
  }, {
    immediate: true,
  });

  const handleInputFinish = (value: string) => {
    // editRef.value.getValue().then(() => {
    emits('onInputFinish', value);
    // });
  };

  defineExpose<Exposes>({
    getValue() {
      return editRef.value
        .getValue()
        .then(() => (localValue.value));
    },
  });
</script>

