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
  <div class="es-cluster-replace-box">
    <template v-if="!isEmpty">
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
      <div
        v-show="nodeInfoMap.hot.nodeList.length > 0"
        class="item">
        <div class="item-label">
          {{ t('热节点') }}
        </div>
        <HostReplace
          ref="hotRef"
          v-model:host-list="nodeInfoMap.hot.hostList"
          v-model:node-list="nodeInfoMap.hot.nodeList"
          v-model:resource-spec="nodeInfoMap.hot.resourceSpec"
          :cloud-info="{
            id: data.bk_cloud_id,
            name: data.bk_cloud_name,
          }"
          :data="nodeInfoMap.hot"
          :disable-host-method="(hostData) => nodeDisableHostMethod(hostData, 'hot')"
          :ip-source="ipSource"
          @remove-node="handleRemoveNode" />
      </div>
      <div
        v-show="nodeInfoMap.cold.nodeList.length > 0"
        class="item">
        <div class="item-label">
          {{ t('冷节点') }}
        </div>
        <HostReplace
          ref="coldRef"
          v-model:host-list="nodeInfoMap.cold.hostList"
          v-model:node-list="nodeInfoMap.cold.nodeList"
          v-model:resource-spec="nodeInfoMap.cold.resourceSpec"
          :cloud-info="{
            id: data.bk_cloud_id,
            name: data.bk_cloud_name,
          }"
          :data="nodeInfoMap.cold"
          :disable-host-method="(hostData) => nodeDisableHostMethod(hostData, 'cold')"
          :ip-source="ipSource"
          @remove-node="handleRemoveNode" />
      </div>
      <div
        v-show="nodeInfoMap.client.nodeList.length > 0"
        class="item">
        <div class="item-label">
          {{ t('Client 节点') }}
        </div>
        <HostReplace
          ref="clientRef"
          v-model:host-list="nodeInfoMap.client.hostList"
          v-model:node-list="nodeInfoMap.client.nodeList"
          v-model:resource-spec="nodeInfoMap.client.resourceSpec"
          :cloud-info="{
            id: data.bk_cloud_id,
            name: data.bk_cloud_name,
          }"
          :data="nodeInfoMap.client"
          :disable-host-method="(hostData) => nodeDisableHostMethod(hostData, 'client')"
          :ip-source="ipSource"
          @remove-node="handleRemoveNode" />
      </div>
      <div
        v-show="nodeInfoMap.master.nodeList.length > 0"
        class="item">
        <div class="item-label">Master</div>
        <HostReplace
          ref="masterRef"
          v-model:host-list="nodeInfoMap.master.hostList"
          v-model:node-list="nodeInfoMap.master.nodeList"
          v-model:resource-spec="nodeInfoMap.master.resourceSpec"
          :cloud-info="{
            id: data.bk_cloud_id,
            name: data.bk_cloud_name,
          }"
          :data="nodeInfoMap.master"
          :disable-host-method="(hostData) => nodeDisableHostMethod(hostData, 'master')"
          :ip-source="ipSource"
          @remove-node="handleRemoveNode" />
      </div>
    </template>
    <div
      v-else
      class="node-empty">
      <BkException
        scene="part"
        type="empty">
        <template #description>
          <DbIcon type="attention" />
          <span>{{ t('请先返回列表选择要替换的节点 IP') }}</span>
        </template>
      </BkException>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { InfoBox } from 'bkui-vue';
  import { computed, reactive, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type EsModel from '@services/model/es/es';
  import { createTicket } from '@services/source/ticket';
  import type { HostInfo } from '@services/types';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import HostReplace, { type TReplaceNode } from '@views/db-manage/common/es-host-replace/Index.vue';

  import { messageError } from '@utils';

  interface Props {
    data: EsModel;
    nodeList: TReplaceNode['nodeList'];
  }

  interface Emits {
    (e: 'change'): void;
    (e: 'removeNode', bkHostId: number): void;
  }

  interface Exposes {
    submit: () => Promise<any>;
    cancel: () => Promise<any>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const makeMapByHostId = (hostList: TReplaceNode['hostList']) =>
    hostList.reduce(
      (result, item) => ({
        ...result,
        [item.host_id]: true,
      }),
      {} as Record<number, boolean>,
    );

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const hotRef = ref();
  const coldRef = ref();
  const clientRef = ref();
  const masterRef = ref();

  const ipSource = ref('resource_pool');
  const nodeInfoMap = reactive<Record<string, TReplaceNode>>({
    hot: {
      clusterId: props.data.id,
      role: 'es_datanode_hot',
      nodeList: [],
      hostList: [],
      specClusterType: ClusterTypes.ES,
      specMachineType: 'es_datanode',
      resourceSpec: {
        spec_id: 0,
        count: 0,
        instance_num: 1,
      },
    },
    cold: {
      clusterId: props.data.id,
      role: 'es_datanode_cold',
      nodeList: [],
      hostList: [],
      specClusterType: ClusterTypes.ES,
      specMachineType: 'es_datanode',
      resourceSpec: {
        spec_id: 0,
        count: 0,
        instance_num: 1,
      },
    },
    client: {
      clusterId: props.data.id,
      role: 'es_client',
      nodeList: [],
      hostList: [],
      specClusterType: ClusterTypes.ES,
      specMachineType: 'es_client',
      resourceSpec: {
        spec_id: 0,
        count: 0,
        instance_num: 1,
      },
    },
    master: {
      clusterId: props.data.id,
      role: 'es_master',
      nodeList: [],
      hostList: [],
      specClusterType: ClusterTypes.ES,
      specMachineType: 'es_master',
      resourceSpec: {
        spec_id: 0,
        count: 0,
        instance_num: 1,
      },
    },
  });

  const isEmpty = computed(() => {
    const { hot, cold, client, master } = nodeInfoMap;
    return (
      hot.nodeList.length < 1 && cold.nodeList.length < 1 && client.nodeList.length < 1 && master.nodeList.length < 1
    );
  });

  const disableTipsMap = {
    cold: t('主机已被冷节点使用'),
    client: t('主机已被 Client 节点使用'),
    hot: t('主机已被热节点使用'),
    master: t('主机已被 Master 节点使用'),
  };

  watch(
    () => props.nodeList,
    () => {
      const hotList: TReplaceNode['nodeList'] = [];
      const coldList: TReplaceNode['nodeList'] = [];
      const clientList: TReplaceNode['nodeList'] = [];
      const masterList: TReplaceNode['nodeList'] = [];

      props.nodeList.forEach((nodeItem) => {
        if (nodeItem.isHot) {
          hotList.push(nodeItem);
        } else if (nodeItem.isCold) {
          coldList.push(nodeItem);
        } else if (nodeItem.isClient) {
          clientList.push(nodeItem);
        } else if (nodeItem.isMaster) {
          masterList.push(nodeItem);
        }
      });

      nodeInfoMap.hot.nodeList = hotList;
      nodeInfoMap.cold.nodeList = coldList;
      nodeInfoMap.client.nodeList = clientList;
      nodeInfoMap.master.nodeList = masterList;
    },
    {
      immediate: true,
    },
  );

  // 节点主机互斥
  const nodeDisableHostMethod = (hostData: HostInfo, type: keyof typeof disableTipsMap) => {
    const types = Object.keys(disableTipsMap);
    for (const key of types) {
      if (key !== type) {
        const hostIdMap = makeMapByHostId(nodeInfoMap[key].hostList);
        if (hostIdMap[hostData.host_id]) {
          return disableTipsMap[key as keyof typeof disableTipsMap];
        }
      }
    }
    return false;
  };

  const handleRemoveNode = (node: TReplaceNode['nodeList'][0]) => {
    emits('removeNode', node.bk_host_id);
  };

  defineExpose<Exposes>({
    submit() {
      return new Promise((resolve, reject) => {
        if (isEmpty.value) {
          messageError(t('至少替换一种节点类型'));
          return reject(t('至少替换一种节点类型'));
        }

        Promise.all([
          hotRef.value.getValue(),
          coldRef.value.getValue(),
          clientRef.value.getValue(),
          masterRef.value.getValue(),
        ]).then(
          ([hotValue, coldValue, clientValue, masterValue]) => {
            const isEmptyValue = () => {
              if (ipSource.value === 'manual_input') {
                return (
                  hotValue.new_nodes.length +
                    coldValue.new_nodes.length +
                    clientValue.new_nodes.length +
                    masterValue.new_nodes.length <
                  1
                );
              }

              return !(
                (hotValue.resource_spec.spec_id > 0 && hotValue.resource_spec.count > 0) ||
                (coldValue.resource_spec.spec_id > 0 && coldValue.resource_spec.count > 0) ||
                (clientValue.resource_spec.spec_id > 0 && clientValue.resource_spec.count > 0) ||
                (masterValue.resource_spec.spec_id > 0 && masterValue.resource_spec.count > 0)
              );
            };

            if (isEmptyValue()) {
              messageError(t('替换节点不能为空'));
              return reject();
            }

            const getReplaceNodeNums = () => {
              if (ipSource.value === 'manual_input') {
                return Object.values(nodeInfoMap).reduce((result, nodeData) => result + nodeData.hostList.length, 0);
              }
              return Object.values(nodeInfoMap).reduce((result, nodeData) => {
                if (nodeData.resourceSpec.spec_id > 0) {
                  return result + nodeData.nodeList.length;
                }
                return result;
              }, 0);
            };

            InfoBox({
              title: t('确认替换n台节点IP', { n: getReplaceNodeNums() }),
              subTitle: t('替换后原节点 IP 将不在可用，资源将会被释放'),
              confirmText: t('确认'),
              cancelText: t('取消'),
              headerAlign: 'center',
              contentAlign: 'center',
              footerAlign: 'center',
              onCancel: () => reject(),
              onConfirm: () => {
                const nodeData = {};
                if (ipSource.value === 'manual_input') {
                  Object.assign(nodeData, {
                    new_nodes: {
                      hot: hotValue.new_nodes,
                      cold: coldValue.new_nodes,
                      client: clientValue.new_nodes,
                      master: masterValue.new_nodes,
                    },
                  });
                } else {
                  Object.assign(nodeData, {
                    resource_spec: {
                      hot: hotValue.resource_spec,
                      cold: coldValue.resource_spec,
                      client: clientValue.resource_spec,
                      master: masterValue.resource_spec,
                    },
                  });
                }
                createTicket({
                  ticket_type: 'ES_REPLACE',
                  bk_biz_id: currentBizId,
                  details: {
                    cluster_id: props.data.id,
                    ip_source: ipSource.value,
                    old_nodes: {
                      hot: hotValue.old_nodes,
                      cold: coldValue.old_nodes,
                      client: clientValue.old_nodes,
                      master: masterValue.old_nodes,
                    },
                    ...nodeData,
                  },
                }).then(() => {
                  emits('change');
                  resolve('success');
                });
              },
            });
          },
          () => reject('error'),
        );
      });
    },
    cancel() {
      return Promise.resolve();
    },
  });
</script>
<style lang="less">
  .es-cluster-replace-box {
    padding: 18px 43px 18px 37px;
    font-size: 12px;
    line-height: 20px;
    color: #63656e;

    .ip-srouce-box {
      display: flex;
      margin-bottom: 16px;

      .bk-radio-button {
        flex: 1;
        background: #fff;
      }
    }

    .item {
      & ~ .item {
        margin-top: 24px;
      }

      .item-label {
        margin-bottom: 6px;
        font-weight: bold;
        color: #313238;
      }
    }

    .node-empty {
      height: calc(100vh - 58px);
      padding-top: 168px;
    }
  }
</style>
