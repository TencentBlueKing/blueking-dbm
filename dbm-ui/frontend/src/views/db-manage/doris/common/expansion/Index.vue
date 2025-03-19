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
        <HostExpansion
          v-if="!isLoading"
          :key="nodeType"
          v-model:expansion-disk="nodeInfoMap[nodeType].expansionDisk"
          v-model:host-list="nodeInfoMap[nodeType].hostList"
          v-model:resource-spec="nodeInfoMap[nodeType].resourceSpec"
          :cloud-info="{
            id: data.bk_cloud_id,
            name: data.bk_cloud_name,
          }"
          :data="nodeInfoMap[nodeType]"
          :db-type="DBTypes.DORIS"
          :disable-host-method="(data: HostInfo) => disableHostMethod(data, nodeInfoMap[nodeType].mutexNodeTypes)"
          :ip-source="ipSource" />
      </div>
    </div>
  </BkLoading>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import DorisModel from '@services/model/doris/doris';
  import DorisMachineModel from '@services/model/doris/doris-machine';
  import { getDorisMachineList } from '@services/source/doris';
  import { createTicket } from '@services/source/ticket';
  import type { HostInfo } from '@services/types';

  import { useTicketMessage } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import HostExpansion, { type TExpansionNode } from '@views/db-manage/common/host-expansion/Index.vue';
  import NodeStatusList from '@views/db-manage/common/host-expansion/NodeStatusList.vue';

  import { messageError } from '@utils';

  interface TDorisExpansionNode extends TExpansionNode {
    mutexNodeTypes: ('hot' | 'cold' | 'observer')[];
  }

  interface Props {
    data: DorisModel;
  }

  type Emits = (e: 'change') => void;

  interface Exposes {
    submit: () => Promise<any>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const makeMapByHostId = (hostList: TExpansionNode['hostList'] = []) =>
    hostList.reduce(
      (result, item) => ({
        ...result,
        [item.bk_host_id]: true,
      }),
      {} as Record<number, boolean>,
    );

  const generateNodeInfo = (
    values: Pick<
      TDorisExpansionNode,
      'label' | 'role' | 'specMachineType' | 'tagText' | 'mutexNodeTypes' | 'showCount'
    >,
  ): TDorisExpansionNode => ({
    ...values,
    clusterId: props.data.id,
    // targetDisk: 0,
    expansionDisk: 0,
    hostList: [],
    ipSource: 'resource_pool',
    originalHostList: [],
    resourceSpec: {
      count: 0,
      spec_id: 0,
    },
    specClusterType: ClusterTypes.DORIS,
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
      label: t('Observer节点'),
    },
  ];

  const nodeInfoMap = reactive<Record<string, TDorisExpansionNode>>({
    cold: generateNodeInfo({
      label: t('冷节点'),
      mutexNodeTypes: ['hot', 'observer'],
      role: 'doris_backend_cold',
      specMachineType: 'doris_backend',
      tagText: t('存储层'),
    }),
    hot: generateNodeInfo({
      label: t('热节点'),
      mutexNodeTypes: ['cold', 'observer'],
      role: 'doris_backend_hot',
      specMachineType: 'doris_backend',
      tagText: t('存储层'),
    }),
    observer: generateNodeInfo({
      label: t('Observer节点'),
      mutexNodeTypes: ['hot', 'cold'],
      role: 'doris_observer',
      showCount: true,
      specMachineType: 'doris_observer',
      tagText: t('接入层'),
    }),
  });

  const nodeStatusListRef = ref<InstanceType<typeof NodeStatusList>>();
  const isLoading = ref(false);
  const ipSource = ref('resource_pool');
  const nodeType = ref('cold');

  // 获取主机详情
  const fetchHostDetail = () => {
    isLoading.value = true;

    getDorisMachineList({
      cluster_ids: String(props.data.id),
      limit: -1,
      offset: 0,
    })
      .then((data) => {
        const hotOriginalHostList: DorisMachineModel[] = [];
        const coldOriginalHostList: DorisMachineModel[] = [];
        const observerOriginalHostList: DorisMachineModel[] = [];

        let hotDiskTotal = 0;
        let coldDiskTotal = 0;
        let observerDiskTotal = 0;

        data.results.forEach((hostItem) => {
          if (hostItem.isHot) {
            hotDiskTotal += Math.floor(Number(hostItem.host_info.bk_disk));
            hotOriginalHostList.push(hostItem);
          } else if (hostItem.isCold) {
            coldDiskTotal += Math.floor(Number(hostItem.host_info.bk_disk));
            coldOriginalHostList.push(hostItem);
          } else if (hostItem.isObserver) {
            observerDiskTotal += Math.floor(Number(hostItem.host_info.bk_disk));
            observerOriginalHostList.push(hostItem);
          }
        });

        nodeInfoMap.hot.totalDisk = hotDiskTotal;
        nodeInfoMap.hot.originalHostList = hotOriginalHostList;

        nodeInfoMap.cold.totalDisk = coldDiskTotal;
        nodeInfoMap.cold.originalHostList = coldOriginalHostList;

        nodeInfoMap.observer.totalDisk = observerDiskTotal;
        nodeInfoMap.observer.originalHostList = observerOriginalHostList;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  fetchHostDetail();

  // 主机节点互斥
  const disableHostMethod = (data: HostInfo, mutexNodeTypes: ('observer' | 'hot' | 'cold')[]) => {
    const tipMap = {
      cold: t('主机已被冷节点使用'),
      hot: t('主机已被热节点使用'),
      observer: t('主机已被Observer节点使用'),
    };

    for (const mutexNodeType of mutexNodeTypes) {
      const hostMap = makeMapByHostId(nodeInfoMap[mutexNodeType].hostList);
      if (hostMap[data.host_id]) {
        return tipMap[mutexNodeType];
      }
    }
    return false;
  };

  defineExpose<Exposes>({
    submit() {
      if (!nodeStatusListRef.value!.validate()) {
        messageError(t('至少添加一种节点IP'));
        return Promise.reject();
      }

      const renderSubTitle = () => {
        const renderExpansionDiskTips = () =>
          Object.values(nodeInfoMap).map((nodeData) => {
            if (nodeData.showCount) {
              const expansionCount =
                ipSource.value === 'resource_pool' ? nodeData.resourceSpec.count : nodeData.hostList.length;
              if (expansionCount) {
                return (
                  <div class='tips-item'>
                    {t('name容量从n台扩容至n台', {
                      hostNumAfter: expansionCount + nodeData.originalHostList.length,
                      hostNumBefore: nodeData.originalHostList.length,
                      name: nodeData.label,
                    })}
                  </div>
                );
              }
            } else {
              if (nodeData.expansionDisk) {
                return (
                  <div class='tips-item'>
                    {t('name容量从nG扩容至nG', {
                      expansionDisk: nodeData.totalDisk + nodeData.expansionDisk,
                      name: nodeData.label,
                      totalDisk: nodeData.totalDisk,
                    })}
                  </div>
                );
              }
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
            {renderExpansionDiskTips()}
          </div>
        );
      };

      return new Promise((resolve, reject) => {
        InfoBox({
          cancelText: t('取消'),
          confirmText: t('确认'),
          contentAlign: 'left',
          extCls: 'doris-expansion-modal',
          footerAlign: 'center',
          headerAlign: 'center',
          onClose: () => reject(),
          onConfirm: () => {
            const hostData = {};

            const generateExtInfo = () =>
              Object.entries(nodeInfoMap).reduce(
                (results, [key, item]) => {
                  Object.assign(results, {
                    [key]: {
                      expansion_disk: item.expansionDisk,
                      total_disk: item.totalDisk,
                      total_hosts: item.originalHostList.length,
                    },
                  });
                  return results;
                },
                {} as Record<string, TExpansionNode>,
              );

            if (ipSource.value === 'manual_input') {
              const formatHost = (hostList: TExpansionNode['hostList'] = []) => {
                const hosts = hostList.map((hostItem) => ({
                  bk_biz_id: hostItem.dedicated_biz,
                  bk_cloud_id: hostItem.bk_cloud_id,
                  bk_disk: hostItem.bk_disk,
                  bk_host_id: hostItem.bk_host_id,
                  ip: hostItem.ip,
                }));
                return {
                  count: hostList.length,
                  hosts,
                  spec_id: 0,
                };
              };
              Object.assign(hostData, {
                resource_spec: {
                  cold: formatHost(nodeInfoMap.cold.hostList),
                  hot: formatHost(nodeInfoMap.hot.hostList),
                  observer: formatHost(nodeInfoMap.observer.hostList),
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
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              details: {
                cluster_id: props.data.id,
                ext_info: generateExtInfo(),
                ip_source: 'resource_pool',
                ...hostData,
              },
              ticket_type: TicketTypes.DORIS_SCALE_UP,
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
          title: t('确认扩容集群？'),
        });
      });
    },
  });
</script>

<style lang="less">
  .doris-expansion-modal {
    .bk-modal-content div {
      font-size: 14px;
    }

    .tips-item {
      padding: 2px 0;
    }
  }
</style>
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
