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
  <div class="render-host-box">
    <TableEditInput
      ref="editRef"
      v-model="localValue"
      :placeholder="$t('请输入单个(IP 或 域名):Port')"
      :rules="rules"
      @submit="handleInputFinish" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { domainPort, ipPort } from '@common/regex';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    data?: IDataRow['targetCluster'];
  }

  interface Exposes {
    getValue: () => Promise<string>;
  }

  interface Emits {
    (e: 'input-finish', value: string): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const localValue = ref(props.data);
  const editRef = ref();

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('目标集群不能为空'),
    },
    {
      validator: (value: string) => ipPort.test(value) || domainPort.test(value),
      message: t('目标集群格式不正确'),
    },
  ];

  const handleInputFinish = (value: string) => {
    emits('input-finish', value);
  };

  defineExpose<Exposes>({
    getValue() {
      return editRef.value.getValue().then(() => localValue.value);
    },
  });
</script>
<style lang="less" scoped>
  .render-host-box {
    position: relative;
  }
</style>
