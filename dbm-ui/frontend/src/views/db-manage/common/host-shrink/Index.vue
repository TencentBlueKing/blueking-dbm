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
  <div class="big-data-cluster-shrink-node-box">
    <div class="header-box">
      <span class="header-label">{{ data.label }}</span>
      <BkTag
        class="ml-8"
        theme="info">
        {{ data.tagText }}
      </BkTag>
    </div>
    <BkAlert
      v-if="isDisabled"
      class="mb-16"
      theme="warning">
      <template #title>
        <I18nT keypath="当前仅剩n台 IP_无法缩容">
          <span>{{ data.originalNodeList.length }}</span>
        </I18nT>
      </template>
    </BkAlert>
    <BkForm form-type="vertical">
      <BkFormItem>
        <template #label>
          <span>{{ t('缩容的节点 IP') }}</span>
          <span style="font-weight: normal; color: #979ba5">
            {{ t('（默认从节点列表选取，如不满足，可以手动添加）') }}
          </span>
        </template>
        <div class="data-preview-table">
          <div class="data-preview-header">
            <I18nT keypath="共n台，共nG">
              <span
                class="number"
                style="color: #3a84ff">
                {{ nodeTableData.length }}
              </span>
              <span
                class="number"
                style="color: #2dcb56">
                {{ data.shrinkDisk }}
              </span>
            </I18nT>
            <BkButton
              size="small"
              style="margin-left: auto"
              @click="handleShowHostSelect">
              <DbIcon type="add" />
              {{ t('手动添加') }}
            </BkButton>
          </div>
          <BkTable
            v-if="nodeTableData.length > 0"
            :data="nodeTableData">
            <BkTableColumn
              field="ip"
              label="IP" />
            <BkTableColumn
              field="host_info"
              :label="t('状态')">
              <template #default="{ data: hostItem }: { data: TShrinkNode['hostList'][number] }">
                <HostAgentStatus :data="hostItem.alive || 0" />
              </template>
            </BkTableColumn>
            <BkTableColumn
              field="host_info.bk_disk"
              :label="t('磁盘G')">
              <template #default="{ data: hostItem }: { data: TShrinkNode['hostList'][number] }">
                {{ hostItem.bk_disk || '--' }}
              </template>
            </BkTableColumn>
            <BkTableColumn
              field=""
              fixed="right"
              :label="t('操作')"
              :width="120">
              <template #default="{ data: hostItem }: { data: TShrinkNode['hostList'][number] }">
                <BkButton
                  text
                  theme="primary"
                  @click="() => handleRemoveHost(hostItem)">
                  {{ t('删除') }}
                </BkButton>
              </template>
            </BkTableColumn>
          </BkTable>
        </div>
      </BkFormItem>
      <div
        v-if="nodeTableData.length"
        class="mt-16">
        <I18nT
          keypath="当前容量：nG"
          tag="span">
          <span style="font-weight: bolder">{{ data.totalDisk }}</span>
        </I18nT>
        ，
        <I18nT
          keypath="缩容后预估：nG"
          tag="span">
          <span style="font-weight: bolder">{{ estimateCapacity }}</span>
        </I18nT>
      </div>
    </BkForm>
    <SelectOriginalHost
      v-model:is-show="isShowHostDialog"
      :min-host="data.minHost"
      :model-value="data.hostList"
      :original-node-list="data.originalNodeList"
      @change="handleSelectChange" />
  </div>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import HostAgentStatus from '@components/host-agent-status/Index.vue';

  import SelectOriginalHost from './components/SelectOriginalHost.vue';

  export interface TShrinkNode {
    // 缩容后的主机列表
    hostList: {
      alive: number;
      bk_cloud_id: number;
      bk_disk: number;
      bk_host_id: number;
      ip: string;
    }[];
    // 节点显示名称
    label: string;
    // 改节点所需的最少主机数
    minHost: number;
    // 原始实例节点列表
    originalNodeList: {
      bk_cloud_id: number;
      bk_host_id: number;
      cpu: number;
      disk: number;
      ip: string;
      mem: number;
      node_count: number;
      role?: string;
      role_set?: string[];
      status: number;
    }[];
    // 缩容目标磁盘大小
    // targetDisk: number,
    // 选择节点后实际的缩容磁盘大小
    shrinkDisk: number;
    // 节点类型 tag 文本
    tagText: string;
    // 原始磁盘大小
    totalDisk: number;
  }

  export interface Props {
    data: TShrinkNode;
  }

  export interface Emits {
    (e: 'change', value: TShrinkNode['hostList']): void;
    (e: 'target-disk-change', value: TShrinkNode['totalDisk']): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const nodeTableData = shallowRef(props.data.hostList || []);
  const isShowHostDialog = ref(false);

  const isDisabled = computed(() => props.data.originalNodeList.length <= props.data.minHost);

  // 资源池预估容量
  const estimateCapacity = computed(() => {
    const { shrinkDisk, totalDisk } = props.data;
    return totalDisk - shrinkDisk;
  });

  const handleShowHostSelect = () => {
    isShowHostDialog.value = true;
  };

  // 添加节点
  const handleSelectChange = (originalNodeList: TShrinkNode['originalNodeList']) => {
    nodeTableData.value = originalNodeList.map((item) => ({
      alive: item.status,
      bk_cloud_id: item.bk_cloud_id,
      bk_disk: item.disk,
      bk_host_id: item.bk_host_id,
      ip: item.ip,
    }));
    window.changeConfirm = true;
    emits('change', [...nodeTableData.value]);
  };

  // 删除选择的节点
  const handleRemoveHost = (data: TShrinkNode['hostList'][0]) => {
    const hostList = nodeTableData.value.reduce(
      (result, item) => {
        if (item.bk_host_id !== data.bk_host_id) {
          result.push(item);
        }
        return result;
      },
      [] as TShrinkNode['hostList'],
    );

    nodeTableData.value = hostList;
    window.changeConfirm = true;
    emits('change', hostList);
  };
</script>
<style lang="less">
  .big-data-cluster-shrink-node-box {
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
    }
  }
</style>
