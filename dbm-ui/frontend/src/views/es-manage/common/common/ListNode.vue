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

  import { getListNodes } from '@services/es';
  import EsNodeModel from '@services/model/es/es-node';

  import { useGlobalBizs } from '@stores';

  import RenderClusterRole from '@components/cluster-common/RenderRole.vue';
  import RenderHostStatus from '@components/render-host-status/Index.vue';

  interface Props {
    modelValue: Array<EsNodeModel>;
    isShow: boolean;
    clusterId: number;
    from?: string
  }
  interface Emits {
    (e: 'update:isShow', value: boolean): void;
    (e: 'update:modelValue', value: Array<EsNodeModel>): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const { t } = useI18n();

  const globalBizsStore = useGlobalBizs();

  const isLoading = ref(true);
  const isAnomalies = ref(false);
  const tableData = shallowRef<EsNodeModel[]>([]);
  const checkedNodeMap = shallowRef<Record<number, EsNodeModel>>({});

  const isSelectedAll = computed(() => {
    if (tableData.value.length <= 0) return false;

    const typeNodes = getTypeNodes();
    const clientSelected: EsNodeModel[] = [];
    const hotSelected: EsNodeModel[] = [];
    const coldSelected: EsNodeModel[] = [];

    for (const nodeItem of Object.values(checkedNodeMap.value)) {
      if (nodeItem.isClient) {
        clientSelected.push(nodeItem);
      } else if (nodeItem.isHot) {
        hotSelected.push(nodeItem);
      } else if (nodeItem.isCold) {
        coldSelected.push(nodeItem);
      }
    }

    if (clientSelected.length === 0 && hotSelected.length === 0 && coldSelected.length === 0) {
      return false;
    }

    return typeNodes.clientNodes.length - 1 === clientSelected.length
      && typeNodes.hotNodes.length - 1 === hotSelected.length
      && typeNodes.coldNodes.length - 1 === coldSelected.length;
  });

  const checkNodeDisable = (node: EsNodeModel) => {
    const options = {
      disabled: false,
      tooltips: {
        disabled: true,
        content: '',
      },
    };

    if (props.from === 'shrink') {
      // master 节点不支持缩容
      if (node.isMaster) {
        options.disabled = true;
        options.tooltips.disabled = false;
        options.tooltips.content = t('节点类型不支持缩容');

        return options;
      }

      // 其它类型的节点数不能全部被缩容，至少保留一个
      const clientNodes: string[] = [];
      const hotNodes: string[] = [];
      const coldNodes: string[] = [];
      tableData.value.forEach((nodeItem) => {
        // console.log('from check disable = ', checkedNodeMap.value, nodeItem);
        if (checkedNodeMap.value[nodeItem.bk_host_id]) {
          return;
        }
        if (nodeItem.isClient) {
          clientNodes.push(nodeItem.ip);
        } else if (nodeItem.isHot) {
          hotNodes.push(nodeItem.ip);
        } else if (nodeItem.isCold) {
          coldNodes.push(nodeItem.ip);
        }
      });

      if (node.isClient && clientNodes.length < 2 && clientNodes.includes(node.ip)) {
        options.disabled = true;
        options.tooltips.disabled = false;
        options.tooltips.content = t('Client类型节点至少保留一个');

        return options;
      }

      if (node.isHot && hotNodes.length < 2 && hotNodes.includes(node.ip)) {
        options.disabled = true;
        options.tooltips.disabled = false;
        options.tooltips.content = t('Hot类型节点至少保留一个');
        return options;
      }

      if (node.isCold && coldNodes.length < 2 && coldNodes.includes(node.ip)) {
        options.disabled = true;
        options.tooltips.disabled = false;
        options.tooltips.content = t('Cold类型节点至少保留一个');
      }
    }

    return options;
  };

  function getTypeNodes() {
    return tableData.value.reduce((result, nodeItem) => {
      if (nodeItem.isClient) {
        result.clientNodes.push(nodeItem);
      } else if (nodeItem.isHot) {
        result.hotNodes.push(nodeItem);
      } else if (nodeItem.isCold) {
        result.coldNodes.push(nodeItem);
      }

      return result;
    }, {
      clientNodes: [] as EsNodeModel[],
      hotNodes: [] as EsNodeModel[],
      coldNodes: [] as EsNodeModel[],
    });
  }

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
      render: ({ data }: {data: EsNodeModel}) => {
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
      render: ({ data }: {data: EsNodeModel}) => (
        <RenderClusterRole data={[data.role]} />
      ),
    },
    {
      label: t('Agent状态'),
      render: ({ data }: {data: EsNodeModel}) => (
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
    }), {} as Record<number, EsNodeModel>);
  });

  fetchData();


  const handleSelect = (checked: boolean, data: EsNodeModel) => {
    const checkedMap = { ...checkedNodeMap.value };
    if (checked) {
      checkedMap[data.bk_host_id] = new EsNodeModel(data);
    } else {
      delete checkedMap[data.bk_host_id];
    }

    checkedNodeMap.value = checkedMap;
  };

  const handleSelectAll = async (checked: boolean) => {
    let checkedMap = {} as Record<number, EsNodeModel>;
    if (checked && props.from === 'shrink') {
      const typeNodes = getTypeNodes();
      for (const nodes of Object.values(typeNodes)) {
        // 至少保留一个
        nodes.splice(-1, 1);
        for (const node of nodes) {
          checkedMap[node.bk_host_id] = node;
        }
      }
    } else if (checked) {
      checkedMap = tableData.value.reduce((result, nodeData) => {
        if (checkNodeDisable(nodeData).disabled) {
          return result;
        }
        return {
          ...result,
          [nodeData.bk_host_id]: nodeData,
        };
      }, {} as Record<number, EsNodeModel>);
    }

    checkedNodeMap.value = checkedMap;
  };

  const handleSubmit = () => {
    emits('update:modelValue', Object.values(checkedNodeMap.value));
    handleClosed();
  };

  const handleClosed = () => {
    emits('update:isShow', false);
  };
</script>
