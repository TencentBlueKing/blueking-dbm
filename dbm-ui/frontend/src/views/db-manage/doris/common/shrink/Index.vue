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
        <HostShrink
          v-if="!isLoading"
          :key="nodeType"
          :data="nodeInfoMap[nodeType]"
          @change="handleNodeHostChange" />
      </div>
    </div>
  </BkLoading>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import DorisModel from '@services/model/doris/doris';
  import DorisMachineModel from '@services/model/doris/doris-machine';
  import { getDorisNodeList } from '@services/source/doris';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { TicketTypes } from '@common/const';

  import HostShrink, { type TShrinkNode } from '@views/db-manage/common/host-shrink/Index.vue';
  import NodeStatusList from '@views/db-manage/common/host-shrink/NodeStatusList.vue';

  import { messageError } from '@utils';

  interface Props {
    data: DorisModel;
    machineList?: DorisMachineModel[];
  }

  type Emits = (e: 'change') => void;

  interface Exposes {
    submit: () => Promise<any>;
  }

  const props = withDefaults(defineProps<Props>(), {
    machineList: () => [],
  });
  const emits = defineEmits<Emits>();

  const generateNodeInfo = (values: Pick<TShrinkNode, 'label' | 'minHost' | 'tagText'>): TShrinkNode => ({
    ...values,
    hostList: [],
    originalNodeList: [],
    // targetDisk: 0,
    shrinkDisk: 0,
    totalDisk: 0,
  });

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

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

  const nodeInfoMap = reactive<Record<string, TShrinkNode>>({
    cold: generateNodeInfo({
      label: t('冷节点'),
      minHost: 0,
      tagText: t('存储层'),
    }),
    hot: generateNodeInfo({
      label: t('热节点'),
      minHost: 0,
      tagText: t('存储层'),
    }),
    observer: generateNodeInfo({
      label: 'Observer',
      minHost: 0,
      tagText: t('接入层'),
    }),
  });

  const isLoading = ref(false);
  const nodeType = ref('cold');

  const fetchListNode = () => {
    const hotOriginalNodeList: TShrinkNode['originalNodeList'] = [];
    const coldOriginalNodeList: TShrinkNode['originalNodeList'] = [];
    const observerOriginalNodeList: TShrinkNode['originalNodeList'] = [];

    isLoading.value = true;
    getDorisNodeList({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
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

        nodeInfoMap.cold.originalNodeList = coldOriginalNodeList;
        nodeInfoMap.cold.totalDisk = coldDiskTotal;

        nodeInfoMap.observer.originalNodeList = observerOriginalNodeList;
        nodeInfoMap.observer.totalDisk = observerDiskTotal;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  fetchListNode();

  // 默认选中的缩容节点
  watch(
    () => props.machineList,
    () => {
      const hotList: TShrinkNode['hostList'] = [];
      const coldList: TShrinkNode['hostList'] = [];
      const observerList: TShrinkNode['hostList'] = [];

      let hotShrinkDisk = 0;
      let coldShrinkDisk = 0;
      let observerShrinkDisk = 0;

      props.machineList.forEach((machineItem) => {
        const machineDisk = machineItem.host_info?.bk_disk || 0;
        const machineHost = {
          alive: machineItem.host_info?.alive || 0,
          bk_cloud_id: machineItem.bk_cloud_id,
          bk_disk: machineDisk,
          bk_host_id: machineItem.bk_host_id,
          ip: machineItem.ip,
        };
        if (machineItem.isHot) {
          hotShrinkDisk += machineDisk;
          hotList.push(machineHost);
        } else if (machineItem.isCold) {
          coldShrinkDisk += machineDisk;
          coldList.push(machineHost);
        } else if (machineItem.isObserver) {
          observerShrinkDisk += machineDisk;
          observerList.push(machineHost);
        }
      });
      nodeInfoMap.hot.hostList = hotList;
      nodeInfoMap.hot.shrinkDisk = hotShrinkDisk;
      nodeInfoMap.cold.hostList = coldList;
      nodeInfoMap.cold.shrinkDisk = coldShrinkDisk;
      nodeInfoMap.observer.hostList = observerList;
      nodeInfoMap.observer.shrinkDisk = observerShrinkDisk;

      if (coldList.length) {
        nodeType.value = 'cold';
      } else if (hotList.length) {
        nodeType.value = 'hot';
      } else if (observerList) {
        nodeType.value = 'observer';
      }
    },
    {
      immediate: true,
    },
  );

  // 缩容节点主机修改
  const handleNodeHostChange = (hostList: TShrinkNode['hostList']) => {
    const shrinkDisk = hostList.reduce((result, hostItem) => result + (hostItem.bk_disk || 0), 0);
    nodeInfoMap[nodeType.value].hostList = hostList;
    nodeInfoMap[nodeType.value].shrinkDisk = shrinkDisk;

    if (nodeInfoMap.hot.hostList.length === nodeInfoMap.hot.originalNodeList.length) {
      // 热节点全缩容后，限制冷节点至少留2台
      nodeInfoMap.cold.minHost = 2;
    } else if (nodeInfoMap.cold.hostList.length === nodeInfoMap.cold.originalNodeList.length) {
      // 冷节点全缩容后，限制热节点至少留2台
      nodeInfoMap.hot.minHost = 2;
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
          const renderShrinkDiskTips = () =>
            Object.entries(nodeInfoMap).map(([nodeType, nodeData]) => {
              if (nodeData.shrinkDisk) {
                if (nodeType === 'observer') {
                  return (
                    <div class='tips-item'>
                      {t('name容量从n台缩容至n台', {
                        hostNumAfter: nodeData.originalNodeList.length - nodeData.hostList.length,
                        hostNumBefore: nodeData.originalNodeList.length,
                        name: nodeData.label,
                      })}
                    </div>
                  );
                }
                return (
                  <div class='tips-item'>
                    {t('name容量从nG缩容至nG', {
                      name: nodeData.label,
                      targetDisk: nodeData.totalDisk - nodeData.shrinkDisk,
                      totalDisk: nodeData.totalDisk,
                    })}
                  </div>
                );
              }
              return null;
            });

          return (
            <div style='background-color: #F5F7FA; padding: 8px 16px;'>
              <div class='tips-item'>
                {t('集群')} :
                <span
                  class='ml-8'
                  style='color: #313238'>
                  {props.data.cluster_name}
                </span>
              </div>
              {renderShrinkDiskTips()}
            </div>
          );
        };

        InfoBox({
          cancelText: t('取消'),
          confirmText: t('确认'),
          contentAlign: 'left',
          extCls: 'doris-shrink-modal',
          footerAlign: 'center',
          headerAlign: 'center',
          onClose: () => reject(),
          onConfirm: () => {
            const fomatHost = (hostList: TShrinkNode['hostList'] = []) =>
              hostList.map((hostItem) => ({
                bk_cloud_id: hostItem.bk_cloud_id,
                bk_host_id: hostItem.bk_host_id,
                ip: hostItem.ip,
              }));

            const generateExtInfo = () =>
              Object.entries(nodeInfoMap).reduce(
                (results, [key, item]) => {
                  Object.assign(results, {
                    [key]: {
                      shrink_disk: item.shrinkDisk,
                      total_disk: item.totalDisk,
                      total_hosts: item.originalNodeList.length,
                    },
                  });
                  return results;
                },
                {} as Record<string, TShrinkNode>,
              );

            createTicket({
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              details: {
                cluster_id: props.data.id,
                ext_info: generateExtInfo(),
                ip_source: 'resource_pool',
                old_nodes: {
                  cold: fomatHost(nodeInfoMap.cold.hostList),
                  hot: fomatHost(nodeInfoMap.hot.hostList),
                  observer: fomatHost(nodeInfoMap.observer.hostList),
                },
              },
              ticket_type: TicketTypes.DORIS_SHRINK,
            })
              .then((data) => {
                ticketMessage(data.id);
                resolve('success');
                emits('change');
              })
              .catch(() => {
                reject();
              });
          },
          subTitle: renderSubTitle,
          title: t('确认缩容【name】集群', {
            name: props.data.cluster_name,
          }),
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
