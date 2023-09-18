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
  <BkDialog
    :is-show="isShow"
    :title="$t('添加节点IP')"
    :width="1100"
    @closed="handleClosed">
    <BkLoading
      :loading="isLoading"
      style="padding-bottom: 20px;">
      <DbOriginalTable
        ref="tableRef"
        :columns="columns"
        :data="tableData"
        :is-anomalies="isAnomalies"
        @refresh="fetchData" />
    </BkLoading>
    <template #footer>
      <span
        v-bk-tooltips="{
          disabled: !isSubmitDisabled,
          content: $t('请添加节点IP')
        }">
        <BkButton
          :disabled="isSubmitDisabled"
          theme="primary"
          @click="handleSubmit">
          {{ $t('确定') }}
        </BkButton>
      </span>
      <BkButton
        class="ml8"
        @click="handleClosed">
        {{ $t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script setup lang="tsx">
  import {
    computed,
    nextTick,
    ref,
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getListNodes } from '@services/kafka';
  import KafkaNodeModel from '@services/model/kafka/kafka-node';

  import { useGlobalBizs } from '@stores';

  import RenderClusterRole from '@components/cluster-common/RenderRole.vue';
  import RenderHostStatus from '@components/render-host-status/Index.vue';

  interface Props {
    modelValue: Array<KafkaNodeModel>;
    isShow: boolean;
    clusterId: number;
    from?: string
  }
  interface Emits {
    (e: 'update:isShow', value: boolean): void;
    (e: 'update:modelValue', value: Array<KafkaNodeModel>): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const isLoading = ref(true);
  const isAnomalies = ref(false);
  const tableData = shallowRef<KafkaNodeModel[]>([]);
  const checkedNodeMap = shallowRef<Record<number, KafkaNodeModel>>({});

  const isSelectedAll = computed(() => {
    if (tableData.value.length <= 0) return false;

    const brokerSelected = Object.values(checkedNodeMap.value).filter(node => node.isBroker);
    const brokerNodes = tableData.value.filter(node => node.isBroker);
    return brokerSelected.length > 0 && brokerSelected.length === brokerNodes.length - 1;
  });

  const checkNodeDisable = (node: KafkaNodeModel) => {
    const options = {
      disabled: false,
      tooltips: {
        disabled: true,
        content: '',
      },
    };

    if (props.from === 'shrink') {
      // broker 节点不支持缩容
      if (!node.isBroker) {
        options.disabled = true;
        options.tooltips.disabled = false;
        options.tooltips.content = t('节点类型不支持缩容');
      } else {
        // 其它类型的节点数不能全部被缩容，至少保留一个
        const brokerIps: string[] = [];
        tableData.value.forEach((nodeItem) => {
          if (checkedNodeMap.value[nodeItem.bk_host_id]) {
            return;
          }
          if (nodeItem.isBroker) {
            brokerIps.push(nodeItem.ip);
          }
        });

        if (brokerIps.length < 2 && brokerIps.includes(node.ip)) {
          options.disabled = true;
          options.tooltips.disabled = false;
          options.tooltips.content = t('Broker类型节点至少保留一个');
        }
      }
    }

    return options;
  };

  const columns = [
    {
      width: 60,
      label: () => (
        <bk-checkbox
          label={true}
          model-value={isSelectedAll.value}
          onChange={handleSelectAll}
        />
      ),
      render: ({ data }: {data: KafkaNodeModel}) => {
        const disabledInfo = checkNodeDisable(data);
        return (
          <span v-bk-tooltips={disabledInfo.tooltips}>
            <bk-checkbox
              disabled={disabledInfo.disabled}
              style="vertical-align: middle;"
              label={true}
              model-value={Boolean(checkedNodeMap.value[data.bk_host_id])}
              onChange={(value: boolean) => handleSelect(value, data)}
            />
          </span>
        );
      },
    },
    {
      label: t('节点IP'),
      field: 'ip',
    },
    {
      label: t('实例数量'),
      field: 'node_count',
    },
    {
      label: t('类型'),
      width: 300,
      render: ({ data }: {data: KafkaNodeModel}) => (
        <RenderClusterRole data={[data.role]} />
      ),
    },
    {
      label: t('Agent状态'),
      render: ({ data }: {data: KafkaNodeModel}) => (
        <RenderHostStatus data={data.status} />
      ),
    },
  ];

  const isSubmitDisabled = computed(() => Object.keys(checkedNodeMap.value).length < 1);

  const fetchData = () => {
    isLoading.value = true;
    getListNodes({
      bk_biz_id: globalBizsStore.currentBizId,
      cluster_id: props.clusterId,
      no_limit: 1,
    }).then((data) => {
      tableData.value = data.results;
      isAnomalies.value = false;
    })
      .catch(() => {
        tableData.value = [];
        isAnomalies.value = true;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  watch(() => props.isShow, () => {
    nextTick(() => {
      if (props.isShow) {
        fetchData();
      }
    });
    checkedNodeMap.value = props.modelValue.reduce((result, item) => ({
      ...result,
      [item.bk_host_id]: item,
    }), {} as Record<number, KafkaNodeModel>);
  });

  fetchData();


  const handleSelect = (checked: boolean, data: KafkaNodeModel) => {
    const checkedMap = { ...checkedNodeMap.value };
    if (checked) {
      checkedMap[data.bk_host_id] = new KafkaNodeModel(data);
    } else {
      delete checkedMap[data.bk_host_id];
    }

    checkedNodeMap.value = checkedMap;
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked && props.from === 'shrink') {
      const brokerNodes = tableData.value.filter(node => node.isBroker);
      // 至少保留一个
      brokerNodes.splice(-1, 1);
      checkedNodeMap.value = brokerNodes.reduce((result, nodeData) => ({
        ...result,
        [nodeData.bk_host_id]: nodeData,
      }), {} as Record<number, KafkaNodeModel>);
    } else if (checked) {
      checkedNodeMap.value = tableData.value.reduce((result, nodeData) => {
        if (checkNodeDisable(nodeData).disabled) {
          return result;
        }
        return {
          ...result,
          [nodeData.bk_host_id]: nodeData,
        };
      }, {} as Record<number, KafkaNodeModel>);
    } else {
      checkedNodeMap.value = {};
    }
  };

  const handleSubmit = () => {
    emits('update:modelValue', Object.values(checkedNodeMap.value));
    handleClosed();
  };

  const handleClosed = () => {
    emits('update:isShow', false);
  };
</script>
