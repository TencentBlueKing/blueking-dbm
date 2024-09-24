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
  <div class="render-switch-box">
    <RenderText
      v-if="selectedIpList"
      ref="textRef"
      class="ip-box"
      :data="selectedIpList"
      @click="handleIpTextClick">
      <template #content="{ data: ipData }">
        <div class="ip-content">
          <div class="ip-text">{{ ipData }}</div>
          <DbIcon
            class="delete-icon"
            type="delete-fill"
            @click.stop="handleIpDelete" />
        </div>
      </template>
    </RenderText>
    <TableEditSelect
      v-else
      ref="selectRef"
      v-model="localValue"
      :disabled="!data?.clusterId"
      :filterable="false"
      :list="selectList"
      :placeholder="t('请选择')"
      :rules="rules"
      @change="(value) => handleChange(value as string)">
      <template #default="{ optionItem }">
        <div class="role-host-select-option">
          <div>{{ optionItem.label }}</div>
          <div class="option-count">{{ count }}</div>
        </div>
      </template>
    </TableEditSelect>
  </div>
  <InstanceSelector
    v-model:is-show="isShowInstanceSelecotr"
    :cluster-types="[props.clusterType]"
    :selected="selected"
    :tab-list-config="tabListConfig"
    @cancel="handleInstancesCancel"
    @change="handleInstancesChange" />
</template>

<script lang="ts">
  export enum HostSelectType {
    AUTO = 'auto',
    MANUAL = 'manual',
  }
</script>
<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import InstanceSelector, { type InstanceSelectorValues, type IValue } from '@components/instance-selector/Index.vue';
  import TableEditSelect from '@components/render-table/columns/select/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  interface Props {
    data?: {
      clusterId: number;
      hostSelectType?: string;
    };
    clusterType: ClusterTypes | 'TendbClusterHost';
    tabListConfig: ComponentProps<typeof InstanceSelector>['tabListConfig'];
    selectedNodeList?: IValue[];
    count?: number;
    instanceIpList: string[];
  }

  interface Emits {
    (e: 'type-change', value: string): void;
    (e: 'num-change', value: number): void;
  }

  interface Exposes {
    resetValue: () => void;
    getValue: (fieldName: string) => Promise<
      | {
          fieldName: {
            ip: string;
            bk_host_id: number;
            bk_cloud_id: number;
            bk_biz_id: number;
          };
        }
      | undefined
    >;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    selectedNodeList: () => [],
    count: 0,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const selectRef = ref();
  const textRef = ref();
  const isShowInstanceSelecotr = ref(false);
  const localValue = ref(props.data?.hostSelectType ? props.data?.hostSelectType : HostSelectType.AUTO);

  const selected = shallowRef({ [props.clusterType]: [] } as InstanceSelectorValues<IValue>);

  const selectList = [
    {
      label: t('自动匹配'),
      value: HostSelectType.AUTO,
    },
    {
      label: t('手动选择'),
      value: HostSelectType.MANUAL,
    },
  ];

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('请选择节点类型'),
    },
  ];

  const selectedIpList = computed(() => selected.value[props.clusterType].map((item) => item.ip).join('\n'));

  watch(
    () => props.selectedNodeList,
    () => {
      selected.value[props.clusterType] = props.selectedNodeList;
    },
    {
      immediate: true,
    },
  );

  const handleIpDelete = () => {
    selected.value[props.clusterType] = [];
    emits('num-change', 0);
  };

  const handleChange = (value: string) => {
    localValue.value = value as HostSelectType;
    if (value === HostSelectType.MANUAL) {
      isShowInstanceSelecotr.value = true;
    }
    emits('type-change', value);
  };

  // const handleOptionClick = (value: string) => {
  //   if (value === localValue.value) {
  //     isShowInstanceSelecotr.value = true;
  //   }
  // };

  const handleInstancesChange = (selectedValues: InstanceSelectorValues<IValue>) => {
    selected.value = selectedValues;
    const selectedList = selected.value[props.clusterType];
    const { length } = selectedList;
    let count = 0;
    if (length > 0) {
      const selectedIpMap = selectedList.reduce(
        (prevMap, selectedItem) => Object.assign(prevMap, { [selectedItem.ip]: false }),
        {} as Record<string, boolean>,
      );
      count = props.instanceIpList.reduce((prevCount, instanceIp) => {
        if (!(instanceIp in selectedIpMap) || selectedIpMap[instanceIp]) {
          return prevCount;
        }
        selectedIpMap[instanceIp] = true;
        return prevCount + 1;
      }, 0);
    }
    emits('num-change', count);
  };

  const handleInstancesCancel = () => {
    localValue.value = HostSelectType.AUTO;
    emits('type-change', HostSelectType.AUTO);
  };

  const handleIpTextClick = () => {
    isShowInstanceSelecotr.value = true;
  };

  defineExpose<Exposes>({
    resetValue() {
      localValue.value = HostSelectType.AUTO;
      selected.value[props.clusterType] = [];
    },
    getValue(fieldName: string) {
      const formatHost = (host: IValue) => ({
        ip: host.ip,
        bk_host_id: host.bk_host_id,
        bk_cloud_id: host.bk_cloud_id,
        bk_biz_id: currentBizId,
      });
      if (localValue.value === HostSelectType.MANUAL) {
        return textRef.value.getValue().then(() => ({
          [fieldName]: selected.value[props.clusterType].map((item) => formatHost(item)),
        }));
      }
      return Promise.resolve();
    },
  });
</script>

<style lang="less">
  .role-host-select-option {
    display: flex;
    width: 100%;

    .option-count {
      width: 23px;
      height: 16px;
      padding: 0 8px;
      margin-left: auto;
      color: #979ba5;
      background-color: #f0f1f5;
      border-radius: 2px;
    }
  }
</style>
<style lang="less" scoped>
  .render-switch-box {
    padding: 0;
    color: #63656e;

    :deep(.bk-input--text) {
      border: none;
      outline: none;
    }

    .ip-box {
      cursor: pointer;

      .ip-content {
        display: flex;
        align-items: center;

        .ip-text {
          flex: 1;
          white-space: break-spaces;
        }

        .delete-icon {
          display: none;
          color: #979ba5;
        }
      }

      &:hover {
        .delete-icon {
          display: inline-block;
        }
      }
    }
  }
</style>
