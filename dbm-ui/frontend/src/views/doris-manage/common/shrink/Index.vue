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
    class="doris-cluster-shrink-box"
    :loading="isLoading">
    <BkAlert
      class="mb16"
      theme="warning"
      :title="t('至少缩容一种类型')" />
    <div class="box-wrapper">
      <NodeStatusList
        ref="nodeStatusListRef"
        v-model="nodeType"
        :list="nodeStatusList"
        :node-info="nodeInfoMap" />
      <div class="node-panel">
        <template v-if="nodeType === 'observer'">
          <DorisObserverHostShrink
            v-if="!isLoading"
            :key="nodeType"
            :data="nodeInfoMap[nodeType]"
            @change="handleNodeHostChange"
            @target-disk-change="handleTargetDiskChange" />
        </template>
        <template v-else>
          <HostShrink
            v-if="!isLoading"
            :key="nodeType"
            :data="nodeInfoMap[nodeType]"
            @change="handleNodeHostChange"
            @target-disk-change="handleTargetDiskChange" />
        </template>
      </div>
    </div>
  </BkLoading>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import type { ComponentExposed } from 'vue-component-type-helpers'
  import { useI18n } from 'vue-i18n';

  import type DorisModel from '@services/model/doris/doris';
  import type DorisNodeModel from '@services/model/doris/doris-node';
  import { getDorisNodeList } from '@services/source/doris';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import DorisObserverHostShrink from '@components/cluster-common/doris-observer-host-shrink/Index.vue'
  import HostShrink, {
    type TShrinkNode,
  } from '@components/cluster-common/host-shrink/Index.vue';
  import NodeStatusList from '@components/cluster-common/host-shrink/NodeStatusList.vue';

  import { messageError } from '@utils';

  type TNodeInfo = TShrinkNode<DorisNodeModel>

  interface Props {
    data: DorisModel,
    nodeList?: TNodeInfo['nodeList']
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

  const generateNodeInfo = (values: Pick<TNodeInfo, 'label' | 'minHost' | 'tagText'>): TNodeInfo => ({
    ...values,
    originalNodeList: [],
    nodeList: [],
    totalDisk: 0,
    targetDisk: 0,
    shrinkDisk: 0,
  })

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const bizId = globalBizsStore.currentBizId;

  const nodeStatusList = [
    {
      key: 'cold',
      label: t('冷节点'),
    },
    {
      key: 'hot',
      label: t('热节点'),
    },
    {
      key: 'observer',
      label: 'Observer',
    },
  ];

  const nodeStatusListRef = ref<ComponentExposed<typeof NodeStatusList>>();

  const nodeInfoMap = reactive<Record<string, TNodeInfo>>({
    hot: generateNodeInfo({
      label: t('热节点'),
      minHost: 0,
      tagText: t('存储层')
    }),
    cold: generateNodeInfo({
      label: t('冷节点'),
      minHost: 0,
      tagText: t('存储层')
    }),
    observer: generateNodeInfo({
      label: 'Observer',
      minHost: 0,
      tagText: t('接入层')
    }),
  });

  const isLoading = ref(false);
  const nodeType = ref('cold');

  const fetchListNode = () => {
    const hotOriginalNodeList: TNodeInfo['nodeList'] = [];
    const coldOriginalNodeList: TNodeInfo['nodeList'] = [];
    const observerOriginalNodeList: TNodeInfo['nodeList'] = [];

    isLoading.value = true;
    getDorisNodeList({
      bk_biz_id: globalBizsStore.currentBizId,
      cluster_id: props.data.id,
      no_limit: 1,
    })
      .then((data) => {
        let hotDiskTotal = 0;
        let coldDiskTotal = 0;
        let observerDiskTotal = 0;

        data.results.forEach((nodeItem) => {
          if (nodeItem.isHot) {
            hotDiskTotal += nodeItem.disk;
            hotOriginalNodeList.push(nodeItem);
          } else if (nodeItem.isCold) {
            coldDiskTotal += nodeItem.disk;
            coldOriginalNodeList.push(nodeItem);
          } else if (nodeItem.isObserver) {
            observerDiskTotal += nodeItem.disk;
            observerOriginalNodeList.push(nodeItem);
          }
        });

        nodeInfoMap.hot.originalNodeList = hotOriginalNodeList;
        nodeInfoMap.hot.totalDisk = hotDiskTotal;
        if (nodeInfoMap.hot.shrinkDisk) {
          nodeInfoMap.hot.targetDisk = hotDiskTotal - nodeInfoMap.hot.shrinkDisk;
        }

        nodeInfoMap.cold.originalNodeList = coldOriginalNodeList;
        nodeInfoMap.cold.totalDisk = coldDiskTotal;
        if (nodeInfoMap.cold.shrinkDisk) {
          nodeInfoMap.cold.targetDisk = coldDiskTotal - nodeInfoMap.cold.shrinkDisk;
        }

        nodeInfoMap.observer.originalNodeList = observerOriginalNodeList;
        nodeInfoMap.observer.totalDisk = observerDiskTotal;
        if (nodeInfoMap.observer.shrinkDisk) {
          nodeInfoMap.observer.targetDisk = observerDiskTotal - nodeInfoMap.observer.shrinkDisk;
        }
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  fetchListNode();

  // 默认选中的缩容节点
  watch(() => props.nodeList, () => {
    const hotNodeList: TNodeInfo['nodeList'] = [];
    const coldNodeList: TNodeInfo['nodeList'] = [];
    const observerNodeList: TNodeInfo['nodeList'] = [];

    let hotShrinkDisk = 0;
    let coldShrinkDisk = 0;
    let observerShrinkDisk = 0;

    props.nodeList.forEach((nodeItem) => {
      if (nodeItem.isHot) {
        hotShrinkDisk += nodeItem.disk;
        hotNodeList.push(nodeItem);
      } else if (nodeItem.isCold) {
        coldShrinkDisk += nodeItem.disk;
        coldNodeList.push(nodeItem);
      } else if (nodeItem.isObserver) {
        observerShrinkDisk += nodeItem.disk;
        observerNodeList.push(nodeItem);
      }
    });
    nodeInfoMap.hot.nodeList = hotNodeList;
    nodeInfoMap.hot.shrinkDisk = hotShrinkDisk;
    nodeInfoMap.cold.nodeList = coldNodeList;
    nodeInfoMap.cold.shrinkDisk = coldShrinkDisk;
    nodeInfoMap.observer.nodeList = observerNodeList;
    nodeInfoMap.observer.shrinkDisk = observerShrinkDisk;
  }, {
    immediate: true,
  });

  // 容量修改
  const handleTargetDiskChange = (value: number) => {
    nodeInfoMap[nodeType.value].targetDisk = value;
  };

  // 缩容节点主机修改
  const handleNodeHostChange = (nodeList: TNodeInfo['nodeList']) => {
    const shrinkDisk = nodeList.reduce((result, hostItem) => result + hostItem.disk, 0);
    nodeInfoMap[nodeType.value].nodeList = nodeList;
    nodeInfoMap[nodeType.value].shrinkDisk = shrinkDisk;

    if (nodeInfoMap.hot.nodeList.length === nodeInfoMap.hot.originalNodeList.length) {
      // 热节点全缩容后，限制冷节点至少留2台
      nodeInfoMap.cold.minHost = 2;
      if (nodeInfoMap.cold.originalNodeList.length === 2) {
        // 冷节点只有2台并且已经不可编辑状态，需要初始化已填写的目标容量值
        nodeInfoMap.cold.targetDisk = 0;
      }
    } else if (nodeInfoMap.cold.nodeList.length === nodeInfoMap.cold.originalNodeList.length) {
      // 冷节点全缩容后，限制热节点至少留2台
      nodeInfoMap.hot.minHost = 2;
      if (nodeInfoMap.hot.originalNodeList.length === 2) {
        // 热节点只有2台并且已经不可编辑状态，需要初始化已填写的目标容量值
        nodeInfoMap.hot.targetDisk = 0;
      }
    } else {
      // 取消限制
      nodeInfoMap.cold.minHost = 0;
      nodeInfoMap.hot.minHost = 0;
    }
  };

  defineExpose<Exposes>({
    submit() {
      return new Promise((resolve, reject) => {
        if (!nodeStatusListRef.value!.validate()) {
          messageError(t('至少缩容一种类型'));
          return reject();
        }

        const renderSubTitle = () => {
          const renderDiskTips = () => {
            const isNotMatch = Object.values(nodeInfoMap)
              .some(nodeData => nodeData.totalDisk + nodeData.shrinkDisk !== nodeData.targetDisk);
            if (isNotMatch) {
              return (
                <div style="font-size: 14px">
                  <div>{t('目标容量与所选 IP 容量不一致，确认提交？')}</div>
                  <div class="mb-8">{t('继续提交将按照手动选择的 IP 容量进行')}</div>
                </div>
              );
            }
            return null;
          };
          const renderShrinkDiskTips = () => Object.entries(nodeInfoMap).map(([nodeType, nodeData]) => {
            if (nodeData.shrinkDisk) {
              if (nodeType === 'observer') {
                return (
                  <div class='tips-item'>
                    {t('name容量从n台缩容至n台', {
                      name: nodeData.label,
                      hostNumBefore: nodeData.originalNodeList.length,
                      hostNumAfter: nodeData.originalNodeList.length - nodeData.nodeList.length,
                    })}
                  </div>
                );
              }
              return (
                <div class='tips-item'>
                  {t('name容量从nG缩容至nG', {
                    name: nodeData.label,
                    totalDisk: nodeData.totalDisk,
                    targetDisk: nodeData.totalDisk - nodeData.shrinkDisk,
                  })}
                </div>
              );
            }
            return null;
          });

          return (
            <div>
              {renderDiskTips()}
              <div style="background-color: #F5F7FA; padding: 8px 16px;">
                <div class='tips-item'>
                  {t('集群')} :
                  <span
                    style="color: #313238"
                    class="ml-8">
                    {props.data.cluster_name}
                  </span>
                </div>
                {renderShrinkDiskTips()}
              </div>
            </div>
          );
        };

        InfoBox({
          title: t('确认缩容【name】集群', { name: props.data.cluster_name }),
          subTitle: renderSubTitle,
          confirmText: t('确认'),
          cancelText: t('取消'),
          headerAlign: 'center',
          contentAlign: 'left',
          footerAlign: 'center',
          extCls: 'doris-shrink-modal',
          onClose: () => reject(),
          onConfirm: () => {
            const fomatHost = (nodeList: TNodeInfo['nodeList'] = []) => nodeList.map(hostItem => ({
              ip: hostItem.ip,
              bk_cloud_id: hostItem.bk_cloud_id,
              bk_host_id: hostItem.bk_host_id,
              bk_biz_id: bizId,
            }));

            const generateExtInfo = () => Object.entries(nodeInfoMap).reduce((results, [key, item]) => {
              const obj = {
                host_list: item.nodeList.map(item => ({
                  ip: item.ip,
                  bk_disk: item.disk,
                  alive: item.status,
                })),
                total_hosts: item.originalNodeList.length,
                total_disk: item.totalDisk,
                target_disk: item.targetDisk,
                shrink_disk: item.shrinkDisk,
              };
              Object.assign(results, {
                [key]: obj,
              });
              return results;
            }, {} as Record<string, TNodeInfo>);

            createTicket({
              ticket_type: TicketTypes.DORIS_SHRINK,
              bk_biz_id: bizId,
              details: {
                cluster_id: props.data.id,
                ip_source: 'manual_input',
                nodes: {
                  hot: fomatHost(nodeInfoMap.hot.nodeList),
                  cold: fomatHost(nodeInfoMap.cold.nodeList),
                  observer: fomatHost(nodeInfoMap.observer.nodeList),
                },
                ext_info: generateExtInfo(),
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
  .doris-shrink-modal {
    .bk-modal-content div {
      font-size: 14px;
    }

    .tips-item {
      padding: 2px 0;
    }
  }
</style>
<style lang="less">
  .doris-cluster-shrink-box {
    padding: 18px 43px 18px 37px;
    font-size: 12px;
    line-height: 20px;
    color: #63656e;
    background: #f5f7fa;

    .box-wrapper {
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
