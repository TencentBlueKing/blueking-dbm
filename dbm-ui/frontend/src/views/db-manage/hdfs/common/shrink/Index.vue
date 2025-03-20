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
    class="hdfs-cluster-shrink-box"
    :loading="isLoading">
    <div class="wrapper">
      <NodeStatusList
        v-show="false"
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

  import type HdfsModel from '@services/model/hdfs/hdfs';
  import type HdfsNodeModel from '@services/model/hdfs/hdfs-node';
  import { getHdfsNodeList } from '@services/source/hdfs';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { TicketTypes } from '@common/const';

  import HostShrink, { type TShrinkNode } from '@views/db-manage/common/host-shrink/Index.vue';
  import NodeStatusList from '@views/db-manage/common/host-shrink/NodeStatusList.vue';

  import { messageError } from '@utils';

  type TNodeInfo = TShrinkNode<HdfsNodeModel>;

  interface Props {
    data: HdfsModel;
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
  const ticketMessage = useTicketMessage();

  const nodeStatusList = [
    {
      key: 'datanode',
      label: 'DataNode',
    },
  ];

  const nodeStatusListRef = ref();
  const nodeInfoMap = reactive<Record<string, TNodeInfo>>({
    datanode: {
      label: 'DataNode',
      // 最小主机数
      minHost: 2,
      nodeList: [],
      originalNodeList: [],
      // 缩容后的目标容量
      // targetDisk: 0,
      // 实际选择的缩容主机容量
      shrinkDisk: 0,
      tagText: t('存储层'),
      // 当前主机总容量
      totalDisk: 0,
    },
  });

  const isLoading = ref(false);
  const nodeType = ref('datanode');

  const fetchListNode = () => {
    const datanodeOriginalNodeList: TNodeInfo['nodeList'] = [];

    isLoading.value = true;
    getHdfsNodeList({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_id: props.data.id,
      no_limit: 1,
    })
      .then((data) => {
        let datanodeDiskTotal = 0;

        data.results.forEach((nodeItem) => {
          if (nodeItem.isDataNode) {
            datanodeDiskTotal += nodeItem.disk;
            datanodeOriginalNodeList.push(nodeItem);
          }
        });

        nodeInfoMap.datanode.originalNodeList = datanodeOriginalNodeList;
        nodeInfoMap.datanode.totalDisk = datanodeDiskTotal;
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
      const datanodeList: TNodeInfo['nodeList'] = [];

      let datanodeShrinkDisk = 0;

      props.nodeList.forEach((nodeItem) => {
        if (nodeItem.isDataNode) {
          datanodeShrinkDisk += nodeItem.disk;
          datanodeList.push(nodeItem);
        }
      });
      nodeInfoMap.datanode.nodeList = datanodeList;
      nodeInfoMap.datanode.shrinkDisk = datanodeShrinkDisk;
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
  };

  defineExpose<Exposes>({
    submit() {
      return new Promise((resolve, reject) => {
        if (!nodeStatusListRef.value.validate()) {
          messageError(t('DataNode 缩容主机未填写'));
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
                {} as Record<string, TNodeInfo>,
              );

            createTicket({
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              details: {
                cluster_id: props.data.id,
                ext_info: generateExtInfo(),
                ip_source: 'resource_pool',
                old_nodes: {
                  [nodeType.value]: fomatHost(nodeInfoMap.datanode.nodeList),
                },
              },
              ticket_type: TicketTypes.HDFS_SHRINK,
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
  .hdfs-cluster-shrink-box {
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
