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
  <div class="bi-data-cluster-expansion-node-box">
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
  import type { HostInfo } from '@services/types';

  import HostSelector from './components/HostSelector.vue';
  import ResourcePoolSelector from './components/ResourcePoolSelector.vue';

  export interface TExpansionNode {
    // 集群节点展示名
    label: string;
    // 集群id
    clusterId: number;
    // 集群的节点类型
    role: string;
    // 初始主机
    originalHostList: {
      bk_host_id: number;
      host_info: {
        bk_disk: number;
      };
    }[];
    // 服务器来源
    ipSource: 'resource_pool' | 'manual_input';
    // 扩容主机
    hostList: HostInfo[];
    // 当前主机的总容量
    totalDisk: number;
    // 扩容目标容量
    // targetDisk: number;
    // 实际选中的扩容主机容量
    expansionDisk: number;
    // 资源池规格集群类型
    specClusterType: string;
    // 资源池规格集群类型
    specMachineType: string;
    // 扩容资源池
    resourceSpec: {
      spec_id: number;
      count: number;
    };
    // 节点类型 tag 文本
    tagText: string;
    // 是否显示台数
    showCount?: boolean;
  }

  interface Props {
    cloudInfo: {
      id: number;
      name: string;
    };
    data: TExpansionNode;
    ipSource: string;
    disableHostMethod?: (params: HostInfo) => string | boolean;
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
  .bi-data-cluster-expansion-node-box {
    padding: 0 24px 24px;

    .bk-form-label {
      font-size: 12px;
      font-weight: bold;
      color: #63656e;
    }

    .strong-num {
      padding: 0 4px;
      font-weight: bold;
    }

    .header-box {
      padding: 10px 0;
      font-size: 14px;
      color: #313238;

      .header-box-label {
        font-weight: bold;
      }
    }

    .target-content-box {
      display: flex;
      align-items: flex-start;

      .content-label {
        padding-right: 8px;
      }

      .content-value {
        flex: 1;
      }

      .content-tips {
        display: flex;
        height: 40px;
        padding: 0 16px;
        margin-top: 12px;
        background: #fafbfd;
        align-items: center;
      }
    }

    .data-preview-table {
      margin-top: 16px;

      .data-preview-header {
        display: flex;
        height: 42px;
        padding: 0 16px;
        background: #f0f1f5;
        align-items: center;
      }

      .bk-table {
        th {
          background: #f5f7fa;
        }
      }
    }
  }
</style>
