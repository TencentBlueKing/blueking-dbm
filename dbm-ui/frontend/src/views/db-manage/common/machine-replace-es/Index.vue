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
  <DbSideslider
    v-model:is-show="isShow"
    background-color="#F5F7FA"
    class="es-cluster-machine-replace-box"
    quick-close
    :title="title"
    :width="960">
    <div class="machine-replace-wrapper">
      <template v-if="!isEmpty">
        <BkRadioGroup
          v-model="ipSource"
          class="ip-srouce-box">
          <BkRadioButton label="resource_pool">
            {{ t('资源池自动匹配') }}
          </BkRadioButton>
          <!-- <BkRadioButton label="manual_input">
            {{ t('资源池手动选择') }}
          </BkRadioButton> -->
        </BkRadioGroup>
        <template
          v-for="[key, nodeInfo] in Object.entries(modelValue)"
          :key="key">
          <div
            v-show="nodeInfo.oldHostList.length > 0"
            class="node-item">
            <div class="item-label">{{ nodeInfo.label }}</div>
            <ReourcePanel
              ref="nodeRefs"
              v-model:host-list="nodeInfo.hostList"
              v-model:old-host-list="nodeInfo.oldHostList"
              v-model:resource-spec="nodeInfo.resourceSpec"
              :cloud-info="{
                id: clusterData.bk_cloud_id,
                name: clusterData.bk_cloud_name,
              }"
              :data="nodeInfo"
              :disable-host-method="(data: TReplaceNode['hostList'][0]) => machineDisableHandler(data, key)"
              :ip-source="ipSource"
              @remove-node="handleRemoveNode" />
          </div>
        </template>
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
    <template #footer>
      <BkButton
        class="w-88"
        :loading="isSubmiting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <BkButton
        class="w-88 ml-8"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbSideslider>
</template>
<script lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import EsModel from '@services/model/es/es';
  import type { HostInfo } from '@services/types';

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import { messageError } from '@utils';

  import ReourcePanel from './ResourcePanel.vue';

  export interface TReplaceNode {
    // 集群id
    clusterId: number;
    hostList: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_disk: number;
      bk_host_id: number;
      instance_num?: number;
      ip: string;
    }[];
    label: string;
    oldHostList: {
      bk_cloud_id: number;
      bk_cloud_name: string;
      bk_host_id: number;
      host_info: HostInfo;
      ip: string;
      related_instances: {
        bk_instance_id: number;
      }[];
    }[];
    // 扩容资源池
    resourceSpec: {
      count: number;
      instance_num: number;
      spec_id: number;
    };
    // 集群的节点类型
    role: string;
    // 资源池规格集群类型
    specClusterType: string;
    // 资源池规格集群类型
    specMachineType: string;
  }

  interface INodeValue {
    new_nodes: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
    old_nodes: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
    resource_spec: {
      count: number;
      spec_id: number;
    };
  }
</script>
<script setup lang="tsx">
  interface Props {
    clusterData: EsModel;
    machineDisableMethod?: (machine: TReplaceNode['hostList'][0], role: string) => boolean | string;
    title: string;
  }

  interface Emits {
    (e: 'submit'): void;
    (e: 'removeNode', node: TReplaceNode['oldHostList'][number]): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<Record<string, TReplaceNode>>({
    required: true,
  });

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const getResourceSpce = () => {
    if (ipSource.value === 'manual_input') {
      return Object.entries(modelValue.value).reduce(
        (result, [nodeName, nodeInfo]) => {
          return Object.assign(result, {
            [nodeName]: {
              count: nodeInfo.hostList.length,
              hosts: nodeInfo.hostList.map((hostItem) => ({
                bk_biz_id: hostItem.bk_biz_id,
                bk_cloud_id: hostItem.bk_cloud_id,
                bk_disk: hostItem.bk_disk,
                bk_host_id: hostItem.bk_host_id,
                instance_num: hostItem.instance_num,
                ip: hostItem.ip,
              })),
              spec_id: 0,
            },
          });
        },
        {} as Record<
          string,
          {
            count: number;
            hosts: TReplaceNode['hostList'];
            spec_id: number;
          }
        >,
      );
    }
    return Object.entries(modelValue.value).reduce(
      (result, [nodeName, nodeInfo]) => {
        return Object.assign(result, {
          [nodeName]: nodeInfo.resourceSpec,
        });
      },
      {} as TReplaceNode['resourceSpec'],
    );
  };

  const getOldNodes = () => {
    return Object.entries(modelValue.value).reduce(
      (result, [nodeName, nodeInfo]) => {
        return Object.assign(result, {
          [nodeName]: nodeInfo.oldHostList.map((item) => ({
            bk_cloud_id: item.bk_cloud_id,
            bk_host_id: item.bk_host_id,
            ip: item.ip,
          })),
        });
      },
      {} as Record<string, INodeValue['old_nodes']>,
    );
  };

  const { loading: isSubmiting, run: createTicket } = useCreateTicket<{
    cluster_id: number;
    ip_source: string;
    old_nodes: ReturnType<typeof getOldNodes>;
    resource_spec: ReturnType<typeof getResourceSpce>;
  }>(TicketTypes.ES_REPLACE, {
    onSuccess() {
      emits('submit');
      isShow.value = false;
    },
  });

  const ipSource = ref('resource_pool');
  const nodeRefs = useTemplateRef('nodeRefs');

  const machineDisableHandler = (hostData: TReplaceNode['hostList'][0], type: string) => {
    if (!props.machineDisableMethod) {
      return false;
    }
    return props.machineDisableMethod(hostData, type);
  };

  const isEmpty = computed(() => {
    return Object.values(modelValue.value).every((item) => item.oldHostList.length < 1);
  });

  const handleRemoveNode = (node: TReplaceNode['oldHostList'][0]) => {
    emits('removeNode', node);
  };

  const handleSubmit = () => {
    if (isEmpty.value) {
      messageError(t('至少替换一种节点类型'));
      return;
    }

    Promise.all(nodeRefs.value!.map((item) => item!.getValue()))
      .then(() => {
        const replaceResult = Object.entries(modelValue.value).reduce<Record<string, INodeValue>>(
          (result, [key, nodeInfo]) => {
            if (nodeInfo.oldHostList.length < 1) {
              return Object.assign(result, {
                [key]: {
                  new_nodes: [],
                  resource_spec: {
                    count: 0,
                    spec_id: 0,
                  },
                },
              });
            }
            return Object.assign(result, {
              [key]: {
                new_nodes: nodeInfo.hostList.map((hostItem) => ({
                  bk_biz_id: hostItem.bk_biz_id,
                  bk_cloud_id: hostItem.bk_cloud_id,
                  bk_host_id: hostItem.bk_host_id,
                  ip: hostItem.ip,
                })),
                resource_spec: {
                  ...nodeInfo.resourceSpec,
                  count: nodeInfo.oldHostList.length,
                },
              },
            });
          },
          {},
        );

        const isEmptyValue = () => {
          if (ipSource.value === 'manual_input') {
            return Object.values(replaceResult).every((item) => item.new_nodes.length < 1);
          }
          return Object.values(replaceResult).every(
            (item) => item.resource_spec.spec_id > 0 && item.resource_spec.count < 1,
          );
        };

        if (isEmptyValue()) {
          messageError(t('替换节点不能为空'));
          return Promise.reject();
        }

        const getReplaceNodeNums = () => {
          if (ipSource.value === 'manual_input') {
            return Object.values(modelValue.value).reduce((result, nodeData) => result + nodeData.hostList.length, 0);
          }
          return Object.values(modelValue.value).reduce((result, nodeData) => {
            if (nodeData.resourceSpec.spec_id > 0) {
              return result + nodeData.oldHostList.length;
            }
            return result;
          }, 0);
        };

        InfoBox({
          cancelText: t('取消'),
          confirmText: t('确认'),
          contentAlign: 'center',
          footerAlign: 'center',
          headerAlign: 'center',
          onConfirm: () =>
            createTicket({
              details: {
                cluster_id: props.clusterData.id,
                ip_source: ipSource.value,
                old_nodes: getOldNodes(),
                resource_spec: getResourceSpce(),
              },
            }),
          subTitle: t('替换后原节点 IP 将不在可用，资源将会被释放'),
          title: t('确认替换n台节点IP', {
            n: getReplaceNodeNums(),
          }),
        });
      })
      .catch(() => {
        messageError(t('扩容主机未填写'));
      });
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .es-cluster-machine-replace-box {
    padding: 18px 43px 18px 37px;
    font-size: 12px;
    line-height: 20px;
    color: #63656e;

    .machine-replace-wrapper {
      padding: 18px 24px;
      font-size: 12px;
      line-height: 20px;
      color: #63656e;
    }

    .ip-srouce-box {
      display: flex;
      margin-bottom: 16px;

      .bk-radio-button {
        flex: 1;
        background: #fff;
      }
    }

    .node-item {
      & ~ .node-item {
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
