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
      <BkRadioGroup
        v-model="ipSource"
        class="ip-srouce-box">
        <BkRadioButton label="resource_pool">
          {{ $t('资源池自动匹配') }}
        </BkRadioButton>
        <BkRadioButton label="manual_input">
          {{ $t('手动选择') }}
        </BkRadioButton>
      </BkRadioGroup>
      <div
        v-show="nodeInfoMap.bookkeeper.nodeList.length > 0"
        class="item">
        <div class="item-label">
          Bookkeeper
        </div>
        <HostReplace
          ref="BookkeeperRef"
          v-model:hostList="nodeInfoMap.bookkeeper.hostList"
          v-model:nodeList="nodeInfoMap.bookkeeper.nodeList"
          v-model:resourceSpec="nodeInfoMap.bookkeeper.resourceSpec"
          :data="nodeInfoMap.bookkeeper"
          :disable-host-method="bookkeeperDisableHostMethod"
          :ip-source="ipSource"
          @remove-node="handleRemoveNode" />
      </div>
      <div
        v-show="nodeInfoMap.broker.nodeList.length > 0"
        class="item">
        <div class="item-label">
          Broker
        </div>
        <HostReplace
          ref="brokerRef"
          v-model:hostList="nodeInfoMap.broker.hostList"
          v-model:nodeList="nodeInfoMap.broker.nodeList"
          v-model:resourceSpec="nodeInfoMap.broker.resourceSpec"
          :data="nodeInfoMap.broker"
          :disable-host-method="brokerDisableHostMethod"
          :ip-source="ipSource"
          @remove-node="handleRemoveNode" />
      </div>
      <div
        v-show="nodeInfoMap.zookeeper.nodeList.length > 0"
        class="item">
        <div class="item-label">
          Zookeeper
        </div>
        <HostReplace
          ref="zookeeperRef"
          v-model:hostList="nodeInfoMap.zookeeper.hostList"
          v-model:nodeList="nodeInfoMap.zookeeper.nodeList"
          v-model:resourceSpec="nodeInfoMap.zookeeper.resourceSpec"
          :data="nodeInfoMap.zookeeper"
          :disable-host-method="zookeeperDisableHostMethod"
          :ip-source="ipSource"
          @remove-node="handleRemoveNode" />
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

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import HostReplace, {
    type TReplaceNode,
  } from '@components/cluster-common/host-replace/Index.vue';

  import { messageError  } from '@utils';

  type TNodeInfo = TReplaceNode<PulsarNodeModel>

  interface Props {
    data: PulsarModel,
    nodeList: TNodeInfo['nodeList']
  }

  interface Emits {
    (e: 'change'): void,
    (e: 'removeNode', bkHostId: number): void
  }

  interface Exposes {
    submit: () => Promise<any>,
    cancel: () => Promise<any>,
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const makeMapByHostId = (hostList: TNodeInfo['hostList']) =>  hostList.reduce((result, item) => ({
    ...result,
    [item.host_id]: true,
  }), {} as Record<number, boolean>);

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const BookkeeperRef = ref();
  const brokerRef = ref();
  const zookeeperRef = ref();

  const ipSource = ref('resource_pool');
  const nodeInfoMap = reactive<Record<string, TNodeInfo>>({
    bookkeeper: {
      clusterId: props.data.id,
      role: 'pulsar_bookkeeper',
      nodeList: [],
      hostList: [],
      specClusterType: ClusterTypes.PULSAE,
      specMachineType: 'pulsar_bookkeeper',
      resourceSpec: {
        spec_id: 0,
        count: 0,
      },
    },
    broker: {
      clusterId: props.data.id,
      role: 'pulsar_broker',
      nodeList: [],
      hostList: [],
      specClusterType: ClusterTypes.PULSAE,
      specMachineType: 'pulsar_broker',
      resourceSpec: {
        spec_id: 0,
        count: 0,
      },
    },
    zookeeper: {
      clusterId: props.data.id,
      role: 'pulsar_zookeeper',
      nodeList: [],
      hostList: [],
      specClusterType: ClusterTypes.PULSAE,
      specMachineType: 'pulsar_zookeeper',
      resourceSpec: {
        spec_id: 0,
        count: 3,
      },
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
    const bookkeeperList: TNodeInfo['nodeList'] = [];
    const brokerList: TNodeInfo['nodeList'] = [];
    const zookeeperList: TNodeInfo['nodeList'] = [];

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

  // 节点主机互斥
  const bookkeeperDisableHostMethod = (hostData: TNodeInfo['hostList'][0]) => {
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
  // 节点主机互斥
  const brokerDisableHostMethod = (hostData: TNodeInfo['hostList'][0]) => {
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
  // 节点主机互斥
  const zookeeperDisableHostMethod = (hostData: TNodeInfo['hostList'][0]) => {
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
        if (isEmpty.value) {
          messageError(t('至少替换一种节点类型'));
          return reject();
        }

        Promise.all([
          BookkeeperRef.value.getValue(),
          brokerRef.value.getValue(),
          zookeeperRef.value.getValue(),
        ]).then(([bookkeeperValue, brokerValue, zookeeperValue]) => {
          const isEmptyValue = () => {
            if (ipSource.value === 'manual_input') {
              return bookkeeperValue.new_nodes.length
                + brokerValue.new_nodes.length
                + zookeeperValue.new_nodes.length < 1;
            }

            return !((bookkeeperValue.resource_spec.spec_id > 0 && bookkeeperValue.resource_spec.count > 0)
              || (brokerValue.resource_spec.spec_id > 0 && brokerValue.resource_spec.count > 0)
              || (zookeeperValue.resource_spec.spec_id > 0 && zookeeperValue.resource_spec.count > 0));
          };

          if (isEmptyValue()) {
            messageError(t('替换节点不能为空'));
            return reject();
          }

          const getReplaceNodeNums = () => {
            if (ipSource.value === 'manual_input') {
              return Object.values(nodeInfoMap).reduce((result, nodeData) => result + nodeData.hostList.length, 0);
            }
            return Object.values(nodeInfoMap).reduce((result, nodeData) => {
              if (nodeData.resourceSpec.spec_id > 0 && nodeData.resourceSpec.count > 0) {
                return result + nodeData.nodeList.length;
              }
              return result;
            }, 0);
          };

          InfoBox({
            title: t('确认替换n台节点IP', { n: getReplaceNodeNums() }),
            subTitle: t('替换后原节点 IP 将不在可用，资源将会被释放'),
            confirmText: t('确认'),
            cancelText: t('取消'),
            headerAlign: 'center',
            contentAlign: 'center',
            footerAlign: 'center',
            onClosed: () => reject(),
            onConfirm: () => {
              const nodeData = {};
              if (ipSource.value === 'manual_input') {
                Object.assign(nodeData, {
                  new_nodes: {
                    bookkeeper: bookkeeperValue.new_nodes,
                    broker: brokerValue.new_nodes,
                    zookeeper: zookeeperValue.new_nodes,
                  },
                });
              } else {
                Object.assign(nodeData, {
                  resource_spec: {
                    bookkeeper: bookkeeperValue.resource_spec,
                    broker: brokerValue.resource_spec,
                    zookeeper: zookeeperValue.resource_spec,
                  },
                });
              }
              createTicket({
                ticket_type: 'PULSAR_REPLACE',
                bk_biz_id: currentBizId,
                details: {
                  cluster_id: props.data.id,
                  ip_source: ipSource.value,
                  old_nodes: {
                    bookkeeper: bookkeeperValue.old_nodes,
                    broker: brokerValue.old_nodes,
                    zookeeper: zookeeperValue.old_nodes,
                  },
                  ...nodeData,
                },
              })
                .then(() => {
                  emits('change');
                  resolve('success');
                })
                .catch(() => {
                  reject();
                });
            },
          });
        }, () => reject());
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

    .ip-srouce-box{
      display: flex;
      margin-bottom: 16px;

      .bk-radio-button{
        flex: 1;
        background: #fff;
      }
    }

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
