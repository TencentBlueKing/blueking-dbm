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
      :data="originalNodeList"
      style="max-height: calc(100vh - 300px)"
      @row-click="handleRowClick" />
    <template #footer>
      <I18nT
        class="mr-16"
        keypath="已选n台_共nG"
        tag="span">
        <span
          class="number"
          style="color: #3a84ff">
          {{ Object.values(checkedNodeMap).length }}
        </span>
        <span
          class="number"
          style="color: #2dcb56">
          {{ selectNodeDiskTotal }}
        </span>
      </I18nT>
      <BkButton
        style="width: 64px"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="ml-8"
        style="width: 64px"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script lang="tsx">
  interface IModleValue {
    bk_host_id: number;
    cpu: number;
    disk: number;
    ip: string;
    mem: number;
    node_count: number;
    role?: string;
    role_set?: string[];
    status: number;
  }
</script>
<script setup lang="tsx" generic="T extends IModleValue">
  import { computed, shallowRef, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import RenderHostStatus from '@components/render-host-status/Index.vue';

  import RenderClusterRole from '@views/db-manage/common/RenderRole.vue';

  import type { TShrinkNode } from '../Index.vue';

  export interface Props {
    isShow: boolean;
    minHost: number;
    modelValue: TShrinkNode['hostList'];
    originalNodeList: TShrinkNode['originalNodeList'];
  }

  export interface Emits {
    (e: 'change', value: TShrinkNode['originalNodeList']): void;
    (e: 'update:isShow', value: boolean): void;
  }

  type IRowData = TShrinkNode['originalNodeList'][number];

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const checkedNodeMap = shallowRef<Record<number, IRowData>>({});
  const selectNodeDiskTotal = computed(() =>
    Object.values(checkedNodeMap.value).reduce((result, item) => result + item.disk, 0),
  );

  const checkNodeDisable = (node: IRowData) => {
    const options = {
      disabled: false,
      tooltips: {
        content: '',
        disabled: true,
      },
    };
    if (checkedNodeMap.value[node.bk_host_id]) {
      return options;
    }

    if (Object.values(checkedNodeMap.value).length >= props.originalNodeList.length - props.minHost) {
      options.disabled = true;
      options.tooltips.disabled = false;
      options.tooltips.content = t('节点至少保留n个', { n: props.minHost });
      return options;
    }

    return options;
  };

  const tableColumns = [
    {
      label: () => (
        <bk-checkbox
          model-value={
            Object.values(checkedNodeMap.value).length === props.originalNodeList.length &&
            props.originalNodeList.length > 0
          }
          label={true}
          onChange={handleSelectAll}
        />
      ),
      render: ({ data }: { data: IRowData }) => {
        const disabledInfo = checkNodeDisable(data);
        return (
          <span v-bk-tooltips={disabledInfo.tooltips}>
            <bk-checkbox
              disabled={disabledInfo.disabled}
              label={true}
              model-value={Boolean(checkedNodeMap.value[data.bk_host_id])}
              style='vertical-align: middle; pointer-events: none;'
            />
          </span>
        );
      },
      width: 60,
    },
    {
      field: 'ip',
      label: t('节点IP'),
    },
    {
      field: 'node_count',
      label: t('实例数量'),
    },
    {
      label: t('类型'),
      render: ({ data }: { data: IRowData }) => {
        return <RenderClusterRole data={data.role_set || [data.role as string]} />;
      },
      width: 300,
    },
    {
      label: t('Agent状态'),
      render: ({ data }: { data: IRowData }) => <RenderHostStatus data={data.status} />,
    },
    {
      field: 'cpu',
      label: 'CPU',
      render: ({ data }: { data: IRowData }) => (data.cpu ? `${data.cpu} ${t('核')}` : '--'),
    },
    {
      field: 'mem',
      label: t('内存_MB'),
      render: ({ data }: { data: IRowData }) => data.mem || '--',
    },
    {
      field: 'disk',
      label: t('磁盘_GB'),
      render: ({ data }: { data: IRowData }) => data.disk || '--',
    },
  ];

  watch(
    () => props.modelValue,
    () => {
      checkedNodeMap.value = props.modelValue.reduce(
        (result, item) => ({
          ...result,
          [item.bk_host_id]: item,
        }),
        {},
      );
    },
    {
      immediate: true,
    },
  );

  // 全选（不能全部选中，留最小数量）
  const handleSelectAll = (checked: boolean) => {
    const checkedMap = {} as Record<number, IRowData>;
    if (checked) {
      props.originalNodeList.slice(0, props.originalNodeList.length - props.minHost).forEach((nodeItem) => {
        checkedMap[nodeItem.bk_host_id] = nodeItem;
      });
    }
    checkedNodeMap.value = checkedMap;
  };

  // 选中单行
  const handleRowClick = (event: MouseEvent, data: IRowData) => {
    if (checkNodeDisable(data).disabled) {
      return;
    }
    const selectMap = { ...checkedNodeMap.value };
    if (!selectMap[data.bk_host_id]) {
      selectMap[data.bk_host_id] = data;
    } else {
      delete selectMap[data.bk_host_id];
    }
    checkedNodeMap.value = selectMap;
  };

  const handleSubmit = () => {
    emits('change', Object.values(checkedNodeMap.value));
    handleClose();
  };

  const handleClose = () => {
    emits('update:isShow', false);
  };
</script>
