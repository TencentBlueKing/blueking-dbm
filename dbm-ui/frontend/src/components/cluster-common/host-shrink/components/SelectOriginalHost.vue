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
    :title="t('手动添加节点 IP')"
    :width="1100">
    <BkTable
      class="mb-16"
      :columns="tableColumns"
      :data="originalNodeList" />
    <template #footer>
      <I18nT
        class="mr-16"
        keypath="已选n台_共nG_(目标容量:nG)"
        tag="span">
        <span
          class="number"
          style="color: #3a84ff;">
          {{ Object.values(checkedNodeMap).length }}
        </span>
        <span
          class="number"
          style="color: #2dcb56;">
          {{ selectNodeDiskTotal }}
        </span>
        <span
          class="number"
          style="color: #63656e;">
          {{ targetDisk }}
        </span>
      </I18nT>
      <BkButton
        style="width: 64px;"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="ml-8"
        style="width: 64px;"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script setup lang="tsx" generic="T extends EsNodeModel|HdfsNodeModel|KafkaNodeModel|PulsarNodeModel">
  import  {
    computed,
    ref,
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type EsNodeModel from '@services/model/es/es-node';
  import type HdfsNodeModel from '@services/model/hdfs/hdfs-node';
  import type KafkaNodeModel from '@services/model/kafka/kafka-node';
  import type PulsarNodeModel from '@services/model/pulsar/pulsar-node';

  import RenderClusterRole from '@components/cluster-common/RenderRole.vue';
  import RenderHostStatus from '@components/render-host-status/Index.vue';

  import type { TShrinkNode } from '../Index.vue';

  interface Props {
    modelValue: TShrinkNode<T>['nodeList'],
    isShow: boolean,
    originalNodeList: TShrinkNode<T>['nodeList'],
    targetDisk: number,
  }

  interface Emits {
    (e: 'change', value: Props['modelValue']): void;
    (e: 'update:isShow', value: boolean): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isSelectedAll = ref(false);

  const checkedNodeMap = shallowRef<Record<number, Props['modelValue'][0]>>({});
  const selectNodeDiskTotal = computed(() => Object.values(checkedNodeMap.value)
    .reduce((result, item) => result + item.disk, 0));

  const checkNodeDisable = (node: Props['modelValue'][0]) => {
    const options = {
      disabled: false,
      tooltips: {
        disabled: true,
        content: '',
      },
    };
    if (checkedNodeMap.value[node.bk_host_id]) {
      return options;
    }

    if (Object.values(checkedNodeMap.value).length >= props.originalNodeList.length - 1) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('节点至少保留一个');
      return options;
    }

    return options;
  };

  const tableColumns = [
    {
      width: 60,
      label: () => (
        <bk-checkbox
          label={true}
          model-value={isSelectedAll.value}
          onChange={handleSelectAll}
        />
      ),
      render: ({ data }: {data: Props['modelValue'][0]}) => {
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
      render: ({ data }: {data: Props['modelValue'][0]}) => (
        <RenderClusterRole data={[data.role]} />
      ),
    },
    {
      label: t('Agent状态'),
      render: ({ data }: {data: Props['modelValue'][0]}) => (
        <RenderHostStatus data={data.status} />
      ),
    },
    {
      label: 'CPU',
      field: 'cpu',
      render: ({ data }: {data:Props['modelValue'][0]}) => (data.cpu ? `${data.cpu} ${t('核')}` : '--'),
    },
    {
      label: t('内存_MB'),
      field: 'mem',
      render: ({ data }: {data:Props['modelValue'][0]}) => data.mem || '--',
    },
    {
      label: t('磁盘_GB'),
      field: 'disk',
      render: ({ data }: {data:Props['modelValue'][0]}) => data.disk || '--',
    },
  ];

  watch(() => props.modelValue, () => {
    checkedNodeMap.value = props.modelValue.reduce((result, item) => ({
      ...result,
      [item.bk_host_id]: item,
    }), {});
  }, {
    immediate: true,
  });

  // 全选（不能全部选中，留最后一个）
  const handleSelectAll = (checked: boolean) => {
    const checkedMap = {} as Record<number, Props['modelValue'][0]>;
    if (checked) {
      props.originalNodeList.slice(0, -1).forEach((nodeItem) => {
        checkedMap[nodeItem.bk_host_id] = nodeItem;
      });
    }
    checkedNodeMap.value = checkedMap;
  };

  // 选中节点
  const handleSelect = (checked: boolean, data: Props['modelValue'][0]) => {
    const checkedMap = { ...checkedNodeMap.value };
    if (checked) {
      checkedMap[data.bk_host_id] = data;
    } else {
      delete checkedMap[data.bk_host_id];
    }

    checkedNodeMap.value = checkedMap;
  };

  const handleSubmit = () => {
    emits('change', Object.values(checkedNodeMap.value));
    handleClose();
  };

  const handleClose = () => {
    emits('update:isShow', false);
  };
</script>
