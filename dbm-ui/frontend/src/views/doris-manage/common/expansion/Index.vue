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
    class="doris-cluster-expansion-box"
    :loading="isLoading">
    <BkAlert
      class="mb16"
      theme="warning"
      :title="t('至少添加一种节点IP')" />
    <BkRadioGroup
      v-model="ipSource"
      class="ip-srouce-box">
      <BkRadioButton label="resource_pool">
        {{ t('资源池自动匹配') }}
      </BkRadioButton>
      <BkRadioButton label="manual_input">
        {{ t('手动选择') }}
      </BkRadioButton>
    </BkRadioGroup>
    <div class="content-wrapper">
      <NodeStatusList
        ref="nodeStatusListRef"
        v-model="nodeType"
        :ip-source="ipSource"
        :list="nodeStatusList"
        :node-info="nodeInfoMap" />
      <div class="node-panel">
        <template v-if="nodeType === 'observer'">
          <DorisObserverHostExpansion
            v-if="!isLoading"
            :key="nodeType"
            v-model:expansionDisk="nodeInfoMap[nodeType].expansionDisk"
            v-model:hostList="nodeInfoMap[nodeType].hostList"
            v-model:resourceSpec="nodeInfoMap[nodeType].resourceSpec"
            v-model:targetDisk="nodeInfoMap[nodeType].targetDisk"
            :cloud-info="{
              id: data.bk_cloud_id,
              name: data.bk_cloud_name,
            }"
            :data="nodeInfoMap[nodeType]"
            :disable-host-method="(data: HostDetails) => disableHostMethod(data, nodeInfoMap[nodeType].mutexNodeTypes)"
            :ip-source="ipSource" />
        </template>
        <template v-else>
          <HostExpansion
            v-if="!isLoading"
            :key="nodeType"
            v-model:expansionDisk="nodeInfoMap[nodeType].expansionDisk"
            v-model:hostList="nodeInfoMap[nodeType].hostList"
            v-model:resourceSpec="nodeInfoMap[nodeType].resourceSpec"
            v-model:targetDisk="nodeInfoMap[nodeType].targetDisk"
            :cloud-info="{
              id: data.bk_cloud_id,
              name: data.bk_cloud_name,
            }"
            :data="nodeInfoMap[nodeType]"
            :disable-host-method="(data: HostDetails) => disableHostMethod(data, nodeInfoMap[nodeType].mutexNodeTypes)"
            :ip-source="ipSource" />
        </template>
      </div>
    </div>
  </BkLoading>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import type DorisModel from '@services/model/doris/doris';
  import { getHostDetails } from '@services/source/ipchooser';
  import { createTicket } from '@services/source/ticket';
  import type { HostDetails } from '@services/types';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    ClusterTypes,
    TicketTypes
  } from '@common/const';

  import DorisObserverHostExpansion from '@components/cluster-common/doris-observer-host-expansion/Index.vue';
  import HostExpansion, {
    type TExpansionNode,
  } from '@components/cluster-common/host-expansion/Index.vue';
  import NodeStatusList from '@components/cluster-common/host-expansion/NodeStatusList.vue';

  import { messageError } from '@utils';

  interface TDorisExpansionNode extends TExpansionNode {
    mutexNodeTypes: ('hot' | 'cold' | 'observer')[]
  }

  interface Props {
    data: DorisModel,
  }

  interface Emits {
    (e: 'change'): void
  }

  interface Exposes {
    submit: () => Promise<any>
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const makeMapByHostId = (hostList: TExpansionNode['hostList'] = []) => hostList.reduce((result, item) => ({
    ...result,
    [item.host_id]: true,
  }), {} as Record<number, boolean>);

  // TODO 替换为doris数据
  const generateNodeInfo = (values: Pick<TDorisExpansionNode, 'label' | 'role' | 'specMachineType' | 'tagText' | 'mutexNodeTypes'>): TDorisExpansionNode => ({
    ...values,
    clusterId: props.data.id,
    originalHostList: [],
    ipSource: 'resource_pool',
    hostList: [],
    totalDisk: 0,
    targetDisk: 0,
    expansionDisk: 0,
    specClusterType: ClusterTypes.ES,
    resourceSpec: {
      spec_id: 0,
      count: 1,
    },
  })

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
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
      label: t('Observer节点'),
    },
  ];

  // TODO 替换为doris数据
  const nodeInfoMap = reactive<Record<string, TDorisExpansionNode>>({
    hot: generateNodeInfo({
      label: t('热节点'),
      role: 'es_datanode_hot',
      specMachineType: 'es_datanode',
      tagText: t('存储层'),
      mutexNodeTypes: ['cold', 'observer']
    }),
    cold: generateNodeInfo({
      label: t('冷节点'),
      role: 'es_datanode_cold',
      specMachineType: 'es_datanode',
      tagText: t('存储层'),
      mutexNodeTypes: ['hot', 'observer']
    }),
    observer: generateNodeInfo({
      label: t('Observer节点'),
      role: 'es_datanode_hot',
      specMachineType: 'es_datanode',
      tagText: t('接入层'),
      mutexNodeTypes: ['hot', 'cold']
    })
  });

  const nodeStatusListRef = ref<InstanceType<typeof NodeStatusList>>();
  const isLoading = ref(false);
  const ipSource = ref('resource_pool');
  const nodeType = ref('cold');

  // 获取主机详情
  const fetchHostDetail = () => {
    const hotHostIdMap = props.data.doris_datanode_hot.reduce((result, item) => ({
      ...result,
      [item.bk_host_id]: true,
    }), {} as Record<number, boolean>);
    const coldHostIdMap = props.data.doris_datanode_cold.reduce((result, item) => ({
      ...result,
      [item.bk_host_id]: true,
    }), {} as Record<number, boolean>);

    const hostIdList = [
      ...props.data.doris_datanode_hot,
      ...props.data.doris_datanode_cold,
    ].map(item => ({
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
        scope_id: currentBizId,
        scope_type: 'biz',
      }],
    }).then((data) => {
      const hotOriginalHostList: HostDetails[] = [];
      const coldOriginalHostList: HostDetails[] = [];

      let hotDiskTotal = 0;
      let coldDiskTotal = 0;

      data.forEach((hostItem) => {
        if (hotHostIdMap[hostItem.host_id]) {
          hotDiskTotal += Math.floor(Number(hostItem.bk_disk));
          hotOriginalHostList.push(hostItem);
        }
        if (coldHostIdMap[hostItem.host_id]) {
          coldDiskTotal += Math.floor(Number(hostItem.bk_disk));
          coldOriginalHostList.push(hostItem);
        }
      });

      nodeInfoMap.hot.totalDisk = hotDiskTotal;
      nodeInfoMap.hot.originalHostList = hotOriginalHostList;

      nodeInfoMap.cold.totalDisk = coldDiskTotal;
      nodeInfoMap.cold.originalHostList = coldOriginalHostList;
    })
      .finally(() => {
        isLoading.value = false;
      });
  };

  fetchHostDetail();

  // 主机节点互斥
  const disableHostMethod = (data: HostDetails, mutexNodeTypes: ('observer' | 'hot' | 'cold')[]) => {
    const tipMap = {
      'observer': t('主机已被Observer节点使用'),
      'hot': t('主机已被热节点使用'),
      'cold': t('主机已被冷节点使用')
    }

    for (const mutexNodeType of mutexNodeTypes) {
      const hostMap = makeMapByHostId(nodeInfoMap[mutexNodeType].hostList);
      if (hostMap[data.host_id]) {
        return tipMap[mutexNodeType];
      }
    }
    return false
  }

  // 扩容主机节点互斥
  // const disableHostMethod = (hostData: TExpansionNode['originalHostList'][0]) => {
  //   const hotDisableHostMethod = (hostData: TExpansionNode['originalHostList'][0]) => {
  //     const coldHostIdMap = makeMapByHostId(nodeInfoMap.cold.hostList);
  //     if (coldHostIdMap[hostData.host_id]) {
  //       return t('主机已被xx节点使用', ['冷']);
  //     }
  //     const observerHostIdMap = makeMapByHostId(nodeInfoMap.observer.hostList);
  //     if (observerHostIdMap[hostData.host_id]) {
  //       return t('主机已被xx节点使用', ['Observer']);
  //     }
  //     return false;
  //   };
  //   const coldDisableHostMethod = (hostData: TExpansionNode['originalHostList'][0]) => {
  //     const hotHostIdMap = makeMapByHostId(nodeInfoMap.hot.hostList);
  //     if (hotHostIdMap[hostData.host_id]) {
  //       return t('主机已被xx节点使用', ['热']);
  //     }
  //     const observerHostIdMap = makeMapByHostId(nodeInfoMap.observer.hostList);
  //     if (observerHostIdMap[hostData.host_id]) {
  //       return t('主机已被xx节点使用', ['Observer']);
  //     }
  //     return false;
  //   };
  //   const observerDisableHostMethod = (hostData: TExpansionNode['originalHostList'][0]) => {
  //     const hotHostIdMap = makeMapByHostId(nodeInfoMap.hot.hostList);
  //     if (hotHostIdMap[hostData.host_id]) {
  //       return t('主机已被xx节点使用', ['热']);
  //     }
  //     const coldHostIdMap = makeMapByHostId(nodeInfoMap.cold.hostList);
  //     if (coldHostIdMap[hostData.host_id]) {
  //       return t('主机已被xx节点使用', ['冷']);
  //     }
  //     return false;
  //   };

  //   if (nodeType.value === 'hot') {
  //     return hotDisableHostMethod(hostData);
  //   }
  //   if (nodeType.value === 'cold') {
  //     return coldDisableHostMethod(hostData);
  //   }
  //   if (nodeType.value === 'observer') {
  //     return observerDisableHostMethod(hostData);
  //   }

  //   return false;
  // };

  defineExpose<Exposes>({
    submit() {
      if (!nodeStatusListRef.value!.validate()) {
        messageError(t('至少添加一种节点IP'));
        return Promise.reject();
      }

      const renderSubTitle = () => {
        const renderDiskTips = () => {
          const isNotMatch = Object.values(nodeInfoMap)
            .some(nodeData => nodeData.targetDisk > 0
              && nodeData.totalDisk + nodeData.expansionDisk !== nodeData.targetDisk);
          if (isNotMatch) {
            return (
              <>
                <div>{t('目标容量与所选 IP 容量不一致，确认提交？')}</div>
                <div class="mb-4">{t('继续提交将按照手动选择的 IP 容量进行')}</div>
              </>
            );
          }
          return null;
        };
        const renderExpansionDiskTips = () => Object.values(nodeInfoMap).map((nodeData) => {
          if (nodeData.expansionDisk) {
            // TODO 替换为doris数据
            if (nodeData.specMachineType === 'es_client') {
              return (
                <div>
                  {t('name容量从n台扩容至n台', {
                    name: nodeData.label,
                    hostNumBefore: nodeData.originalHostList.length,
                    hostNumAfter: nodeData.resourceSpec.count + nodeData.originalHostList.length,
                  })}
                </div>
              );
            }
            return (
              <div>
                {t('name容量从nG扩容至nG', {
                  name: nodeData.label,
                  totalDisk: nodeData.totalDisk,
                  expansionDisk: nodeData.totalDisk + nodeData.expansionDisk,
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
              <div>
                {t('集群')} :
                <span
                  style="color: #313238"
                  class="ml-8">
                  {props.data.cluster_name}
                </span>
              </div>
              {renderExpansionDiskTips()}
            </div>
          </div>
        );
      };

      return new Promise((resolve, reject) => {
        InfoBox({
          title: t('确认扩容集群？'),
          subTitle: renderSubTitle,
          confirmText: t('确认'),
          cancelText: t('取消'),
          headerAlign: 'center',
          contentAlign: 'left',
          footerAlign: 'center',
          onClosed: () => reject(),
          onConfirm: () => {
            const hostData = {};

            const generateExtInfo = () => Object.entries(nodeInfoMap).reduce((results, [key, item]) => {
              const obj = {
                host_list: item.hostList,
                total_hosts: item.originalHostList.length,
                total_disk: item.totalDisk,
                target_disk: item.targetDisk,
                expansion_disk: item.expansionDisk,
              };
              Object.assign(results, {
                [key]: obj,
              });
              return results;
            }, {} as Record<string, TExpansionNode>);

            if (ipSource.value === 'manual_input') {
              const fomatHost = (hostList: TExpansionNode['hostList'] = []) => hostList.map(hostItem => ({
                ip: hostItem.ip,
                bk_cloud_id: hostItem.cloud_id,
                bk_host_id: hostItem.host_id,
                bk_biz_id: hostItem.meta.bk_biz_id,
              }));
              Object.assign(hostData, {
                nodes: {
                  hot: fomatHost(nodeInfoMap.hot.hostList),
                  cold: fomatHost(nodeInfoMap.cold.hostList),
                  observer: fomatHost(nodeInfoMap.observer.hostList)
                },
              });
            } else {
              const resourceSpec = {};
              if (nodeInfoMap.hot.resourceSpec.spec_id > 0 && nodeInfoMap.hot.resourceSpec.count > 0) {
                Object.assign(resourceSpec, {
                  hot: nodeInfoMap.hot.resourceSpec,
                });
              }
              if (nodeInfoMap.cold.resourceSpec.spec_id > 0 && nodeInfoMap.cold.resourceSpec.count > 0) {
                Object.assign(resourceSpec, {
                  cold: nodeInfoMap.cold.resourceSpec,
                });
              }
              if (nodeInfoMap.observer.resourceSpec.spec_id > 0 && nodeInfoMap.observer.resourceSpec.count > 0) {
                Object.assign(resourceSpec, {
                  observer: nodeInfoMap.observer.resourceSpec,
                });
              }
              Object.assign(hostData, {
                resource_spec: resourceSpec,
              });
            }

            createTicket({
              bk_biz_id: currentBizId,
              ticket_type: TicketTypes.DORIS_SCALE_UP,
              details: {
                ip_source: ipSource.value,
                cluster_id: props.data.id,
                ...hostData,
                ext_info: generateExtInfo(),
              },
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
        });
      });
    },
  });
</script>

<style lang="less" scoped>
  .doris-cluster-expansion-box {
    padding: 18px 43px 18px 37px;
    font-size: 12px;
    line-height: 20px;
    color: #63656e;
    background: #f5f7fa;

    .ip-srouce-box {
      display: flex;
      margin-bottom: 16px;

      .bk-radio-button {
        flex: 1;
        background: #fff;
      }
    }

    .content-wrapper {
      display: flex;
      background: #fff;
      border-radius: 2px;
      box-shadow: 0 2px 4px 0 #1919290d;

      .node-panel {
        flex: 1;
      }
    }
  }
</style>
