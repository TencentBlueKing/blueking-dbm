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
    :append-rules="rules"
    field="host.ip"
    fixed="left"
    :label="t('目标主机')"
    :loading="loading"
    :min-width="150"
    required>
    <template #headAppend>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-host-select"
        @click="handleShowSelector">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <EditableInput
      v-model="modelValue.ip"
      :placeholder="t('请输入IP')"
      @change="handleInputChange" />
  </EditableColumn>
  <InstanceSelector
    v-model:is-show="showSelector"
    active-tab="idleHosts"
    db-type="redis"
    :panel-list="['idleHosts', 'manualInput']"
    role="ip"
    :selected="selectedIps"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkInstance } from '@services/source/dbbase';

  import { ipv4 } from '@common/regex';

  import type { SpecInfo } from '@views/db-manage/redis/common/spec-panel/Index.vue';

  import InstanceSelector, { type InstanceSelectorValues } from './instance-selector/Index.vue';

  export type SelectorHost = InstanceSelectorValues['idleHosts'][0];

  interface Props {
    selected: {
      ip: string;
    }[];
  }

  interface Emits {
    (e: 'batch-edit', list: InstanceSelectorValues['idleHosts']): void;
    (e: 'append-row'): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id?: number;
    cluster_domain: string;
    cluster_ids: number[];
    ip: string;
    role: string;
    spec_config: SpecInfo;
  }>({
    default: () => ({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: undefined,
      cluster_domain: '',
      cluster_ids: [],
      ip: '',
      role: '',
      spec_config: {} as SpecInfo,
    }),
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const selectedIps = computed<InstanceSelectorValues>(() => ({
    idleHosts: props.selected.map(
      (item) =>
        ({
          ip: item.ip,
        }) as InstanceSelectorValues['idleHosts'][0],
    ),
  }));

  const rules = [
    {
      message: t('IP 格式不符合IPv4标准'),
      trigger: 'change',
      validator: (value: string) => ipv4.test(value),
    },
    {
      message: t('目标主机重复'),
      trigger: 'blur',
      validator: (value: string) => props.selected.filter((item) => item.ip === value).length < 2,
    },
    {
      message: t('目标主机不存在'),
      trigger: 'blur',
      validator: () => Boolean(modelValue.value.bk_host_id),
    },
  ];

  const { loading, run: queryHost } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      if (data.length) {
        const currentHost = data[0];
        const roleMap = {
          master: 'redis_master',
          proxy: 'proxy',
          slave: 'redis_slave',
        } as Record<string, string>;
        modelValue.value = {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: currentHost.bk_cloud_id,
          bk_host_id: currentHost.bk_host_id,
          cluster_domain: currentHost.master_domain,
          cluster_ids: currentHost.related_clusters.map((item) => item.id),
          ip: currentHost.ip,
          role: roleMap[currentHost.role] || '',
          spec_config: currentHost.spec_config,
        };
        // 输入的主机为master主机带出slave主机
        if (currentHost.role === 'master') {
          emits('append-row');
        }
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: undefined,
      cluster_domain: '',
      cluster_ids: [],
      ip: value,
      role: '',
      spec_config: {} as SpecInfo,
    };
    if (value) {
      queryHost({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        instance_addresses: [value],
      });
    }
  };

  const handleSelectorChange = (selected: InstanceSelectorValues) => {
    emits('batch-edit', selected.idleHosts);
  };
</script>
<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
