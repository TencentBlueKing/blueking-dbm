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
    :append-rules="rules"
    field="source.bk_host_innerip"
    fixed="left"
    :label="t('源客户端IP')"
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
    <Input
      v-model="modelValue.bk_host_innerip"
      :placeholder="t('请输入管控区域IP')"
      @change="handleInputChange" />
    <IpSelector
      v-model:show-dialog="showSelector"
      :biz-id="currentBizId"
      button-text=""
      :data="selectedHosts"
      service-mode="all"
      :show-view="false"
      @change="handleSelectorChange" />
  </Column>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getHostTopoInfos } from '@services/source/ipchooser';
  import type { HostInfo } from '@services/types';

  import { useGlobalBizs } from '@stores';

  import { netIp } from '@common/regex';

  import { Column, Input } from '@components/editable-table/Index.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  export type SelectorHost = HostInfo;

  interface Props {
    selected: {
      ip: string;
    }[];
  }

  interface Emits {
    (e: 'batch-edit', list: HostInfo[]): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_cloud_id?: number;
    bk_host_id?: number;
    ip: string;
    bk_host_innerip: string;
  }>({
    default: () => ({
      bk_cloud_id: undefined,
      bk_host_id: undefined,
      ip: '',
      bk_host_innerip: '',
    }),
  });

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const showSelector = ref(false);
  const selectedHosts = computed(() =>
    props.selected.map(
      (item) =>
        ({
          ip: item.ip,
        }) as HostInfo,
    ),
  );

  const rules = [
    {
      validator: (value: string) => netIp.test(value),
      message: t('源客户端 IP 格式不正确'),
      trigger: 'change',
    },
    {
      validator: (value: string) => props.selected.filter((item) => item.ip === value).length < 2,
      message: t('源客户端 IP 重复'),
      trigger: 'change',
    },
    {
      validator: () => Boolean(modelValue.value.bk_host_id),
      message: t('源客户端 IP 不存在'),
      trigger: 'blur',
    },
  ];

  const { run: queryHost, loading } = useRequest(getHostTopoInfos, {
    manual: true,
    onSuccess: (data) => {
      if (data.hosts_topo_info.length > 0) {
        const [currentHost] = data.hosts_topo_info;
        modelValue.value = {
          bk_cloud_id: currentHost.bk_cloud_id,
          bk_host_id: currentHost.bk_host_id,
          ip: currentHost.ip,
          bk_host_innerip: `${currentHost.bk_cloud_id}:${currentHost.ip}`,
        };
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = {
      bk_cloud_id: undefined,
      bk_host_id: undefined,
      ip: '',
      bk_host_innerip: value,
    };
    if (value) {
      queryHost({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        filter_conditions: {
          bk_host_innerip: [value],
        },
      });
    }
  };

  const handleSelectorChange = (selected: HostInfo[]) => {
    emits('batch-edit', selected);
  };
</script>
<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
