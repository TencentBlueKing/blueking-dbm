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
  <div class="pulsar-cluster-expansion-node-box">
    <div class="header">
      {{ data.label }}
    </div>
    <BkForm form-type="vertical">
      <BkFormItem :label="$t('目标容量')">
        <div class="target-content-box">
          <div class="content-label">
            {{ $t('扩容至') }}
          </div>
          <div class="content-value">
            <div>
              <BkInput
                clearable
                :min="data.totalDisk"
                :model-value="`${localTargetDisk > 0 ? localTargetDisk : undefined}`"
                :placeholder="$t('请输入')"
                style="width: 156px; margin-right: 8px;"
                type="number"
                @change="handleTargetDiskChange" />
              <span>GB</span>
              <template v-if="localTargetDisk">
                <span>
                  {{ $t(', 共扩容') }}
                </span>
                <span
                  class="strong-num"
                  style="color: #2dcb56;">
                  {{ localTargetDisk - data.totalDisk }}
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
                <span v-else>
                  {{ t('请先设置目标容量') }}
                </span>
              </span>
            </div>
          </div>
        </div>
      </BkFormItem>
      <BkFormItem :label="$t('服务器')">
        <BkRadioGroup model-value="manual_input">
          <BkRadioButton
            v-bk-tooltips="$t('该功能暂未开放')"
            disabled
            label="auto"
            style="width: 160px;">
            {{ $t('资源池自动匹配') }}
          </BkRadioButton>
          <BkRadioButton
            checked
            label="manual_input"
            style="width: 160px;">
            {{ $t('手动选择') }}
          </BkRadioButton>
        </BkRadioGroup>
        <IpSelector
          :biz-id="bizId"
          class="mt-12"
          :cloud-info="cloudInfo"
          :disable-host-method="disableHostMethod"
          :disable-tips="localTargetDisk < 1 ? t('请先设置目标容量') : ''"
          :show-view="false"
          @change="handleHostChange">
          <template #submitTips="{ hostList }">
            <I18nT
              keypath="已选n台_共nGB(目标容量：nG)"
              style="font-size: 14px; color: #63656e;"
              tag="span">
              <span
                class="strong-num"
                style="color: #2dcb56;">
                {{ hostList.length }}
              </span>
              <span
                class="strong-num"
                style="color: #3a84ff;">
                {{ calcSelectHostDisk(hostList) }}
              </span>
              <span
                class="strong-num"
                style="color: #63656e;">
                {{ localTargetDisk - data.totalDisk }}
              </span>
            </I18nT>
          </template>
        </IpSelector>
        <div
          v-if="nodeTableData.length > 0"
          class="data-preview-table">
          <div class="data-preview-header">
            <div>
              <span>共</span>
              <span style="padding: 0 4px; font-weight: bold; color: #3a84ff;">
                {{ nodeTableData.length }}
              </span>
              <span>台，共</span>
              <span style="padding: 0 4px; font-weight: bold; color: #2dcb56;">
                {{ props.data.expansionDisk }}
              </span>
              <span>G</span>
            </div>
            <div
              v-if="!isTargetMatchReal"
              style="margin-left: 8px; color: #ff9c01;">
              <DbIcon type="exclamation-fill" />
              {{ t('与目标容量不匹配') }}
            </div>
          </div>
          <BkTable
            :columns="tableColumns"
            :data="nodeTableData" />
        </div>
      </BkFormItem>
    </BkForm>
  </div>
</template>
<script setup lang="tsx">
  import {
    computed,
    ref,
    shallowRef  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { HostDetails } from '@services/types/ip';

  import { useGlobalBizs } from '@stores';

  import DbStatus from '@components/db-status/index.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import type { TNodeInfo } from '../Index.vue';

  interface Props {
    cloudInfo: {
      id: number,
      name: string
    },
    data: TNodeInfo,
    disableHostMethod: (params: HostDetails) => string | boolean
  }

  interface Emits {
    (e: 'change', value: HostDetails[]): void,
    (e: 'targetDiskChange', value: number): void,
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const bizId = globalBizsStore.currentBizId;

  const localTargetDisk = ref(props.data.targetDisk);
  const nodeTableData = shallowRef<HostDetails[]>(props.data.hostList || []);

  // 目标容量和实际容量误差允许 1GB
  const isTargetMatchReal = computed(() => {
    const {
      totalDisk,
      targetDisk,
      expansionDisk,
    } = props.data;

    const realTargetDisk = totalDisk + expansionDisk;
    return realTargetDisk - targetDisk <= 1 && realTargetDisk - targetDisk >= -1;
  });

  const tableColumns = [
    {
      label: t('节点 IP'),
      field: 'ip',
      render: ({ data }: {data:HostDetails}) => data.ip || '--',
    },
    {
      label: t('Agent状态'),
      field: 'alive',
      render: ({ data }: { data:HostDetails }) => {
        const info = data.alive === 1 ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      label: t('磁盘_GB'),
      field: 'bk_disk',
      render: ({ data }: {data:HostDetails}) => data.bk_disk || '--',
    },
    {
      label: t('操作'),
      width: 100,
      render: ({ data }: {data:HostDetails}) => (
        <bk-button
          text
          theme="primary"
          onClick={() => handleRemoveHost(data)}>
          删除
        </bk-button>
      ),
    },
  ];

  const calcSelectHostDisk = (hostList: HostDetails[]) => hostList
    .reduce((result, hostItem) => result + ~~Number(hostItem.bk_disk), 0);

  const handleTargetDiskChange = (value: number) => {
    localTargetDisk.value = value;
    emits('targetDiskChange', value);
  };

  const handleHostChange = (hostList: Array<HostDetails>) => {
    nodeTableData.value = hostList;
    emits('change', hostList);
  };

  const handleRemoveHost = (data: HostDetails) => {
    const hostList = nodeTableData.value.reduce((result, item) => {
      if (item.host_id !== data.host_id) {
        result.push(item);
      }
      return result;
    }, [] as HostDetails[]);
    nodeTableData.value = hostList;
    emits('change', hostList);
  };
</script>
<style lang="less">
  .pulsar-cluster-expansion-node-box {
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
