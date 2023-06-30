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
    class="hdfs-cluster-expansion-box"
    :loading="isLoading">
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
    <div class="wrapper">
      <NodeStatusList
        v-show="false"
        ref="nodeStatusListRef"
        v-model="nodeType"
        :ip-source="ipSource"
        :list="nodeStatusList"
        :node-info="nodeInfoMap" />
      <div class="node-panel">
        <HostExpansion
          v-if="!isLoading"
          :key="nodeType"
          v-model:expansionDisk="nodeInfoMap[nodeType].expansionDisk"
          v-model:hostList="nodeInfoMap[nodeType].hostList"
          v-model:resourceSpec="nodeInfoMap[nodeType].resourceSpec"
          v-model:targetDisk="nodeInfoMap[nodeType].targetDisk"
          :cloud-info="{
            id: data.bk_cloud_id,
            name: data.bk_cloud_name
          }"
          :data="nodeInfoMap[nodeType]"
          :ip-source="ipSource" />
      </div>
    </div>
  </BkLoading>
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import {
    reactive,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getHostDetails } from '@services/ip';
  import type HdfsModel from '@services/model/hdfs/hdfs';
  import { createTicket } from '@services/ticket';
  import type { HostDetails } from '@services/types/ip';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import HostExpansion, {
    type TExpansionNode,
  } from '@components/cluster-common/host-expansion/Index.vue';
  import NodeStatusList from '@components/cluster-common/host-expansion/NodeStatusList.vue';

  import { messageError } from '@utils';


  interface Props {
    data: HdfsModel,
  }

  interface Emits {
    (e: 'change'): void
  }

  interface Exposes {
    submit: () => Promise<any>
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const bizId = globalBizsStore.currentBizId;

  const nodeStatusList = [
    {
      key: 'datanode',
      label: 'DataNode',
    },
  ];

  const nodeInfoMap = reactive<Record<string, TExpansionNode>>({
    datanode: {
      label: 'Datanode',
      clusterId: props.data.id,
      role: 'hdfs_datanode',
      originalHostList: [],
      ipSource: 'resource_pool',
      hostList: [],
      totalDisk: 0,
      targetDisk: 0,
      expansionDisk: 0,
      specClusterType: ClusterTypes.HDFS,
      specMachineType: 'hdfs_datanode',
      resourceSpec: {
        spec_id: 0,
        count: 0,
      },
    },
  });

  const nodeStatusListRef = ref();
  const isLoading = ref(false);
  const ipSource = ref('resource_pool');
  const nodeType = ref('datanode');

  // 获取主机详情
  const fetchHostDetail = () => {
    const datanodeHostIdMap = props.data.hdfs_datanode.reduce((result, item) => ({
      ...result,
      [item.bk_host_id]: true,
    }), {} as Record<number, boolean>);

    const hostIdList = props.data.hdfs_datanode.map(item => ({
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
      const datanodeOriginalHostList: HostDetails[] = [];

      let datanodeDiskTotal = 0;

      data.forEach((hostItem) => {
        if (datanodeHostIdMap[hostItem.host_id]) {
          datanodeDiskTotal += ~~Number(hostItem.bk_disk);
          datanodeOriginalHostList.push(hostItem);
        }
      });

      nodeInfoMap.datanode.totalDisk = datanodeDiskTotal;
      nodeInfoMap.datanode.originalHostList = datanodeOriginalHostList;
    })
      .finally(() => {
        isLoading.value = false;
      });
  };

  fetchHostDetail();

  defineExpose<Exposes>({
    submit() {
      if (!nodeStatusListRef.value.validate()) {
        messageError(t('Datanode 扩容主机未填写'));
        return Promise.reject();
      }

      const renderSubTitle = () => {
        const renderDiskTips = () => {
          const isNotMatch = Object.values(nodeInfoMap)
            .some(nodeData => nodeData.totalDisk + nodeData.expansionDisk !== nodeData.targetDisk);
          if (isNotMatch) {
            return (
                <>
                  <div>{t('目标容量与所选 IP 容量不一致，确认提交？')}</div>
                  <div>{t('继续提交将按照手动选择的 IP 容量进行')}</div>
                </>
            );
          }
          return null;
        };
        const renderExpansionDiskTips = () => Object.values(nodeInfoMap).map((nodeData) => {
          if (nodeData.expansionDisk) {
            return (
              <div>
                {t('name容量从nG扩容至nG', {
                  name: nodeData.label,
                  totalDisk: nodeData.totalDisk,
                  expansionDisk: nodeData.expansionDisk,
                })}
              </div>
            );
          }
          return null;
        });

        return (
          <div style="font-size: 14px; line-height: 28px; color: #63656E;">
            {renderDiskTips()}
            {renderExpansionDiskTips()}
          </div>
        );
      };

      return new Promise((resolve, reject) => {
        InfoBox({
          title: t('确认扩容【name】集群', { name: props.data.cluster_name }),
          subTitle: renderSubTitle,
          confirmText: t('确认'),
          cancelText: t('取消'),
          headerAlign: 'center',
          contentAlign: 'center',
          footerAlign: 'center',
          onClosed: () => reject(),
          onConfirm: () => {
            const hostData = {};

            if (ipSource.value === 'manual_input') {
              const fomatHost = (hostList: TExpansionNode['hostList'] = []) => hostList.map(hostItem => ({
                ip: hostItem.ip,
                bk_cloud_id: hostItem.cloud_id,
                bk_host_id: hostItem.host_id,
                bk_biz_id: hostItem.meta.bk_biz_id,
              }));
              Object.assign(hostData, {
                nodes: {
                  datanode: fomatHost(nodeInfoMap.datanode.hostList),
                },
              });
            } else {
              Object.assign(hostData, {
                resource_spec: {
                  datanode: nodeInfoMap.datanode.resourceSpec,
                },
              });
            }

            createTicket({
              bk_biz_id: bizId,
              ticket_type: 'HDFS_SCALE_UP',
              details: {
                ip_source: ipSource.value,
                cluster_id: props.data.id,
                ...hostData,
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
  .hdfs-cluster-expansion-box {
    padding: 18px 43px 18px 37px;
    font-size: 12px;
    line-height: 20px;
    color: #63656e;
    background: #f5f7fa;

    .ip-srouce-box{
      display: flex;
      margin-bottom: 16px;

      .bk-radio-button{
        flex: 1;
        background: #fff;
      }
    }

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
