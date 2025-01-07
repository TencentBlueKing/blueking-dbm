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
  <Column
    field="slave.ip"
    :label="t('从库主机')"
    :loading="loading"
    :min-width="150">
    <Block
      v-model="modelValue.ip"
      :placeholder="t('自动生成')" />
  </Column>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getRemoteMachineInstancePair } from '@services/source/mysqlCluster';

  import { Block, Column } from '@components/editable-table/Index.vue';

  interface Props {
    master: {
      bk_cloud_id: number;
      ip: string;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    bk_cloud_id: number;
    bk_host_id?: number;
    ip: string;
  }>({
    default: () => ({
      bk_cloud_id: 0,
      bk_host_id: undefined,
      ip: '',
    }),
  });

  const { t } = useI18n();

  const { run: fetchRemoteMachineInstancePair, loading } = useRequest(getRemoteMachineInstancePair, {
    manual: true,
    onSuccess: (data) => {
      if (data.machines) {
        const [machineInstancePair] = Object.values(data.machines);
        modelValue.value = {
          bk_host_id: machineInstancePair.bk_host_id,
          bk_cloud_id: machineInstancePair.bk_cloud_id,
          ip: machineInstancePair.ip,
        };
      }
    },
  });

  watch(
    () => props.master.ip,
    () => {
      if (props.master.ip) {
        fetchRemoteMachineInstancePair({
          machines: [`${props.master.bk_cloud_id}:${props.master.ip}`],
        });
      } else {
        modelValue.value = {
          bk_cloud_id: 0,
          bk_host_id: undefined,
          ip: '',
        };
      }
    },
    {
      immediate: true,
    },
  );
</script>
