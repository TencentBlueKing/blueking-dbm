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
    class="pulsar-cluster-shrink-box"
    :loading="isLoading">
    <BkAlert
      class="mb16"
      theme="warning"
      :title="$t('Bookkeeper_Broker 至少缩容一种类型')" />
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
          :cluster-id="props.data.id"
          :data="nodeInfoMap[nodeType]"
          @change="handleNodeHostChange"
          @target-disk-change="handleTargetDiskChange" />
      </div>
    </div>
    <div>
      <div class="item-label">
        {{ $t('备注') }}
      </div>
      <BkInput
        v-model="remark"
        :maxlength="100"
        :placeholder="$t('请提供更多有用信息申请信息_以获得更快审批')"
        type="textarea" />
    </div>
  </BkLoading>
</template>
<script lang="tsx">
  export interface TNodeInfo {
    label: string,
    originalNodeList: PulsarNodeModel[],
    nodeList?: PulsarNodeModel[],
    totalDisk: number,
    targetDisk: number,
    shrinkDisk: number,
    minHost: number,
  }
</script>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import {
    reactive,
    ref,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type PulsarModel from '@services/model/pulsar/pulsar';
  import type PulsarNodeModel from '@services/model/pulsar/pulsar-node';
  import { getListNodes } from '@services/pulsar';
  import { createTicket } from '@services/ticket';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { messageError } from '@utils';

  import NodeList from './components/NodeList.vue';
  import RenderNode from './components/RenderNode.vue';

  interface Props {
    data: PulsarModel,
    nodeList?: PulsarNodeModel[]
  }

  interface Emits {
    (e: 'change'): void
  }

  interface Exposes {
    submit: () => Promise<any>
  }

  const props = withDefaults(defineProps<Props>(), {
    nodeList: () => [],
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const bizId = globalBizsStore.currentBizId;

  const nodeInfoMap = reactive<Record<string, TNodeInfo>>({
    broker: {
      label: 'Broker',
      originalNodeList: [],
      nodeList: undefined,
      // 当前主机总容量
      totalDisk: 0,
      // 缩容后的目标容量
      targetDisk: 0,
      // 实际选择的缩容主机容量
      shrinkDisk: 0,
      minHost: 1,
    },
    bookkeeper: {
      label: 'Bookkeeper',
      originalNodeList: [],
      nodeList: undefined,
      totalDisk: 0,
      targetDisk: 0,
      shrinkDisk: 0,
      minHost: 2,
    },
  });

  const isLoading = ref(false);
  const nodeType = ref('bookkeeper');
  const remark = ref('');

  const fetchListNode = () => {
    const bookkeeperOriginalNodeList: PulsarNodeModel[] = [];
    const brokerOriginalNodeList: PulsarNodeModel[] = [];

    isLoading.value = true;
    getListNodes({
      bk_biz_id: globalBizsStore.currentBizId,
      cluster_id: props.data.id,
      no_limit: 1,
    }).then((data) => {
      let bookkeeperDiskTotal = 0;
      let brokerDiskTotal = 0;

      data.results.forEach((nodeItem) => {
        if (nodeItem.isBookkeeper) {
          bookkeeperDiskTotal += nodeItem.disk;
          bookkeeperOriginalNodeList.push(nodeItem);
        } else if (nodeItem.isBroker) {
          brokerDiskTotal += nodeItem.disk;
          brokerOriginalNodeList.push(nodeItem);
        }
      });

      nodeInfoMap.bookkeeper.originalNodeList = bookkeeperOriginalNodeList;
      nodeInfoMap.bookkeeper.totalDisk = bookkeeperDiskTotal;
      if (nodeInfoMap.bookkeeper.shrinkDisk) {
        nodeInfoMap.bookkeeper.targetDisk = bookkeeperDiskTotal - nodeInfoMap.bookkeeper.shrinkDisk;
      }

      nodeInfoMap.broker.originalNodeList = brokerOriginalNodeList;
      nodeInfoMap.broker.totalDisk = brokerDiskTotal;
      if (nodeInfoMap.broker.shrinkDisk) {
        nodeInfoMap.broker.targetDisk = brokerDiskTotal - nodeInfoMap.broker.shrinkDisk;
      }
    })
      .finally(() => {
        isLoading.value = false;
      });
  };

  fetchListNode();

  // 默认选中的缩容节点
  watch(() => props.nodeList, () => {
    const bookkeeperNodeList: PulsarNodeModel[] = [];
    const brokerNodeList: PulsarNodeModel[] = [];

    let bookkeeperShrinkDisk = 0;
    let brokerShrinkDisk = 0;

    props.nodeList.forEach((nodeItem) => {
      if (nodeItem.isBookkeeper) {
        bookkeeperShrinkDisk += nodeItem.disk;
        bookkeeperNodeList.push(nodeItem);
      } else if (nodeItem.isBroker) {
        brokerShrinkDisk += nodeItem.disk;
        brokerNodeList.push(nodeItem);
      }
    });
    nodeInfoMap.bookkeeper.nodeList = bookkeeperNodeList;
    nodeInfoMap.bookkeeper.shrinkDisk = bookkeeperShrinkDisk;
    nodeInfoMap.broker.nodeList = brokerNodeList;
    nodeInfoMap.broker.shrinkDisk = brokerShrinkDisk;
  }, {
    immediate: true,
  });

  // 容量修改
  const handleTargetDiskChange = (value: number) => {
    nodeInfoMap[nodeType.value].targetDisk = value;
  };

  // 缩容节点主机修改
  const handleNodeHostChange = (nodeList: PulsarNodeModel[]) => {
    const shrinkDisk = nodeList.reduce((result, hostItem) => result + hostItem.disk, 0);
    nodeInfoMap[nodeType.value].nodeList = nodeList;
    nodeInfoMap[nodeType.value].shrinkDisk = shrinkDisk;
  };

  defineExpose<Exposes>({
    submit() {
      const isEmpty = (nodeList: undefined | PulsarNodeModel[]) => !nodeList || nodeList.length < 1;

      return new Promise((resolve, reject) => {
        if (isEmpty(nodeInfoMap.broker.nodeList)
          && isEmpty(nodeInfoMap.bookkeeper.nodeList)) {
          // 设置 hostList 为 [] 触发校验标记
          Object.values(nodeInfoMap).forEach((nodeInfo) => {
            if (nodeInfo.targetDisk > 0 && !nodeInfo.nodeList) {
              // eslint-disable-next-line no-param-reassign
              nodeInfo.nodeList = [];
            }
          });
          messageError(t('Bookkeeper_Broker 至少缩容一种类型'));
          return reject();
        }

        InfoBox({
          title: t('确认缩容【name】集群', { name: props.data.cluster_name }),
          subTitle: () => {
            const renderDiskInfo = () => {
              console.log('asda');
              return null;
            };

            const renderBookkeeper = () => {
              const {
                nodeList,
                totalDisk,
                targetDisk,
              } = nodeInfoMap.bookkeeper;
              if (nodeList && nodeList.length < 1) {
                return null;
              }
              return (
                <div>
                  Bookkeeper 的容量将从 { totalDisk } 缩至 { targetDisk }
                </div>
              );
            };

            const renderBroker = () => {
              const {
                nodeList,
                totalDisk,
                targetDisk,
              } = nodeInfoMap.broker;
              if (nodeList && nodeList.length < 1) {
                return null;
              }
              return (
                <div>
                  Broker 的容量将从 { totalDisk } 缩至 { targetDisk }
                </div>
              );
            };

            return (
              <div style="font-size: 14px; color: #63656E; line-height: 28px">
                { renderDiskInfo() }
                { renderBookkeeper() }
                { renderBroker() }
              </div>
            );
          },
          confirmText: t('确认'),
          cancelText: t('取消'),
          headerAlign: 'center',
          contentAlign: 'center',
          footerAlign: 'center',
          onClosed: () => reject(),
          onConfirm: () => {
            const fomatHost = (nodeList: PulsarNodeModel[] = []) => nodeList.map(hostItem => ({
              ip: hostItem.ip,
              bk_cloud_id: hostItem.bk_cloud_id,
              bk_host_id: hostItem.bk_host_id,
              bk_biz_id: bizId,
            }));

            createTicket({
              ticket_type: 'PULSAR_SHRINK',
              bk_biz_id: bizId,
              details: {
                cluster_id: props.data.id,
                ip_source: 'manual_input',
                nodes: {
                  broker: fomatHost(nodeInfoMap.broker.nodeList),
                  bookkeeper: fomatHost(nodeInfoMap.bookkeeper.nodeList),
                },
              },
              remark: remark.value,
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
  .pulsar-cluster-shrink-box {
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
