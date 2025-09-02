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
    field="source"
    fixed="left"
    :label="t('源客户端IP')"
    :loading="loading"
    :min-width="150"
    required>
    <template #headAppend>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-host-select"
        @click="handleShowIpSelector">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <EditableInput
      v-model="localValue"
      :placeholder="t('请输入管控区域:IP或从表头批量选择')"
      @change="handleChange" />
    <IpSelector
      v-model:show-dialog="isShowIpSelector"
      :biz-id="currentBizId"
      button-text=""
      :data="selectedIps"
      :only-alive-host="false"
      service-mode="all"
      :show-view="false"
      @change="handleSelectorChange" />
  </EditableColumn>
  <EditableColumn
    field="module"
    :label="t('模块')"
    :loading="loading"
    :min-width="150"
    required>
    <EditableBlock
      v-model="module"
      :placeholder="t('输入集群后自动生成')" />
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getHostTopoInfos } from '@services/source/ipchooser';
  import type { HostInfo } from '@services/types';

  import { netIp } from '@common/regex';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  type Emits = (e: 'batch-edit', list: HostInfo[]) => void;

  const emits = defineEmits<Emits>();

  const bkCloudId = defineModel<number>('bkCloudId', {
    required: true,
  });

  const source = defineModel<string>('source', {
    required: true,
  });

  const module = defineModel<string>('module', {
    required: true,
  });

  const { t } = useI18n();

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const localValue = ref('');
  const isShowIpSelector = ref(false);
  const selectedIps = shallowRef<HostInfo[]>([]);

  const rules = [
    {
      message: t('IP格式有误，请输入合法IP'),
      trigger: 'change',
      validator: () => !localValue.value || netIp.test(localValue.value),
    },
    {
      message: t('源客户端IP不存在'),
      trigger: 'blur',
      validator: () => !localValue.value || Boolean(source.value),
    },
  ];

  const { loading, run: fetchHostTopoInfo } = useRequest(getHostTopoInfos, {
    manual: true,
    onSuccess: (data) => {
      const [find] = data.hosts_topo_info;
      if (find) {
        [module.value] = find.topo;
        source.value = find.ip;
        bkCloudId.value = find.bk_cloud_id;
      } else {
        module.value = '';
        source.value = '';
        bkCloudId.value = 0;
      }
    },
  });

  const handleShowIpSelector = () => {
    isShowIpSelector.value = true;
  };

  const handleChange = (value: string) => {
    if (!value) {
      return;
    }
    fetchHostTopoInfo({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      filter_conditions: {
        bk_host_innerip: [value],
      },
    });
  };

  const handleSelectorChange = (selected: HostInfo[]) => {
    emits('batch-edit', selected);
  };

  watch(
    source,
    () => {
      if (!localValue.value && source.value) {
        localValue.value = `${bkCloudId.value}:${source.value}`;
        fetchHostTopoInfo({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          filter_conditions: {
            bk_host_innerip: [localValue.value],
          },
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
