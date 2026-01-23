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
    :label="t('源实例')"
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
      v-model="source"
      :placeholder="t('请输入IP:Port或从表头批量选择')" />
  </EditableColumn>
  <InstanceSelector
    v-model="selectedInstances"
    v-model:is-show="isShowIpSelector"
    :cluster-types="[ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE]"
    repeatable
    @change="handleSelectorChange" />
  <EditableColumn
    field="cluster_domain"
    :label="t('所属集群')"
    :loading="loading"
    :min-width="250"
    readonly
    required>
    <EditableBlock
      v-model="clusterDomain"
      :placeholder="t('输入源实例后自动生成')" />
  </EditableColumn>
</template>
<script lang="ts" setup>
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaInstanceModel from '@services/model/mysql/tendbha-instance';
  import { checkInstance } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipPort } from '@common/regex';

  import InstanceSelector from '@components/instance-selector-new/Index.vue';

  type Emits = (e: 'batch-edit', list: TendbhaInstanceModel[]) => void;

  const emits = defineEmits<Emits>();

  const bkCloudId = defineModel<number>('bkCloudId', {
    required: true,
  });

  const source = defineModel<string>('source', {
    required: true,
  });

  const clusterDomain = defineModel<string>('clusterDomain', {
    required: true,
  });

  const { t } = useI18n();

  const bkHostId = ref(0);
  const isShowIpSelector = ref(false);
  const selectedInstances = shallowRef({
    [ClusterTypes.TENDBHA]: [] as TendbhaInstanceModel[],
    [ClusterTypes.TENDBSINGLE]: [] as TendbhaInstanceModel[],
  });

  const rules = [
    {
      message: t('实例格式有误，请输入 IP:Port'),
      trigger: 'change',
      validator: (value: string) => !value || ipPort.test(value),
    },
    {
      message: t('源实例不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(bkHostId.value),
    },
  ];

  const { loading, run: queryInstance } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      const [item] = data;
      if (item) {
        bkCloudId.value = item.bk_cloud_id;
        bkHostId.value = item.bk_host_id;
        source.value = item.instance_address;
        clusterDomain.value = item.master_domain;
      } else {
        bkCloudId.value = 0;
        bkHostId.value = 0;
        source.value = '';
        clusterDomain.value = '';
      }
    },
  });

  const handleShowIpSelector = () => {
    isShowIpSelector.value = true;
  };

  const handleSelectorChange = (selected: UnwrapRef<typeof selectedInstances>) => {
    emits('batch-edit', Object.values(selected).flat());
  };

  watch(
    source,
    () => {
      if (!bkHostId.value && source.value) {
        queryInstance({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: [ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE],
          db_type: DBTypes.MYSQL,
          instance_addresses: [source.value],
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
