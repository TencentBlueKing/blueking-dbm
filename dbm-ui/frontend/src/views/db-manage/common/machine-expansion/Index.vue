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
    class="big-data-machine-expansion-box"
    quick-close
    :title="title"
    :width="960">
    <BkLoading
      class="machine-expansion-wrapper"
      :loading="loading">
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
      <div class="layout">
        <NodeStatusList
          ref="nodeStatusListRef"
          v-model="nodeType"
          :ip-source="ipSource"
          :list="nodeStatusList"
          :node-info="modelValue" />
        <div class="machine-panel">
          <MachinePanel
            v-if="!loading"
            :key="nodeType"
            v-model:expansion-disk="modelValue[nodeType]!.expansionDisk"
            v-model:host-list="modelValue[nodeType]!.hostList"
            v-model:resource-spec="modelValue[nodeType]!.resourceSpec"
            :cloud-info="{
              id: clusterData.bk_cloud_id,
              name: clusterData.bk_cloud_name,
            }"
            :data="modelValue[nodeType]!"
            :db-type="clusterData.db_type"
            :ip-source="ipSource" />
        </div>
      </div>
    </BkLoading>
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
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import DbResourceModel from '@services/model/db-resource/DbResource';

  import { useCreateTicket } from '@hooks';

  import { DBTypes, TicketTypes } from '@common/const';

  import { messageError } from '@utils';

  import MachinePanel from './MachinePanel.vue';
  import NodeStatusList from './NodeStatusList.vue';

  export interface TExpansionNode {
    // 集群id
    clusterId: number;
    // 扩容目标容量
    // targetDisk: number;
    // 实际选中的扩容主机容量
    expansionDisk: number;
    // 扩容主机
    hostList: DbResourceModel[];
    // 服务器来源
    ipSource: 'resource_pool' | 'manual_input';
    // 集群节点展示名
    label: string;
    // 初始主机
    originalHostList: {
      bk_host_id: number;
      host_info: {
        bk_disk: number;
      };
    }[];
    // 扩容资源池
    resourceSpec: {
      count: number;
      spec_id: number;
    };
    // 集群的节点类型
    role: string;
    // 是否显示台数
    showCount?: boolean;
    // 资源池规格集群类型
    specClusterType: string;
    // 资源池规格集群类型
    specMachineType: string;
    // 节点类型 tag 文本
    tagText: string;
    // 当前主机的总容量
    totalDisk: number;
  }

  const ticketTypeMap = {
    [DBTypes.DORIS]: TicketTypes.DORIS_SCALE_UP,
    [DBTypes.ES]: TicketTypes.ES_SCALE_UP,
    [DBTypes.HDFS]: TicketTypes.HDFS_SCALE_UP,
    [DBTypes.KAFKA]: TicketTypes.KAFKA_SCALE_UP,
    [DBTypes.PULSAR]: TicketTypes.PULSAR_SCALE_UP,
  };

  interface Props {
    clusterData: {
      bk_cloud_id: number;
      bk_cloud_name: string;
      cluster_name: string;
      db_type: keyof typeof ticketTypeMap;
      id: number;
    };
    loading?: boolean;
    title: string;
  }

  type Emits = (e: 'submit') => void;
</script>
<script setup lang="tsx">
  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<Record<string, TExpansionNode>>({
    required: true,
  });

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const ipSource = ref('resource_pool');

  const generateExtInfo = () =>
    Object.entries(modelValue.value).reduce(
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
      {} as Record<
        string,
        {
          expansion_disk: number;
          total_disk: number;
          total_hosts: number;
        }
      >,
    );

  const getResourceSpce = () => {
    if (ipSource.value === 'manual_input') {
      return Object.entries(modelValue.value).reduce(
        (result, [nodeName, nodeInfo]) => {
          return Object.assign(result, {
            [nodeName]: {
              count: nodeInfo.hostList.length,
              hosts: nodeInfo.hostList.map((hostItem) => ({
                bk_biz_id: hostItem.dedicated_biz,
                bk_cloud_id: hostItem.bk_cloud_id,
                bk_disk: hostItem.bk_disk,
                bk_host_id: hostItem.bk_host_id,
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
            hosts: TExpansionNode['hostList'];
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
      {} as TExpansionNode['resourceSpec'],
    );
  };

  const { t } = useI18n();

  const { loading: isSubmiting, run: createTicket } = useCreateTicket<{
    cluster_id: number;
    ext_info: ReturnType<typeof generateExtInfo>;
    ip_source: string;
    resource_spec: ReturnType<typeof getResourceSpce>;
  }>(ticketTypeMap[props.clusterData.db_type], {
    onSuccess() {
      emits('submit');
      isShow.value = false;
    },
  });

  const nodeStatusList = computed(() =>
    Object.keys(modelValue.value).map((key) => ({
      key,
      label: modelValue.value[key]!.label,
    })),
  );

  const nodeStatusListRef = ref();
  const nodeType = ref(Object.keys(modelValue.value)[0]!);

  const handleSubmit = () => {
    if (!nodeStatusListRef.value!.validate()) {
      messageError(t('扩容主机未填写'));
      return;
    }

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
            ext_info: generateExtInfo(),
            ip_source: ipSource.value,
            resource_spec: getResourceSpce(),
          },
        }),
      subTitle: () => {
        const renderExpansionDiskTips = () =>
          Object.values(modelValue.value).map((nodeData) => {
            if (nodeData.expansionDisk) {
              return (
                <div>
                  {t('name容量从nG扩容至nG', {
                    expansionDisk: nodeData.totalDisk + nodeData.expansionDisk,
                    name: nodeData.label,
                    totalDisk: nodeData.totalDisk,
                  })}
                </div>
              );
            }
            return null;
          });

        return <div style='font-size: 14px; line-height: 28px; color: #63656E;'>{renderExpansionDiskTips()}</div>;
      },
      title: t('确认扩容【name】集群', {
        name: props.clusterData.cluster_name,
      }),
    });
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .big-data-machine-expansion-box {
    .machine-expansion-wrapper {
      padding: 18px 24px;
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
    }

    .layout {
      display: flex;
      background: #fff;
      border-radius: 2px;
      box-shadow: 0 2px 4px 0 #1919290d;

      .machine-panel {
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
