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
    class="es-cluster-shrink-box"
    :loading="isLoading">
    <BkAlert
      class="mb-16"
      theme="warning"
      :title="$t('热节点，冷节点，Client节点至少缩容一个类型')" />
    <div class="wrapper">
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
  import { reactive, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import EsModel from '@services/model/es/es';
  import EsMachineModel from '@services/model/es/es-machine';
  import { getEsNodeList } from '@services/source/es';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { TicketTypes } from '@common/const';

  import HostShrink, { type TShrinkNode } from '@views/db-manage/common/host-shrink/Index.vue';
  import NodeStatusList from '@views/db-manage/common/host-shrink/NodeStatusList.vue';

  import { messageError } from '@utils';

  interface Props {
    data: EsModel;
    machineList?: EsMachineModel[];
  }

  type Emits = (e: 'change') => void;

  interface Exposes {
    submit: () => Promise<any>;
  }

  const props = withDefaults(defineProps<Props>(), {
    machineList: () => [],
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const nodeStatusList = [
    {
      key: 'cold',
      label: '冷节点',
    },
    {
      key: 'hot',
      label: '热节点',
    },
    {
      key: 'client',
      label: 'Client',
    },
  ];

  const nodeStatusListRef = ref();
  const nodeInfoMap = reactive<Record<string, TShrinkNode>>({
    client: {
      hostList: [],
      label: 'Client',
      minHost: 0,
      originalNodeList: [],
      shrinkDisk: 0,
      tagText: t('接入层'),
      totalDisk: 0,
    },
    cold: {
      hostList: [],
      label: t('冷节点'),
      minHost: 0,
      originalNodeList: [],
      shrinkDisk: 0,
      tagText: t('存储层'),
      totalDisk: 0,
    },
    hot: {
      hostList: [],
      label: t('热节点'),
      minHost: 0,
      originalNodeList: [],
      shrinkDisk: 0,
      tagText: t('存储层'),
      totalDisk: 0,
    },
  });

  const isLoading = ref(false);
  const nodeType = ref('cold');

  const fetchListNode = () => {
    const hotOriginalList: TShrinkNode['originalNodeList'] = [];
    const coldOriginalList: TShrinkNode['originalNodeList'] = [];
    const clientOriginalList: TShrinkNode['originalNodeList'] = [];

    isLoading.value = true;
    getEsNodeList({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_id: props.data.id,
      no_limit: 1,
    })
      .then((data) => {
        let hotDiskTotal = 0;
        let coldDiskTotal = 0;
        let clientDiskTotal = 0;

        data.results.forEach((nodeItem) => {
          if (nodeItem.isHot) {
            hotDiskTotal += nodeItem.disk;
            hotOriginalList.push(nodeItem);
          } else if (nodeItem.isCold) {
            coldDiskTotal += nodeItem.disk;
            coldOriginalList.push(nodeItem);
          } else if (nodeItem.isClient) {
            clientDiskTotal += nodeItem.disk;
            clientOriginalList.push(nodeItem);
          }
        });

        nodeInfoMap.hot.originalNodeList = hotOriginalList;
        nodeInfoMap.hot.totalDisk = hotDiskTotal;

        nodeInfoMap.cold.originalNodeList = coldOriginalList;
        nodeInfoMap.cold.totalDisk = coldDiskTotal;

        nodeInfoMap.client.originalNodeList = clientOriginalList;
        nodeInfoMap.client.totalDisk = clientDiskTotal;
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
      const hotHostList: TShrinkNode['hostList'] = [];
      const coldHostList: TShrinkNode['hostList'] = [];
      const clientHostList: TShrinkNode['hostList'] = [];

      let hotShrinkDisk = 0;
      let coldShrinkDisk = 0;
      let clientShrinkDisk = 0;

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
          hotHostList.push(machineHost);
        } else if (machineItem.isCold) {
          coldShrinkDisk += machineDisk;
          coldHostList.push(machineHost);
        } else if (machineItem.isClient) {
          clientShrinkDisk += machineDisk;
          clientHostList.push(machineHost);
        }
      });
      nodeInfoMap.hot.hostList = hotHostList;
      nodeInfoMap.hot.shrinkDisk = hotShrinkDisk;
      nodeInfoMap.cold.hostList = coldHostList;
      nodeInfoMap.cold.shrinkDisk = coldShrinkDisk;
      nodeInfoMap.client.hostList = clientHostList;
      nodeInfoMap.client.shrinkDisk = clientShrinkDisk;

      if (coldHostList.length) {
        nodeType.value = 'cold';
      } else if (hotHostList.length) {
        nodeType.value = 'hot';
      } else if (clientHostList.length) {
        nodeType.value = 'client';
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
      // 热节点全缩容后，限制冷节点至少留1台
      nodeInfoMap.cold.minHost = 1;
    } else if (nodeInfoMap.cold.hostList.length === nodeInfoMap.cold.originalNodeList.length) {
      // 冷节点全缩容后，限制热节点至少留1台
      nodeInfoMap.hot.minHost = 1;
    } else {
      // 取消限制
      nodeInfoMap.cold.minHost = 0;
      nodeInfoMap.hot.minHost = 0;
    }
  };

  defineExpose<Exposes>({
    submit() {
      return new Promise((resolve, reject) => {
        if (!nodeStatusListRef.value.validate()) {
          messageError(t('热节点，冷节点，Client节点至少缩容一个类型'));
          return reject();
        }

        const renderSubTitle = () => {
          const renderShrinkDiskTips = () =>
            Object.values(nodeInfoMap).map((nodeData) => {
              if (nodeData.shrinkDisk) {
                return (
                  <div>
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

          return <div style='font-size: 14px; line-height: 28px; color: #63656E;'>{renderShrinkDiskTips()}</div>;
        };

        InfoBox({
          cancelText: t('取消'),
          confirmText: t('确认'),
          contentAlign: 'center',
          footerAlign: 'center',
          headerAlign: 'center',
          onCancel: () => reject(),
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

            return createTicket({
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              details: {
                cluster_id: props.data.id,
                ext_info: generateExtInfo(),
                ip_source: 'resource_pool',
                old_nodes: {
                  client: fomatHost(nodeInfoMap.client.hostList),
                  cold: fomatHost(nodeInfoMap.cold.hostList),
                  hot: fomatHost(nodeInfoMap.hot.hostList),
                },
              },
              ticket_type: TicketTypes.ES_SHRINK,
            }).then((data) => {
              ticketMessage(data.id);
              resolve('success');
              emits('change');
            });
          },
          subTitle: renderSubTitle,
          title: t('确认缩容【name】集群', { name: props.data.cluster_name }),
        });
      });
    },
  });
</script>
<style lang="less">
  .es-cluster-shrink-box {
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
