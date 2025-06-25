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

  import HdfsModel from '@services/model/hdfs/hdfs';
  import HdfsMachineModel from '@services/model/hdfs/hdfs-machine';
  import { getHdfsNodeList } from '@services/source/hdfs';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { TicketTypes } from '@common/const';

  import HostShrink, { type TShrinkNode } from '@views/db-manage/common/host-shrink/Index.vue';
  import NodeStatusList from '@views/db-manage/common/host-shrink/NodeStatusList.vue';

  import { messageError } from '@utils';

  interface Props {
    data: HdfsModel;
    machineList?: HdfsMachineModel[];
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
      key: 'datanode',
      label: 'DataNode',
    },
  ];

  const nodeStatusListRef = ref();
  const nodeInfoMap = reactive<Record<string, TShrinkNode>>({
    datanode: {
      hostList: [],
      label: 'DataNode',
      // 最小主机数
      minHost: 2,
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
    const datanodeOriginalNodeList: TShrinkNode['originalNodeList'] = [];

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
    () => props.machineList,
    () => {
      const datanodeList: TShrinkNode['hostList'] = [];

      let datanodeShrinkDisk = 0;

      props.machineList.forEach((machineItem) => {
        if (machineItem.isDataNode) {
          datanodeShrinkDisk += machineItem.host_info?.bk_disk || 0;
          datanodeList.push({
            alive: machineItem.host_info?.alive || 0,
            bk_cloud_id: machineItem.bk_cloud_id,
            bk_disk: machineItem.host_info.bk_disk,
            bk_host_id: machineItem.bk_host_id,
            ip: machineItem.ip,
          });
        }
      });
      nodeInfoMap.datanode.hostList = datanodeList;
      nodeInfoMap.datanode.shrinkDisk = datanodeShrinkDisk;
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
                  [nodeType.value]: fomatHost(nodeInfoMap.datanode.hostList),
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
