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
    <TableEditInput
      ref="inputRef"
      :model-value="slaveHostData?.ip"
      :placeholder="t('选择目标主库后自动生成')"
      readonly
      :rules="rules" />
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getRemoteMachineInstancePair } from '@services/mysqlCluster';

  import TableEditInput from '@views/spider-manage/common/edit/Input.vue';

  import type { IHostData } from './Row.vue';

  interface Props {
    masterData?: IHostData
  }

  interface Exposes {
    getValue: (field: string) => Promise<string>
  }

  interface ISlaveHost {
    bk_cloud_id: number,
    bk_host_id: number,
    ip: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const inputRef = ref();
  const slaveHostData = ref<ISlaveHost>();

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('从库主机不能为空'),
    },
  ];

  const {
    loading: isLoading,
    run: fetchRemoteMachineInstancePair,
  } = useRequest(getRemoteMachineInstancePair, {
    manual: true,
    onSuccess(data) {
      const [machineInstancePair] = Object.values(data.machines);
      slaveHostData.value = {
        bk_host_id: machineInstancePair.bk_host_id,
        bk_cloud_id: machineInstancePair.bk_cloud_id,
        ip: machineInstancePair.ip,
      };
    },
  });

  watch(() => props.masterData, () => {
    if (props.masterData) {
      fetchRemoteMachineInstancePair({
        machines: [`${props.masterData.bk_cloud_id}:${props.masterData.ip}`],
      });
    }
  }, {
    immediate: true,
  });


  defineExpose<Exposes>({
    getValue() {
      return inputRef.value
        .getValue()
        .then(() => ({
          slave: slaveHostData.value,
        }));
    },
  });
</script>
