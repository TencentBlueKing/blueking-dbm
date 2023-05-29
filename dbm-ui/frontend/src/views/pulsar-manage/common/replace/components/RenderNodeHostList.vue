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
  <div class="puslar-replace-render-host-list">
    <table class="ip-table">
      <thead>
        <tr>
          <th>
            <span>{{ t('被替换的节点 IP') }}</span>
            <I18nT
              keypath="(共n台_磁盘容量nG)"
              tag="span">
              <span style="padding: 0 4px;">
                {{ nodeList.length }}
              </span>
              <span style="padding: 0 4px;">
                {{ nodeDiskTotal }}
              </span>
            </I18nT>
          </th>
          <th>
            <span>{{ t('新节点 IP') }}</span>
            <span>(</span>
            <span>
              需{{ nodeList.length }}台
            </span>
            <span
              v-if="hostList.length > 0"
              :class="{ 'is-error': isError }">
              <span>
                ，已选{{ hostList.length }}台
              </span>
              <span v-if="nodeList.length !== hostList.length">
                ，
                {{ nodeList.length > hostList.length ? '少' : '多' }}
                {{ Math.abs(nodeList.length - hostList.length) }}
                台
              </span>
              <span>
                ，共{{ localHostDisk }}G
              </span>
            </span>
            <span>)</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>
            <div class="original-ip-box">
              <div
                v-for="nodeItem in nodeList"
                :key="nodeItem.bk_host_id"
                class="ip-tag">
                <span>{{ nodeItem.ip }}</span>
                <DbIcon
                  class="remove-btn"
                  type="close"
                  @click="handleRemoveNode(nodeItem)" />
              </div>
            </div>
          </td>
          <td>
            <div
              v-if="hostList.length > 0"
              class="new-ip-box">
              <div
                v-for="hostItem in hostList"
                :key="hostItem.host_id"
                class="ip-tag">
                <span>{{ hostItem.ip }}</span>
                <DbIcon
                  class="remove-btn"
                  type="close"
                  @click="handleRemoveHost(hostItem)" />
              </div>
              <div
                class="ip-tag ip-edit-btn"
                @click="handleShowIpSelector">
                <DbIcon type="edit" />
              </div>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
    <div
      v-show="isEmpty"
      class="add-new-box"
      :class="{
        'is-empty': isEmpty
      }">
      <IpSelector
        v-model:show-dialog="isShowIpSelector"
        :biz-id="currentBizId"
        :cloud-info="cloudInfo"
        :disable-dialog-submit-method="disableDialogSubmitMethod"
        :disable-host-method="disableHostMethod"
        :show-view="false"
        @change="handleHostChange">
        <template #submitTips="{ hostList: resultHostList }">
          <I18nT
            keypath="需n台_已选n台"
            style="font-size: 14px; color: #63656e;"
            tag="span">
            <span style="padding: 0 4px; font-weight: bold; color: #2dcb56;">
              {{ nodeList.length }}
            </span>
            <span style="padding: 0 4px; font-weight: bold; color: #3a84ff;">
              {{ resultHostList.length }}
            </span>
          </I18nT>
        </template>
      </IpSelector>
    </div>
  </div>
</template>
<script setup lang="tsx">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type PulsarNodeModel from '@services/model/pulsar/pulsar-node';
  import type { HostDetails } from '@services/types/ip';

  import { useGlobalBizs } from '@stores';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  interface Props {
    nodeList: PulsarNodeModel[],
    hostList: HostDetails[],
    disableHostMethod: (params: HostDetails) => string | boolean
  }

  interface Emits {
    (e: 'update:nodeList', value: Props['nodeList']): void,
    (e: 'update:hostList', value: Props['hostList']): void,
    (e: 'removeNode', bkHostId: number): void
  }

  interface Ivalue {
    bk_host_id: number,
    ip: string,
    bk_cloud_id: number,
  }

  interface Exposes {
    getValue: () => {
      old_nodes: Ivalue[],
      new_nodes: Ivalue[]
    }
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const isShowIpSelector = ref(false);

  const isEmpty = computed(() => props.hostList.length < 1);
  const nodeDiskTotal = computed(() => props.nodeList
    .reduce((result, item) => result + item.disk, 0));
  const localHostDisk = computed(() => props.hostList
    .reduce((result, item) => result + ~~Number(item.bk_disk), 0));
  const cloudInfo = computed(() => {
    const [firstItem] = props.nodeList;
    if (firstItem) {
      return {
        id: firstItem.bk_cloud_id,
        name: firstItem.bk_cloud_name,
      };
    }
    return undefined;
  });

  const isError = computed(() => props.hostList.length > 0
    && props.hostList.length !== props.nodeList.length);

  const disableDialogSubmitMethod = (hostList: Array<any>) => (
    hostList.length === props.nodeList.length
      ? false
      : t('需n台', { n: props.nodeList.length })
  );

  const handleShowIpSelector = () => {
    isShowIpSelector.value = true;
  };

  // 添加新IP
  const handleHostChange = (hostList: Array<HostDetails>) => {
    emits('update:hostList', hostList);
  };

  // 移除节点
  const handleRemoveNode = (node: PulsarNodeModel) => {
    const nodeList = props.nodeList.reduce((result, item) => {
      if (item.bk_host_id !== node.bk_host_id) {
        result.push(item);
      }
      return result;
    }, [] as Array<PulsarNodeModel>);
    emits('update:nodeList', nodeList);
    emits('removeNode', node.bk_host_id);
  };

  // 移除替换的主机
  const handleRemoveHost = (host: HostDetails) => {
    const hostList = props.hostList.reduce((result, item) => {
      if (item.host_id !== host.host_id) {
        result.push(item);
      }
      return result;
    }, [] as Array<HostDetails>);

    emits('update:hostList', hostList);
  };

  defineExpose<Exposes>({
    getValue() {
      return {
        old_nodes: props.nodeList.map(nodeItem => ({
          bk_host_id: nodeItem.bk_host_id,
          ip: nodeItem.ip,
          bk_cloud_id: nodeItem.bk_cloud_id,
        })),
        new_nodes: props.hostList.map(hostItem => ({
          bk_host_id: hostItem.host_id,
          ip: hostItem.ip,
          bk_cloud_id: hostItem.cloud_id,
        })),
      };
    },
  });
</script>
<style lang="less" scoped>
  .puslar-replace-render-host-list {
    position: relative;
    border-bottom: 1px solid #dcdee5;

    .ip-table {
      width: 100%;
      font-size: 12px;
      table-layout: fixed;

      th,
      td {
        width: 50%;
        height: 42px;
        padding: 0 16px;
        font-weight: normal;
        text-align: left;
        border: none;
      }

      th {
        color: #313238;
        background: #f0f1f5;

        &:nth-child(2) {
          background: #eaebf0;
        }
      }

      td {
        padding: 16px 24px;
        background: #fff;

        &:nth-child(2) {
          background: #fcfcfc;
        }
      }

      .is-error {
        color: #ea3636;
      }

      .original-ip-box,
      .new-ip-box {
        display: flex;
        flex-wrap: wrap;
      }

      .ip-tag {
        display: flex;
        height: 22px;
        padding: 0 6px;
        margin: 2px 4px;
        background: #f0f1f5;
        border-radius: 2px;
        align-items: center;
        justify-content: center;
      }

      .ip-edit-btn {
        cursor: pointer;

        &:hover{
          color: #3a84ff;
        }
      }

      .remove-btn {
        margin-left: 4px;
        font-size: 14px;
        cursor: pointer;
      }
    }

    .add-new-box {
      position: absolute;
      inset: 43px 0 1px 50%;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }
</style>
