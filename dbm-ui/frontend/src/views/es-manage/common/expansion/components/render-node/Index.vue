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
    <div class="header">
      {{ data.label }}
    </div>
    <BkForm form-type="vertical">
      <BkFormItem :label="$t('期望容量')">
        <div class="target-content-box">
          <div class="content-label">
            {{ $t('扩容至') }}
          </div>
          <div class="content-value">
            <div>
              <BkInput
                clearable
                :min="data.totalDisk"
                :model-value="targetDisk > 0 ? targetDisk : undefined"
                :placeholder="$t('请输入')"
                style="width: 156px; margin-right: 8px;"
                type="number"
                @change="handleTargetDiskChange" />
              <span>GB</span>
              <template v-if="targetDisk">
                <span>
                  {{ $t(', 共扩容') }}
                </span>
                <span
                  class="strong-num"
                  style="color: #2dcb56;">
                  {{ targetDisk - data.totalDisk }}
                </span>
                <span>GB</span>
              </template>
            </div>
            <div class="content-tips">
              <span>
                {{ $t('当前容量') }}:
                <span class="strong-num">
                  {{ data.totalDisk }}
                </span>
                GB
              </span>
              <span style="margin-left: 65px;">
                <span>{{ $t('扩容后') }}:</span>
                <template v-if="data.targetDisk">
                  <span class="strong-num">{{ data.targetDisk }}</span>
                  GB
                </template>
                <span
                  v-else
                  style="padding-left: 4px;">
                  {{ t('请先设置期望容量') }}
                </span>
              </span>
            </div>
          </div>
        </div>
      </BkFormItem>
      <BkFormItem :label="$t('服务器')">
        <ResourcePoolSelector
          v-if="ipSource === 'resource_pool'"
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
  import { useI18n } from 'vue-i18n';

  import type { HostDetails } from '@services/types/ip';

  import type { TNodeInfo } from '../../Index.vue';

  import HostSelector from './components/HostSelector.vue';
  import ResourcePoolSelector from './components/ResourcePoolSelector.vue';

  interface Props {
    cloudInfo: {
      id: number,
      name: string
    },
    data: TNodeInfo,
    ipSource: string,
    disableHostMethod?: (params: HostDetails) => string | boolean
  }

  defineProps<Props>();

  const targetDisk = defineModel<TNodeInfo['targetDisk']>('targetDisk', {
    required: true,
  });
  const resourceSpec = defineModel<TNodeInfo['resourceSpec']>('resourceSpec', {
    required: true,
  });
  const hostList = defineModel<TNodeInfo['hostList']>('hostList', {
    required: true,
  });
  const expansionDisk = defineModel<TNodeInfo['expansionDisk']>('expansionDisk', {
    required: true,
  });

  const { t } = useI18n();

  const handleTargetDiskChange = (value: TNodeInfo['targetDisk']) => {
    targetDisk.value = ~~value;
  };

  const handleHoseSelectChange = (
    hostListValue: TNodeInfo['hostList'],
    expansionDiskValue: TNodeInfo['expansionDisk'],
  ) => {
    hostList.value = hostListValue;
    expansionDisk.value = expansionDiskValue;
  };

  const handleResourcePoolChange = (
    resourceSpecValue: TNodeInfo['resourceSpec'],
    expansionDiskValue: TNodeInfo['expansionDisk'],
  ) => {
    resourceSpec.value = resourceSpecValue;
    expansionDisk.value = expansionDiskValue;
  };
  </script>
  <style lang="less">
    .es-cluster-expansion-node-box {
      padding: 0 24px 24px;

      .bk-form-label {
        font-size: 12px;
        font-weight: bold;
        color: #63656e;
      }

      .strong-num{
        padding: 0 4px;
        font-weight: bold;
      }

      .header {
        padding: 10px 0;
        font-size: 14px;
        font-weight: bold;
        color: #313238;
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
