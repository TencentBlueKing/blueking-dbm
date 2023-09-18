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
  <BkLoading
    class="pulsar-cluster-expansion-box"
    :loading="isLoading">
    <BkAlert
      class="mb16"
      theme="warning"
      :title="$t('Bookkeeper，Broker 至少扩容一种类型')" />
    <div class="wrapper">
      <NodeList
        v-model="nodeType"
        :node-info="nodeInfoMap" />
      <div class="node-panel">
        <RenderNode
          v-if="!isLoading"
          :key="nodeType"
          :cloud-info="{
            id: data.bk_cloud_id,
            name: data.bk_cloud_name
          }"
          :data="nodeInfoMap[nodeType]"
          :disable-host-method="disableHostMethod"
          @change="handleNodeHostChange"
          @target-disk-change="handleTargetDiskChange" />
      </div>
    </div>
  </BkLoading>
</template>
<script lang="ts">
  export interface TNodeInfo {
    label: string,
    checkStatus: string,
    originalHostList: HostDetails[],
    hostList?: HostDetails[],
    totalDisk: number,
    targetDisk: number,
    expansionDisk: number,
  }
</script>
<script setup lang="ts">
  import { InfoBox } from 'bkui-vue';
  import {
    reactive,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getHostDetails } from '@services/ip';
  import type PulsarModel from '@services/model/pulsar/pulsar';
  import { createTicket } from '@services/ticket';
  import type { HostDetails } from '@services/types/ip';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { messageError } from '@utils';

  import NodeList from './components/NodeList.vue';
  import RenderNode from './components/RenderNode.vue';

  interface Props {
    data: PulsarModel,
  }

  interface Emits {
    (e: 'change'): void
  }

  interface Exposes {
    submit: () => Promise<any>
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const makeMapByHostId = (hostList: Array<HostDetails> = []) => hostList.reduce((result, item) => ({
    ...result,
    [item.host_id]: true,
  }), {} as Record<number, boolean>);

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const bizId = globalBizsStore.currentBizId;

  const nodeInfoMap = reactive<Record<string, TNodeInfo>>({
    broker: {
      label: 'Broker',
      checkStatus: '',
      originalHostList: [],
      hostList: undefined,
      // 当前主机的总容量
      totalDisk: 0,
      // 扩容目标容量
      targetDisk: 0,
      // 实际选中的扩容主机容量
      expansionDisk: 0,
    },
    bookkeeper: {
      label: 'Bookkeeper',
      checkStatus: '',
      originalHostList: [],
      hostList: undefined,
      totalDisk: 0,
      targetDisk: 0,
      expansionDisk: 0,
    },
  });

  const isLoading = ref(false);
  const nodeType = ref('bookkeeper');

  // 获取主机详情
  const fetchHostDetail = () => {
    const bookkeeperHostIdMap = props.data.pulsar_bookkeeper.reduce((result, item) => ({
      ...result,
      [item.bk_host_id]: true,
    }), {} as Record<number, boolean>);
    const brokerHostIdMap = props.data.pulsar_broker.reduce((result, item) => ({
      ...result,
      [item.bk_host_id]: true,
    }), {} as Record<number, boolean>);

    const hostIdList = [
      ...props.data.pulsar_bookkeeper,
      ...props.data.pulsar_broker,
    ].map(item => ({
      host_id: item.bk_host_id,
      meta: {
        bk_biz_id: item.bk_biz_id,
        scope_id: item.bk_biz_id,
        scope_type: 'biz',
      },
    }));

    isLoading.value = true;
    getHostDetails({
      host_list: hostIdList,
      scope_list: [{
        scope_id: bizId,
        scope_type: 'biz',
      }],
    }).then((data) => {
      const bookkeeperOriginalHostList: HostDetails[] = [];
      const brokerOriginalHostList: HostDetails[] = [];

      let bookkeeperDiskTotal = 0;
      let brokerDiskTotal = 0;

      data.forEach((hostItem) => {
        if (bookkeeperHostIdMap[hostItem.host_id]) {
          bookkeeperDiskTotal += ~~Number(hostItem.bk_disk);
          bookkeeperOriginalHostList.push(hostItem);
        }
        if (brokerHostIdMap[hostItem.host_id]) {
          brokerDiskTotal += ~~Number(hostItem.bk_disk);
          brokerOriginalHostList.push(hostItem);
        }
      });

      nodeInfoMap.bookkeeper.totalDisk = bookkeeperDiskTotal;
      nodeInfoMap.bookkeeper.originalHostList = bookkeeperOriginalHostList;

      nodeInfoMap.broker.totalDisk = brokerDiskTotal;
      nodeInfoMap.broker.originalHostList = brokerOriginalHostList;
    })
      .finally(() => {
        isLoading.value = false;
      });
  };

  fetchHostDetail();

  const disableHostMethod = (hostData: HostDetails) => {
    const bookkeeperDisableHostMethod = (hostData: HostDetails) => {
      const brokerHostIdMap = makeMapByHostId(nodeInfoMap.broker.hostList);
      if (brokerHostIdMap[hostData.host_id]) {
        return t('主机已被xx节点使用', ['Broker']);
      }
      return false;
    };
    const brokerDisableHostMethod = (hostData: HostDetails) => {
      const bookkeeperHostIdMap = makeMapByHostId(nodeInfoMap.bookkeeper.hostList);
      if (bookkeeperHostIdMap[hostData.host_id]) {
        return t('主机已被xx节点使用', ['Bookkeeper']);
      }
      return false;
    };

    if (nodeType.value === 'bookkeeper') {
      return bookkeeperDisableHostMethod(hostData);
    }
    if (nodeType.value === 'broker') {
      return brokerDisableHostMethod(hostData);
    }

    return false;
  };

  const handleTargetDiskChange = (value: number) => {
    nodeInfoMap[nodeType.value].targetDisk = value;
  };

  const handleNodeHostChange = (hostList: HostDetails[]) => {
    const expansionDisk = hostList.reduce((result, hostItem) => result + ~~Number(hostItem.bk_disk), 0);
    nodeInfoMap[nodeType.value].hostList = hostList;
    nodeInfoMap[nodeType.value].expansionDisk = expansionDisk;
  };

  defineExpose<Exposes>({
    submit() {
      const isEmpty = (hostList: undefined | HostDetails[]) => !hostList || hostList.length < 1;

      return new Promise((resolve, reject) => {
        if (isEmpty(nodeInfoMap.broker.hostList)
          && isEmpty(nodeInfoMap.bookkeeper.hostList)) {
          // 设置 hostList 为 [] 触发校验标记
          Object.values(nodeInfoMap).forEach((nodeInfo) => {
            if (nodeInfo.targetDisk > 0 && !nodeInfo.hostList) {
              // eslint-disable-next-line no-param-reassign
              nodeInfo.hostList = [];
            }
          });
          messageError(t('Bookkeeper_Broker 至少扩容一种类型'));
          return reject();
        }

        InfoBox({
          title: t('确认扩容【name】集群', { name: props.data.cluster_name }),
          subTitle: '',
          confirmText: t('确认'),
          cancelText: t('取消'),
          headerAlign: 'center',
          contentAlign: 'center',
          footerAlign: 'center',
          onClosed: () => reject(),
          onConfirm: () => {
            const fomatHost = (hostList: HostDetails[] = []) => hostList.map(hostItem => ({
              ip: hostItem.ip,
              bk_cloud_id: hostItem.cloud_id,
              bk_host_id: hostItem.host_id,
              bk_biz_id: hostItem.meta.bk_biz_id,
            }));

            createTicket({
              bk_biz_id: bizId,
              ticket_type: 'PULSAR_SCALE_UP',
              details: {
                ip_source: 'manual_input',
                cluster_id: props.data.id,
                nodes: {
                  broker: fomatHost(nodeInfoMap.broker.hostList),
                  bookkeeper: fomatHost(nodeInfoMap.bookkeeper.hostList),
                },
              },
            }).then((data) => {
              ticketMessage(data.id);
              resolve('success');
              emits('change');
            })
              .catch(() => {
                reject();
              });
          },
        });
      });
    },
  });
</script>
<style lang="less">
  .pulsar-cluster-expansion-box {
    padding: 18px 43px 18px 37px;
    font-size: 12px;
    line-height: 20px;
    color: #63656e;
    background: #f5f7fa;

    .wrapper {
      display: flex;
      background: #fff;
      border-radius: 2px;
      box-shadow: 0 2px 4px 0 #1919290d;

      .node-panel {
        flex: 1;
      }
    }

    .item-label {
      margin-top: 24px;
      margin-bottom: 6px;
      font-weight: bold;
      line-height: 20px;
      color: #313238;
    }
  }
</style>
