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
      class="mb16"
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

  import type EsModel from '@services/model/es/es';
  import type EsNodeModel from '@services/model/es/es-node';
  import { getEsNodeList } from '@services/source/es';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import HostShrink, { type TShrinkNode } from '@views/db-manage/common/host-shrink/Index.vue';
  import NodeStatusList from '@views/db-manage/common/host-shrink/NodeStatusList.vue';

  import { messageError } from '@utils';

  type TNodeInfo = TShrinkNode<EsNodeModel>;

  interface Props {
    data: EsModel;
    nodeList?: TNodeInfo['nodeList'];
  }

  type Emits = (e: 'change') => void;

  interface Exposes {
    submit: () => Promise<any>;
  }

  const props = withDefaults(defineProps<Props>(), {
    nodeList: () => [],
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const bizId = globalBizsStore.currentBizId;

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
  const nodeInfoMap = reactive<Record<string, TNodeInfo>>({
    client: {
      label: 'Client',
      minHost: 0,
      nodeList: [],
      originalNodeList: [],
      // targetDisk: 0,
      shrinkDisk: 0,
      tagText: t('接入层'),
      totalDisk: 0,
    },
    cold: {
      label: t('冷节点'),
      minHost: 0,
      nodeList: [],
      originalNodeList: [],
      // targetDisk: 0,
      shrinkDisk: 0,
      tagText: t('存储层'),
      totalDisk: 0,
    },
    hot: {
      label: t('热节点'),
      minHost: 0,
      nodeList: [],
      originalNodeList: [],
      // targetDisk: 0,
      shrinkDisk: 0,
      tagText: t('存储层'),
      totalDisk: 0,
    },
  });

  const isLoading = ref(false);
  const nodeType = ref('cold');

  const fetchListNode = () => {
    const hotOriginalNodeList: TNodeInfo['nodeList'] = [];
    const coldOriginalNodeList: TNodeInfo['nodeList'] = [];
    const clientOriginalNodeList: TNodeInfo['nodeList'] = [];

    isLoading.value = true;
    getEsNodeList({
      bk_biz_id: globalBizsStore.currentBizId,
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
            hotOriginalNodeList.push(nodeItem);
          } else if (nodeItem.isCold) {
            coldDiskTotal += nodeItem.disk;
            coldOriginalNodeList.push(nodeItem);
          } else if (nodeItem.isClient) {
            clientDiskTotal += nodeItem.disk;
            clientOriginalNodeList.push(nodeItem);
          }
        });

        nodeInfoMap.hot.originalNodeList = hotOriginalNodeList;
        nodeInfoMap.hot.totalDisk = hotDiskTotal;

        nodeInfoMap.cold.originalNodeList = coldOriginalNodeList;
        nodeInfoMap.cold.totalDisk = coldDiskTotal;

        nodeInfoMap.client.originalNodeList = clientOriginalNodeList;
        nodeInfoMap.client.totalDisk = clientDiskTotal;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  fetchListNode();

  // 默认选中的缩容节点
  watch(
    () => props.nodeList,
    () => {
      const hotNodeList: TNodeInfo['nodeList'] = [];
      const coldNodeList: TNodeInfo['nodeList'] = [];
      const clientNodeList: TNodeInfo['nodeList'] = [];

      let hotShrinkDisk = 0;
      let coldShrinkDisk = 0;
      let clientShrinkDisk = 0;

      props.nodeList.forEach((nodeItem) => {
        if (nodeItem.isHot) {
          hotShrinkDisk += nodeItem.disk;
          hotNodeList.push(nodeItem);
        } else if (nodeItem.isCold) {
          coldShrinkDisk += nodeItem.disk;
          coldNodeList.push(nodeItem);
        } else if (nodeItem.isClient) {
          clientShrinkDisk += nodeItem.disk;
          clientNodeList.push(nodeItem);
        }
      });
      nodeInfoMap.hot.nodeList = hotNodeList;
      nodeInfoMap.hot.shrinkDisk = hotShrinkDisk;
      nodeInfoMap.cold.nodeList = coldNodeList;
      nodeInfoMap.cold.shrinkDisk = coldShrinkDisk;
      nodeInfoMap.client.nodeList = clientNodeList;
      nodeInfoMap.client.shrinkDisk = clientShrinkDisk;

      if (coldNodeList.length) {
        nodeType.value = 'cold';
      } else if (hotNodeList.length) {
        nodeType.value = 'hot';
      } else if (clientNodeList.length) {
        nodeType.value = 'client';
      }
    },
    {
      immediate: true,
    },
  );

  // 缩容节点主机修改
  const handleNodeHostChange = (nodeList: TNodeInfo['nodeList']) => {
    const shrinkDisk = nodeList.reduce((result, hostItem) => result + hostItem.disk, 0);
    nodeInfoMap[nodeType.value].nodeList = nodeList;
    nodeInfoMap[nodeType.value].shrinkDisk = shrinkDisk;
    if (nodeInfoMap.hot.nodeList.length === nodeInfoMap.hot.originalNodeList.length) {
      // 热节点全缩容后，限制冷节点至少留1台
      nodeInfoMap.cold.minHost = 1;
    } else if (nodeInfoMap.cold.nodeList.length === nodeInfoMap.cold.originalNodeList.length) {
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
            const fomatHost = (nodeList: TNodeInfo['nodeList'] = []) =>
              nodeList.map((hostItem) => ({
                bk_biz_id: bizId,
                bk_cloud_id: hostItem.bk_cloud_id,
                bk_host_id: hostItem.bk_host_id,
                ip: hostItem.ip,
              }));

            const generateExtInfo = () =>
              Object.entries(nodeInfoMap).reduce(
                (results, [key, item]) => {
                  const obj = {
                    host_list: item.nodeList.map((item) => ({
                      alive: item.status,
                      bk_disk: item.disk,
                      ip: item.ip,
                    })),
                    // target_disk: item.targetDisk,
                    shrink_disk: item.shrinkDisk,
                    total_disk: item.totalDisk,
                    total_hosts: item.originalNodeList.length,
                  };
                  Object.assign(results, {
                    [key]: obj,
                  });
                  return results;
                },
                {} as Record<string, any>,
              );

            return createTicket({
              bk_biz_id: bizId,
              details: {
                cluster_id: props.data.id,
                ext_info: generateExtInfo(),
                ip_source: 'manual_input',
                nodes: {
                  client: fomatHost(nodeInfoMap.client.nodeList),
                  cold: fomatHost(nodeInfoMap.cold.nodeList),
                  hot: fomatHost(nodeInfoMap.hot.nodeList),
                },
              },
              ticket_type: 'ES_SHRINK',
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
