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
    class="big-data-machine-shrink-box"
    quick-close
    :title="title"
    :width="960">
    <BkLoading :loading="loading">
      <div class="machine-shrink-wrapper">
        <NodeStatusList
          ref="nodeStatusListRef"
          v-model="nodeType"
          :list="nodeStatusList"
          :node-info="modelValue" />
        <div class="machine-panel">
          <MachinePanel
            :key="nodeType"
            :data="modelValue[nodeType]!"
            @change="handleNodeHostChange" />
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
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { useCreateTicket } from '@hooks';

  import { DBTypes, TicketTypes } from '@common/const';

  import { messageError } from '@utils';

  import MachinePanel from './MachinePanel.vue';
  import NodeStatusList from './NodeStatusList.vue';

  export interface TShrinkNode {
    // 缩容后的主机列表
    hostList: {
      alive: number;
      bk_cloud_id: number;
      bk_disk: number;
      bk_host_id: number;
      ip: string;
    }[];
    // 节点显示名称
    label: string;
    // 改节点所需的最少主机数
    minHost: number;
    // 原始实例节点列表
    originalNodeList: {
      bk_cloud_id: number;
      bk_host_id: number;
      cpu: number;
      disk: number;
      ip: string;
      mem: number;
      node_count: number;
      role?: string;
      role_set?: string[];
      status: number;
    }[];
    // 缩容目标磁盘大小
    // targetDisk: number,
    // 选择节点后实际的缩容磁盘大小
    shrinkDisk: number;
    // 节点类型 tag 文本
    tagText: string;
    // 原始磁盘大小
    totalDisk: number;
  }

  const ticketTypeMap = {
    [DBTypes.DORIS]: TicketTypes.DORIS_SHRINK,
    [DBTypes.ES]: TicketTypes.ES_SHRINK,
    [DBTypes.HDFS]: TicketTypes.HDFS_SHRINK,
    [DBTypes.KAFKA]: TicketTypes.KAFKA_SHRINK,
    [DBTypes.PULSAR]: TicketTypes.PULSAR_SHRINK,
  };

  export interface Props {
    data: {
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

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const modelValue = defineModel<Record<string, TShrinkNode>>({
    required: true,
  });

  const { t } = useI18n();

  const generateExtInfo = () =>
    Object.entries(modelValue.value).reduce(
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

  const getOldNodes = () => {
    return Object.entries(modelValue.value).reduce(
      (result, [nodeName, nodeInfo]) => {
        return Object.assign(result, {
          [nodeName]: nodeInfo.hostList,
        });
      },
      {} as Record<string, TShrinkNode['hostList']>,
    );
  };

  const { loading: isSubmiting, run: createTicket } = useCreateTicket<{
    cluster_id: number;
    ext_info: ReturnType<typeof generateExtInfo>;
    ip_source: string;
    old_nodes: ReturnType<typeof getOldNodes>;
  }>(ticketTypeMap[props.data.db_type], {
    onSuccess() {
      emits('submit');
      isShow.value = false;
    },
  });

  const nodeStatusListRef = useTemplateRef('nodeStatusListRef');
  const nodeType = ref(Object.keys(modelValue.value)[0] || '');

  const nodeStatusList = computed(() =>
    Object.keys(modelValue.value).map((key) => ({
      key,
      label: modelValue.value[key]!.label,
    })),
  );

  watch(
    isShow,
    () => {
      if (!isShow.value) {
        return;
      }
      const firstNotEmptyNodeType = _.find(
        Object.keys(modelValue.value),
        (nodeType) => modelValue.value[nodeType]!.hostList.length > 0,
      );
      nodeType.value = firstNotEmptyNodeType ? firstNotEmptyNodeType : Object.keys(modelValue.value)[0]!;
    },
    {
      immediate: true,
    },
  );

  // 缩容节点主机修改
  const handleNodeHostChange = (hostList: TShrinkNode['hostList']) => {
    const shrinkDisk = hostList.reduce((result, hostItem) => result + (hostItem.bk_disk || 0), 0);
    modelValue.value[nodeType.value]!.hostList = hostList;
    modelValue.value[nodeType.value]!.shrinkDisk = shrinkDisk;
  };

  const handleSubmit = () => {
    if (!nodeStatusListRef.value!.validate()) {
      messageError(t('缩容主机未填写'));
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
            cluster_id: props.data.id,
            ext_info: generateExtInfo(),
            ip_source: 'resource_pool',
            old_nodes: getOldNodes(),
          },
        }),
      subTitle: () => {
        const renderShrinkDiskTips = () =>
          Object.values(modelValue.value).map((nodeData) => {
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
      },
      title: t('确认缩容【name】集群', {
        name: props.data.cluster_name,
      }),
    });
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .big-data-machine-shrink-box {
    .machine-shrink-wrapper {
      display: flex;
      margin: 24px 24px 0;
      background: #fff;
      border-radius: 2px;
      box-shadow: 0 2px 4px 0 #1919290d;

      .machine-panel {
        flex: 1;
      }
    }
  }
</style>
