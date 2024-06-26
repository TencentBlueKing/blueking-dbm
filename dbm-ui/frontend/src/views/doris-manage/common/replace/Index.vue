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
  <div class="doris-cluster-replace-box">
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
        class="replace-item">
        <div class="item-label">
          {{ t('热节点') }}
        </div>
        <HostReplace
          ref="hotRef"
          v-model:hostList="nodeInfoMap.hot.hostList"
          v-model:nodeList="nodeInfoMap.hot.nodeList"
          v-model:resourceSpec="nodeInfoMap.hot.resourceSpec"
          :cloud-info="{
            id: data.bk_cloud_id,
            name: data.bk_cloud_name,
          }"
          :data="nodeInfoMap.hot"
          :disable-host-method="(data: HostDetails) => disableHostMethod(data, ['observer', 'follower', 'cold'])"
          :ip-source="ipSource"
          @remove-node="handleRemoveNode" />
      </div>
      <div
        v-show="nodeInfoMap.cold.nodeList.length > 0"
        class="replace-item">
        <div class="item-label">
          {{ t('冷节点') }}
        </div>
        <HostReplace
          ref="coldRef"
          v-model:hostList="nodeInfoMap.cold.hostList"
          v-model:nodeList="nodeInfoMap.cold.nodeList"
          v-model:resourceSpec="nodeInfoMap.cold.resourceSpec"
          :cloud-info="{
            id: data.bk_cloud_id,
            name: data.bk_cloud_name,
          }"
          :data="nodeInfoMap.cold"
          :disable-host-method="(data: HostDetails) => disableHostMethod(data, ['observer', 'follower', 'hot'])"
          :ip-source="ipSource"
          @remove-node="handleRemoveNode" />
      </div>
      <div
        v-show="nodeInfoMap.observer.nodeList.length > 0"
        class="replace-item">
        <div class="item-label">
          {{ t('Observer节点') }}
        </div>
        <HostReplace
          ref="observerRef"
          v-model:hostList="nodeInfoMap.observer.hostList"
          v-model:nodeList="nodeInfoMap.observer.nodeList"
          v-model:resourceSpec="nodeInfoMap.observer.resourceSpec"
          :cloud-info="{
            id: data.bk_cloud_id,
            name: data.bk_cloud_name,
          }"
          :data="nodeInfoMap.observer"
          :disable-host-method="(data: HostDetails) => disableHostMethod(data, ['follower', 'hot', 'cold'])"
          :ip-source="ipSource"
          @remove-node="handleRemoveNode" />
      </div>
      <div
        v-show="nodeInfoMap.follower.nodeList.length > 0"
        class="replace-item">
        <div class="item-label">
          {{ t('Follower节点') }}
        </div>
        <HostReplace
          ref="followerRef"
          v-model:hostList="nodeInfoMap.follower.hostList"
          v-model:nodeList="nodeInfoMap.follower.nodeList"
          v-model:resourceSpec="nodeInfoMap.follower.resourceSpec"
          :cloud-info="{
            id: data.bk_cloud_id,
            name: data.bk_cloud_name,
          }"
          :data="nodeInfoMap.follower"
          :disable-host-method="(data: HostDetails) => disableHostMethod(data, ['observer', 'hot', 'cold'])"
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

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import type { ComponentExposed } from 'vue-component-type-helpers'
  import { useI18n } from 'vue-i18n';

  import DorisModel from '@services/model/doris/doris';
  import DorisNodeModel from '@services/model/doris/doris-node';
  import { createTicket } from '@services/source/ticket';
  import type { HostDetails } from '@services/types';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    ClusterTypes,
    TicketTypes
  } from '@common/const';

  import HostReplace, {
    type TReplaceNode,
  } from '@components/cluster-common/host-replace/Index.vue';

  import { messageError } from '@utils';

  type ReplaceNode = TReplaceNode<DorisNodeModel>

  interface Props {
    data: DorisModel,
    nodeList: ReplaceNode['nodeList']
  }

  interface Emits {
    (e: 'change'): void,
    (e: 'removeNode', bkHostId: number): void
  }

  interface Exposes {
    submit: () => Promise<any>,
    cancel: () => Promise<any>,
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const makeMapByHostId = (hostList: ReplaceNode['hostList']) =>  hostList.reduce((result, item) => ({
    ...result,
    [item.host_id]: true,
  }), {} as Record<number, boolean>);

  const generateNodeInfo = (values: Pick<ReplaceNode, 'role' | 'specMachineType'>): ReplaceNode => ({
    ...values,
    clusterId: props.data.id,
    nodeList: [],
    hostList: [],
    specClusterType: ClusterTypes.DORIS,
    resourceSpec: {
      spec_id: 0,
      count: 0,
    },
  })

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const hotRef = ref<ComponentExposed<typeof HostReplace>>();
  const coldRef = ref<ComponentExposed<typeof HostReplace>>();
  const observerRef = ref<ComponentExposed<typeof HostReplace>>();
  const followerRef = ref<ComponentExposed<typeof HostReplace>>();
  const ipSource = ref('resource_pool');

  const nodeInfoMap = reactive<Record<string, ReplaceNode>>({
    hot: generateNodeInfo({
      role: 'doris_backend_hot',
      specMachineType: 'doris_backend',
    }),
    cold: generateNodeInfo({
      role: 'doris_backend_cold',
      specMachineType: 'doris_backend',
    }),
    observer: generateNodeInfo({
      role: 'doris_observer',
      specMachineType: 'doris_observer',
    }),
    follower: generateNodeInfo({
      role: 'doris_follower',
      specMachineType: 'doris_follower',
    }),
  });

  const isEmpty = computed(() => {
    const {
      hot,
      cold,
      observer,
      follower
    } = nodeInfoMap;
    return hot.nodeList.length < 1
      && cold.nodeList.length < 1
      && observer.nodeList.length < 1
      && follower.nodeList.length < 1;
  });

  watch(() => props.nodeList, () => {
    const hotList: ReplaceNode['nodeList'] = [];
    const coldList: ReplaceNode['nodeList'] = [];
    const observerList: ReplaceNode['nodeList'] = [];
    const followerList: ReplaceNode['nodeList'] = [];

    props.nodeList.forEach((nodeItem) => {
      if (nodeItem.isHot) {
        hotList.push(nodeItem);
      } else if (nodeItem.isCold) {
        coldList.push(nodeItem);
      } else if (nodeItem.isObserver) {
        observerList.push(nodeItem);
      } else if (nodeItem.isFollower) {
        followerList.push(nodeItem);
      }
    });

    nodeInfoMap.hot.nodeList = hotList;
    nodeInfoMap.cold.nodeList = coldList;
    nodeInfoMap.observer.nodeList = observerList;
    nodeInfoMap.follower.nodeList = followerList;
  }, {
    immediate: true,
  });

  // 主机节点互斥
  const disableHostMethod = (data: HostDetails, mutexNodeTypes: ('follower' | 'observer' | 'hot' | 'cold')[]) => {
    const tipMap = {
      'follower': t('主机已被Follower节点使用'),
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

  const handleRemoveNode = (node: ReplaceNode['nodeList'][0]) => {
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
          hotRef.value!.getValue(),
          coldRef.value!.getValue(),
          observerRef.value!.getValue(),
          followerRef.value!.getValue()
        ]).then(([hotValue, coldValue, observerValue, followerValue]) => {
          const isEmptyValue = () => {
            if (ipSource.value === 'manual_input') {
              return hotValue.new_nodes.length
                + coldValue.new_nodes.length
                + observerValue.new_nodes.length
                + followerValue.new_nodes.length < 1;
            }

            return !((hotValue.resource_spec.spec_id > 0 && hotValue.resource_spec.count > 0)
              || (coldValue.resource_spec.spec_id > 0 && coldValue.resource_spec.count > 0)
              || (observerValue.resource_spec.spec_id > 0 && observerValue.resource_spec.count > 0)
              || (followerValue.resource_spec.spec_id > 0 && followerValue.resource_spec.count > 0));
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

          const subTitle = (
            <div style="background-color: #F5F7FA; padding: 8px 16px;">
              <div class='tips-item'>
                {t('集群')} :
                <span
                  style="color: #313238"
                  class="ml-8">
                  {props.data.cluster_name}
                </span>
              </div>
              <div class='mt-4'>{t('替换后原节点 IP 将不在可用，资源将会被释放')}</div>
            </div>
          )

          InfoBox({
            title: t('确认替换n台节点IP', { n: getReplaceNodeNums() }),
            subTitle,
            confirmText: t('确认'),
            cancelText: t('取消'),
            headerAlign: 'center',
            contentAlign: 'left',
            footerAlign: 'center',
            extCls: 'doris-replace-modal',
            onClose: () => reject(),
            onConfirm: () => {
              const nodeData = {};
              if (ipSource.value === 'manual_input') {
                Object.assign(nodeData, {
                  new_nodes: {
                    hot: hotValue.new_nodes,
                    cold: coldValue.new_nodes,
                    observer: observerValue.new_nodes,
                    follower: followerValue.new_nodes
                  },
                });
              } else {
                Object.assign(nodeData, {
                  resource_spec: {
                    hot: hotValue.resource_spec,
                    cold: coldValue.resource_spec,
                    observer: observerValue.resource_spec,
                    follower: followerValue.resource_spec
                  },
                });
              }
              createTicket({
                ticket_type: TicketTypes.DORIS_REPLACE,
                bk_biz_id: currentBizId,
                details: {
                  cluster_id: props.data.id,
                  ip_source: ipSource.value,
                  old_nodes: {
                    hot: hotValue.old_nodes,
                    cold: coldValue.old_nodes,
                    observer: observerValue.old_nodes,
                    follower: followerValue.old_nodes
                  },
                  ...nodeData,
                },
              })
                .then((data) => {
                  ticketMessage(data.id);
                  emits('change');
                  resolve('success');
                })
                .catch(() => {
                  reject();
                });
            },
          });
        }, () => reject('error'));
      });
    },
    cancel() {
      return Promise.resolve();
    },
  });
</script>

<style lang="less">
  .doris-replace-modal {
    .bk-modal-content div {
      font-size: 14px;
    }

    .tips-item {
      padding: 2px 0;
    }
  }
</style>
<style lang="less" scoped>
  .doris-cluster-replace-box {
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

    .replace-item {
      & ~ .replace-item {
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
