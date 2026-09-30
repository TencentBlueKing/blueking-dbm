<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <EditableColumn
    field="slave.ip"
    :label="t('从库主机')"
    :loading="loading"
    :min-width="190"
    readonly
    required>
    <EditableBlock :placeholder="t('自动生成')">
      <span v-if="modelValue.ip">{{ modelValue.ip }}</span>
    </EditableBlock>
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getOracleHaInstanceList } from '@services/source/oracleHaCluster';

  import type { HostInfo } from '../types';
  import { buildHostInfo } from '../types';

  interface Props {
    master: {
      cluster_id: number;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<HostInfo>({
    required: true,
  });

  const { t } = useI18n();

  // 反查可用于切换的从库实例，取第一台
  const { loading, run: querySlave } = useRequest(getOracleHaInstanceList, {
    manual: true,
    onSuccess: (data) => {
      const [slaveInstance] = data.results;
      if (slaveInstance) {
        modelValue.value = buildHostInfo({
          bk_cloud_id: slaveInstance.bk_cloud_id,
          bk_host_id: slaveInstance.bk_host_id,
          ip: slaveInstance.ip,
        });
      }
    },
  });
  watch(
    () => props.master,
    () => {
      if (props.master.cluster_id) {
        querySlave({
          cluster_id: props.master.cluster_id,
          role: 'standby',
        });
      } else {
        modelValue.value = buildHostInfo({ ip: '' });
      }
    },
    {
      immediate: true,
    },
  );
</script>
