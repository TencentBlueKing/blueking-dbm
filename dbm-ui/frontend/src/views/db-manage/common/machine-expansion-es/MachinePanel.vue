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
  <div class="es-cluster-expansion-node-box">
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
          v-model:expansion-disk="expansionDisk"
          v-model:resource-spec="resourceSpec"
          :cloud-info="cloudInfo"
          :data="data" />
        <ResourceHostSelect
          v-else
          v-model:expansion-disk="expansionDisk"
          v-model:host-list="hostList"
          :data="data"
          :disable-host-method="disableHostMethod">
        </ResourceHostSelect>
      </BkFormItem>
    </BkForm>
  </div>
</template>
<script setup lang="tsx">
  import ResourceHostSelect from './components/ResourceHostSelect.vue';
  import ResourcePoolSelector from './components/ResourcePoolSelector.vue';
  import { type TExpansionNode } from './Index.vue';

  interface Props {
    cloudInfo: {
      id: number;
      name: string;
    };
    data: TExpansionNode;
    disableHostMethod?: (params: TExpansionNode['hostList'][number]) => string | boolean;
    ipSource: string;
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
</script>
<style lang="less">
  .es-cluster-expansion-node-box {
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
      width: 200px;
      padding: 10px 0;
      font-size: 14px;
      color: #313238;

      .header-label {
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
    }
  }
</style>
