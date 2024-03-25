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
  <BkLoading :loading="isLoading">
    <RenderText
      :data="slaveHost"
      :placeholder="t('选择目标主库后自动生成')"
      readonly />
  </BkLoading>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getRemoteMachineInstancePair } from '@services/source/mysqlCluster';

  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  interface Props {
    cloudId?: number;
    ip?: string;
  }

  interface Emits {
    (e: 'change', value: string): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const slaveHost = ref('');

  const { loading: isLoading, run: fetchRemoteMachineInstancePair } = useRequest(getRemoteMachineInstancePair, {
    manual: true,
    onSuccess(data) {
      const [machineInstancePair] = Object.values(data.machines);
      slaveHost.value = machineInstancePair.ip;
      emits('change', machineInstancePair.ip);
    },
  });

  watch(
    () => props.ip,
    () => {
      if (props.ip) {
        fetchRemoteMachineInstancePair({
          machines: [`${props.cloudId}:${props.ip}`],
        });
      } else {
        slaveHost.value = '';
        emits('change', '');
      }
    },
    {
      immediate: true,
    },
  );
</script>
