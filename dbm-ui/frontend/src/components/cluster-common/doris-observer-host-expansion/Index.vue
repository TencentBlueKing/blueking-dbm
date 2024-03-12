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
  <div class="doris-observer-host-expansion">
    <div class="header-box">
      <span class="header-label">{{ data.label }}</span>
      <BkTag
        class="ml-8"
        theme="info">
        {{ data.tagText }}
      </BkTag>
    </div>
    <BkForm form-type="vertical">
      <BkFormItem>
        <ResourcePoolSelector
          v-if="ipSource === 'resource_pool'"
          :cloud-info="cloudInfo"
          :data="data"
          @change="handleResourcePoolChange" />
        <HostSelector
          v-else
          :cloud-info="cloudInfo"
          :data="data"
          :disable-host-method="disableHostMethod"
          @change="handleHoseSelectChange" />
      </BkFormItem>
    </BkForm>
  </div>
</template>

<script setup lang="tsx">
  import type { HostDetails } from '@services/types';

  import type { TExpansionNode } from '@components/cluster-common/host-expansion/Index.vue';

  import HostSelector from './components/HostSelector.vue';
  import ResourcePoolSelector from './components/ResourcePoolSelector.vue';

  interface Props {
    cloudInfo: {
      id: number;
      name: string;
    };
    data: TExpansionNode;
    ipSource: string;
    disableHostMethod?: (params: HostDetails) => string | boolean;
  }

  defineProps<Props>();

  const resourceSpec = defineModel<TExpansionNode['resourceSpec']>('resourceSpec', {
    required: true,
  });
  const hostList = defineModel<TExpansionNode['hostList']>('hostList', {
    required: true,
  });
  const expansionDisk = defineModel<TExpansionNode['expansionDisk']>('expansionDisk', {
    required: true,
  });

  const handleHoseSelectChange = (
    hostListValue: TExpansionNode['hostList'],
    expansionDiskValue: TExpansionNode['expansionDisk'],
  ) => {
    hostList.value = hostListValue;
    expansionDisk.value = expansionDiskValue;
    window.changeConfirm = true;
  };

  const handleResourcePoolChange = (
    resourceSpecValue: TExpansionNode['resourceSpec'],
    expansionDiskValue: TExpansionNode['expansionDisk'],
  ) => {
    resourceSpec.value = resourceSpecValue;
    expansionDisk.value = expansionDiskValue;
    window.changeConfirm = true;
  };
</script>

<style lang="less">
  .doris-observer-host-expansion {
    padding: 0 24px 24px;

    .bk-form-label {
      font-size: 12px;
      font-weight: bold;
      color: #63656e;
    }

    .header-box {
      padding: 10px 0;
      font-size: 14px;
      color: #313238;

      .header-box-label {
        font-weight: bold;
      }
    }
  }
</style>
