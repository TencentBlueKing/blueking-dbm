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
  <div class="pulsar-cluster-shrink-node-box">
    <div class="header">
      {{ data.label }}
    </div>
    <BkAlert
      v-if="isDisabled"
      class="mb16"
      theme="warning">
      <template #title>
        {{ t('当前仅剩n台 IP_无法缩容', { n: data.minHost}) }}
      </template>
    </BkAlert>
    <BkForm form-type="vertical">
      <BkFormItem :label="$t('目标容量')">
        <div class="target-content-box">
          <div class="content-label">
            {{ $t('缩容至') }}
          </div>
          <div class="content-value">
            <div>
              <BkInput
                clearable
                :disabled="isDisabled"
                :max="data.totalDisk"
                :min="1"
                :model-value="localTargetDisk > 0 ? localTargetDisk : undefined"
                :placeholder="$t('请输入')"
                size="small"
                style="width: 156px; margin-right: 8px;"
                type="number"
                @change="handleTargetDiskChange" />
              <span>GB</span>
              <template v-if="localTargetDisk > 0">
                <span>
                  , {{ $t('共缩容') }}
                </span>
                <span
                  class="strong-num"
                  style="color: #2dcb56;">
                  {{ data.totalDisk - localTargetDisk }}
                </span>
                <span>GB</span>
              </template>
            </div>
            <div class="content-tips">
              <span>
                {{ $t('当前容量') }}:
                <span class="strong-num">{{ data.totalDisk }}</span>
                GB
              </span>
              <span style="margin-left: 65px;">
                <span>{{ $t('缩容后') }}:</span>
                <span v-if="data.targetDisk">
                  <span class="strong-num">{{ localTargetDisk }}</span>
                  GB
                </span>
                <span v-else>
                  {{ t('请先设置目标容量') }}
                </span>
              </span>
            </div>
          </div>
        </div>
      </BkFormItem>
      <BkFormItem>
        <template #label>
          <span>{{ t('缩容的节点 IP') }}</span>
          <span style="font-weight: normal; color: #979ba5;">
            {{ t('（默认从节点列表选取，如不满足，可以手动添加）') }}
          </span>
        </template>
        <div class="data-preview-table">
          <div class="data-preview-header">
            <div v-if="data.targetDisk">
              <span>共</span>
              <span style="padding: 0 4px; font-weight: bold; color: #3a84ff;">
                {{ nodeTableData.length }}
              </span>
              <span>台，共</span>
              <span style="padding: 0 4px; font-weight: bold; color: #2dcb56;">
                {{ data.shrinkDisk }}
              </span>
              <span>G</span>
            </div>
            <div v-else>
              {{ t('请先设置目标容量') }}
            </div>
            <div
              v-if="!isTargetMatchReal"
              style="margin-left: 8px; color: #ff9c01;">
              <DbIcon type="exclamation-fill" />
              {{ t('与目标容量不匹配') }}
            </div>
            <BkButton
              v-if="data.targetDisk"
              size="small"
              style="margin-left: auto;"
              @click="handleShowHostSelect">
              <DbIcon type="add" />
              {{ t('手动添加') }}
            </BkButton>
          </div>
          <BkTable
            v-if="nodeTableData.length > 0"
            :columns="tableColumns"
            :data="nodeTableData" />
        </div>
      </BkFormItem>
    </BkForm>
    <RenderOriginalHostList
      v-model:is-show="isShowHostDialog"
      :cluster-id="clusterId"
      :model-value="data.nodeList ? data.nodeList : []"
      :original-node-list="data.originalNodeList"
      :target-disk="data.totalDisk - localTargetDisk"
      @change="handleSelectChange" />
  </div>
</template>
<script setup lang="tsx">
  import {
    computed,
    ref,
    shallowRef,
    watch  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type PulsarNodeModel from '@services/model/pulsar/pulsar-node';

  import RenderHostStatus from '@components/render-host-status/Index.vue';

  import type { TNodeInfo } from '../Index.vue';

  import RenderOriginalHostList from './RenderOriginalHostList.vue';

  interface Props {
    data: TNodeInfo,
    clusterId: number,
  }

  interface Emits {
    (e: 'change', value: PulsarNodeModel[]): void,
    (e: 'target-disk-change', value: number): void,
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const localTargetDisk = ref(props.data.targetDisk);
  const nodeTableData = shallowRef<PulsarNodeModel[]>(props.data.nodeList || []);
  const isShowHostDialog = ref(false);

  const isDisabled = computed(() => props.data.originalNodeList.length <= props.data.minHost);

  // 目标容量和实际容量误差允许 1GB
  const isTargetMatchReal = computed(() => {
    const {
      totalDisk,
      targetDisk,
      shrinkDisk,
    } = props.data;

    const realTargetDisk = totalDisk - shrinkDisk;
    return realTargetDisk - targetDisk <= 1 && realTargetDisk - targetDisk >= -1;
  });

  const tableColumns = [
    {
      label: t('节点 IP'),
      field: 'ip',
      render: ({ data }: {data:PulsarNodeModel}) => data.ip || '--',
    },
    {
      label: t('Agent状态'),
      field: 'alive',
      render: ({ data }: { data:PulsarNodeModel }) => (
        <RenderHostStatus data={data.status} />
      ),
    },
    {
      label: t('磁盘_GB'),
      field: 'disk',
      render: ({ data }: {data:PulsarNodeModel}) => data.disk || '--',
    },
    {
      label: t('操作'),
      width: 100,
      render: ({ data }: {data:PulsarNodeModel}) => (
        <bk-button
          text
          theme="primary"
          onClick={() => handleRemoveHost(data)}>
          {t('删除')}
        </bk-button>
      ),
    },
  ];

  // 调整目标容量时需要自动匹配
  watch(localTargetDisk, () => {
    const shrinkDisk = props.data.totalDisk - localTargetDisk.value;
    let calcDisk = 0;
    const nodeList: PulsarNodeModel[] = [];
    props.data.originalNodeList.forEach((hostItem) => {
      // 不能全部缩容掉，需要留一台
      if (nodeList.length >=  props.data.originalNodeList.length - props.data.minHost) {
        return;
      }
      if (calcDisk >= shrinkDisk) {
        return;
      }
      nodeList.push(hostItem);
      calcDisk += hostItem.disk;
    });

    nodeTableData.value = nodeList.slice(0, props.data.minHost);

    emits('change', nodeList);
  });

  // 更新目标容量
  const handleTargetDiskChange = (value: number) => {
    localTargetDisk.value = value;
    emits('target-disk-change', value);
  };

  const handleShowHostSelect = () => {
    isShowHostDialog.value = true;
  };

  // 添加节点
  const handleSelectChange = (nodeList: PulsarNodeModel[]) => {
    nodeTableData.value = nodeList;
    emits('change', nodeList);
  };

  // 删除选择的节点
  const handleRemoveHost = (data: PulsarNodeModel) => {
    const nodeList = nodeTableData.value.reduce((result, item) => {
      if (item.bk_host_id !== data.bk_host_id) {
        result.push(item);
      }
      return result;
    }, [] as PulsarNodeModel[]);

    nodeTableData.value = nodeList;
    emits('change', nodeList);
  };
</script>
<style lang="less">
  .pulsar-cluster-shrink-node-box {
    padding: 0 24px 24px;

    .bk-form-label {
      font-size: 12px;
      font-weight: bold;
      color: #63656e;
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

    .strong-num {
      padding: 0 4px;
      font-weight: bold;
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
