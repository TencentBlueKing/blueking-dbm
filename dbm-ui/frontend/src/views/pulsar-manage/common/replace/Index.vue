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
  <div class="pulsar-cluster-replace-box">
    <template v-if="!isEmpty">
      <div
        v-if="nodeInfoMap.bookkeeper.nodeList.length > 0"
        class="item">
        <div class="item-label">
          Bookkeeper
        </div>
        <RenderNodeHostList
          ref="BookkeeperRef"
          v-model:hostList="nodeInfoMap.bookkeeper.hostList"
          v-model:nodeList="nodeInfoMap.bookkeeper.nodeList"
          :disable-host-method="bookkeeperDisableHostMethod"
          @remove-node="handleRemoveNode" />
      </div>
      <div
        v-if="nodeInfoMap.broker.nodeList.length > 0"
        class="item">
        <div class="item-label">
          Broker
        </div>
        <RenderNodeHostList
          ref="brokerRef"
          v-model:hostList="nodeInfoMap.broker.hostList"
          v-model:nodeList="nodeInfoMap.broker.nodeList"
          :disable-host-method="brokerDisableHostMethod"
          @remove-node="handleRemoveNode" />
      </div>
      <div
        v-if="nodeInfoMap.zookeeper.nodeList.length > 0"
        class="item">
        <div class="item-label">
          Zookeeper
        </div>
        <RenderNodeHostList
          ref="zookeeperRef"
          v-model:hostList="nodeInfoMap.zookeeper.hostList"
          v-model:nodeList="nodeInfoMap.zookeeper.nodeList"
          :disable-host-method="zookeeperDisableHostMethod"
          @remove-node="handleRemoveNode" />
      </div>
      <div class="item">
        <div class="item-label">
          {{ $t('备注') }}
        </div>
        <BkInput
          v-model="remark"
          :maxlength="100"
          :placeholder="$t('请提供更多有用信息申请信息_以获得更快审批')"
          type="textarea" />
      </div>
    </template>
    <div
      v-else
      class="node-empty">
      <BkException
        scene="part"
        type="empty">
        <template #description>
          <DbIcon type="attention" />
          <span>{{ t('请先返回列表选择要替换的节点 IP') }}</span>
        </template>
      </BkException>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { InfoBox } from 'bkui-vue';
  import {
    computed,
    reactive,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type PulsarModel from '@services/model/pulsar/pulsar';
  import type PulsarNodeModel from '@services/model/pulsar/pulsar-node';
  import { createTicket } from '@services/ticket';
  import type { HostDetails } from '@services/types/ip';

  import { useGlobalBizs } from '@stores';

  import { messageError  } from '@utils';

  import RenderNodeHostList from './components/RenderNodeHostList.vue';

  export interface TNodeInfo{
    nodeList: PulsarNodeModel[],
    hostList: HostDetails[],
  }

  interface Props {
    data: PulsarModel,
    nodeList: Array<PulsarNodeModel>
  }

  interface Emits {
    (e: 'removeNode', bkHostId: number): void
  }

  interface Exposes {
    submit: () => Promise<any>,
    cancel: () => Promise<any>,
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const makeMapByHostId = (hostList: Array<HostDetails>) =>  hostList.reduce((result, item) => ({
    ...result,
    [item.host_id]: true,
  }), {} as Record<number, boolean>);

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const BookkeeperRef = ref();
  const brokerRef = ref();
  const zookeeperRef = ref();
  const remark = ref('');

  const nodeInfoMap = reactive<Record<string, TNodeInfo>>({
    bookkeeper: {
      nodeList: [],
      hostList: [],
    },
    broker: {
      nodeList: [],
      hostList: [],
    },
    zookeeper: {
      nodeList: [],
      hostList: [],
    },
  });

  const isEmpty = computed(() => {
    const {
      bookkeeper,
      broker,
      zookeeper,
    } = nodeInfoMap;
    return bookkeeper.nodeList.length < 1
      && broker.nodeList.length < 1
      && zookeeper.nodeList.length < 1;
  });

  watch(() => props.nodeList, () => {
    const bookkeeperList: Array<PulsarNodeModel> = [];
    const brokerList: Array<PulsarNodeModel> = [];
    const zookeeperList: Array<PulsarNodeModel> = [];

    props.nodeList.forEach((nodeItem) => {
      if (nodeItem.isBookkeeper) {
        bookkeeperList.push(nodeItem);
      } else if (nodeItem.isBroker) {
        brokerList.push(nodeItem);
      } else if (nodeItem.isZookeeper) {
        zookeeperList.push(nodeItem);
      }
    });

    nodeInfoMap.bookkeeper.nodeList = bookkeeperList;
    nodeInfoMap.broker.nodeList = brokerList;
    nodeInfoMap.zookeeper.nodeList = zookeeperList;
  }, {
    immediate: true,
  });

  const bookkeeperDisableHostMethod = (hostData: HostDetails) => {
    const brokerHostIdMap = makeMapByHostId(nodeInfoMap.broker.hostList);
    if (brokerHostIdMap[hostData.host_id]) {
      return t('主机已被xx节点使用', ['Broker']);
    }
    const zookeeperHostIdMap = makeMapByHostId(nodeInfoMap.zookeeper.hostList);
    if (zookeeperHostIdMap[hostData.host_id]) {
      return t('主机已被xx节点使用', ['Zookeeper']);
    }
    return false;
  };
  const brokerDisableHostMethod = (hostData: HostDetails) => {
    const bookkeeperHostIdMap = makeMapByHostId(nodeInfoMap.bookkeeper.hostList);
    if (bookkeeperHostIdMap[hostData.host_id]) {
      return t('主机已被xx节点使用', ['Bookkeeper']);
    }
    const zookeeperHostIdMap = makeMapByHostId(nodeInfoMap.zookeeper.hostList);
    if (zookeeperHostIdMap[hostData.host_id]) {
      return t('主机已被xx节点使用', ['Zookeeper']);
    }
    return false;
  };
  const zookeeperDisableHostMethod = (hostData: HostDetails) => {
    const brokerHostIdMap = makeMapByHostId(nodeInfoMap.broker.hostList);
    if (brokerHostIdMap[hostData.host_id]) {
      return t('主机已被xx节点使用', ['Broker']);
    }
    const bookkeeperHostIdMap = makeMapByHostId(nodeInfoMap.bookkeeper.hostList);
    if (bookkeeperHostIdMap[hostData.host_id]) {
      return t('主机已被xx节点使用', ['Bookkeeper']);
    }
    return false;
  };

  const handleRemoveNode = (bkHostId: number) => {
    emits('removeNode', bkHostId);
  };

  defineExpose<Exposes>({
    submit() {
      return new Promise((resolve, reject) => {
        const bookkeeper = BookkeeperRef.value ? BookkeeperRef.value.getValue() : {};
        const broker = brokerRef.value ? brokerRef.value.getValue() : {};
        const zookeeper = zookeeperRef.value ? zookeeperRef.value.getValue() : {};

        if (bookkeeper.new_nodes?.length < 1
          && broker.new_nodes?.length < 1
          && zookeeper.new_nodes?.length < 1) {
          messageError(t('替换节点不能为空'));
          return reject();
        }
        InfoBox({
          title: t('确认替换【name】集群', { name: props.data.cluster_name }),
          subTitle: '',
          confirmText: t('确认'),
          cancelText: t('取消'),
          headerAlign: 'center',
          contentAlign: 'center',
          footerAlign: 'center',
          onClosed: () => reject(),
          onConfirm: () => {
            createTicket({
              ticket_type: 'PULSAR_REPLACE',
              bk_biz_id: currentBizId,
              details: {
                cluster_id: props.data.id,
                ip_source: 'manual_input',
                old_nodes: {
                  bookkeeper: bookkeeper.old_nodes,
                  broker: broker.old_nodes,
                  zookeeper: zookeeper.old_nodes,
                },
                new_nodes: {
                  bookkeeper: bookkeeper.new_nodes,
                  broker: broker.new_nodes,
                  zookeeper: zookeeper.new_nodes,
                },
              },
              remark: remark.value,
            })
              .then(() => {
                resolve('success');
              })
              .catch(() => {
                reject();
              });
          },
        });
      });
    },
    cancel() {
      return Promise.resolve();
    },
  });
</script>
<style lang="less">
  .pulsar-cluster-replace-box {
    padding: 18px 43px 18px 37px;
    font-size: 12px;
    line-height: 20px;
    color: #63656e;

    .item {
      & ~ .item {
        margin-top: 24px;
      }

      .item-label {
        margin-bottom: 6px;
        font-weight: bold;
        color: #313238;
      }
    }

    .node-empty {
      height: calc(100vh - 58px);
      padding-top: 168px;
    }
  }
</style>
