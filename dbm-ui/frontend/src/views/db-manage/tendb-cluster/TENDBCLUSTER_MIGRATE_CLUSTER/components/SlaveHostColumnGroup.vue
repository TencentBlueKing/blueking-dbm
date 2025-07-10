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
  <EditableColumn
    :label="t('目标从库主机')"
    :loading="loading"
    :min-width="150">
    <EditableBlock
      v-model="modelValue.ip"
      :placeholder="t('自动生成')" />
  </EditableColumn>
  <EditableColumn
    :label="t('从库主机关联实例')"
    :loading="loading"
    :min-width="150">
    <EditableBlock :placeholder="t('自动生成')">
      <p
        v-for="item in modelValue.related_instances"
        :key="item">
        {{ item }}
      </p>
    </EditableBlock>
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getRemoteMachineInstancePair } from '@services/source/mysqlCluster';

  interface Props {
    masterHost: {
      bk_cloud_id: number;
      ip: string;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
    related_instances: string[];
  }>({
    required: true,
  });

  const { t } = useI18n();

  const { loading, run: queryMachineInstancePair } = useRequest(getRemoteMachineInstancePair, {
    manual: true,
    onSuccess: (data) => {
      const [item] = Object.values(data.machines);
      if (item) {
        modelValue.value = {
          bk_biz_id: item.bk_biz_id,
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          ip: item.ip,
          related_instances: item.related_instances.map((item) => item.instance),
        };
      }
    },
  });

  watch(
    () => props.masterHost,
    () => {
      if (props.masterHost) {
        queryMachineInstancePair({
          machines: [`${props.masterHost.bk_cloud_id}:${props.masterHost.ip}`],
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
