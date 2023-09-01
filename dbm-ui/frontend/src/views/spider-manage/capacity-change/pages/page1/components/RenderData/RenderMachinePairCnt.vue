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
    ref="inputRef"
    :disabled="!isValid"
    :model-value="`${clusterData ? clusterData.machine_pair_cnt : ''}`"
    :placeholder="t('输入集群后自动生成')"
    :readonly="isValid"
    textarea />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type SpiderModel from '@services/model/spider/spider';

  import TableEditInput from '@views/spider-manage/common/edit/Input.vue';

  interface Props {
    clusterData?: SpiderModel
  }
  interface Exposes {
    getValue: () => Promise<any>
  }

  const props = defineProps<Props>();

  const isValid = computed(() => !!props.clusterData);

  const { t } = useI18n();

  defineExpose<Exposes>({
    getValue() {
      return Promise.resolve({});
    },
  });
</script>
