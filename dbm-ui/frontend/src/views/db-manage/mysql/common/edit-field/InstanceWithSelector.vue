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
  <TableEditInput
    ref="inputRef"
    v-model="localValue"
    class="cluster-name-with-selector"
    :placeholder="placeholder ? placeholder : t('请输入IP:Port或从表头批量选择')"
    :rules="rules"
    @blur="() => (isFocused = false)"
    @error="handleInputError"
    @focus="() => (isFocused = true)">
    <template #suspend>
      <BkPopover
        v-if="!isFocused"
        :content="t('选择实例')"
        placement="top"
        :popover-delay="0">
        <div class="edit-btn-wraper">
          <div
            class="edit-btn"
            @click="handleClickSeletor">
            <div class="edit-btn-inner">
              <DbIcon
                class="select-icon"
                type="host-select" />
            </div>
          </div>
        </div>
      </BkPopover>
    </template>
  </TableEditInput>
  <InstanceSelector
    v-model:is-show="isShowInstanceSelecotr"
    :cluster-types="clusterTypes"
    :selected="selectedIntances"
    :tab-list-config="tabListConfig"
    @change="handleInstancesChange" />
</template>
<script lang="ts">
  type InstanceInfo = ServiceReturnType<typeof checkMysqlInstances>[number];

  const instanceWithSelectorMemo: { [key: string]: Record<string, boolean> } = {};
</script>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { checkMysqlInstances } from '@services/source/instances';

  import { ClusterTypes } from '@common/const';
  import { ipPort, ipv4 } from '@common/regex';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';
  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import { random } from '@utils';

  export interface InstanceBasicInfo {
    ip: string;
    port?: number;
    instance_address?: string;
    bk_cloud_id?: number;
    bk_cloud_name?: string;
    bk_host_id?: number;
    cluster_id?: number;
    db_module_id?: number;
    db_module_name?: string;
    master_domain?: string;
    cluster_type?: string;
    related_clusters?: InstanceInfo['related_clusters'];
    related_instances?: {
      cluster_id: number;
      instance_address: string;
    }[];
  }

  interface Props {
    type?: 'instance' | 'cloud-instance' | 'ip'; // instance: ip:port, cloud-instance: cloudId:ip:ipPort, ip: ip
    clusterTypes?: string[];
    placeholder?: string;
    tabListConfig?: Record<ClusterTypes, PanelListType>;
    checkDuplicate?: boolean;
  }

  interface Emits {
    (e: 'instanceChange', value: Required<InstanceBasicInfo>): void;
    (e: 'error', value: boolean): void;
  }

  interface Exposes {
    getValue: () => Promise<Required<InstanceBasicInfo>>;
    focus: () => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    clusterTypes: () => [ClusterTypes.TENDBHA],
    placeholder: '',
    type: 'instance',
    checkDuplicate: true,
    tabListConfig: undefined,
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<InstanceBasicInfo>();

  const { t } = useI18n();

  const inputRef = ref();
  const isFocused = ref(false);
  const isShowInstanceSelecotr = ref(false);
  const localValue = ref('');
  const selectedIntances = shallowRef<InstanceSelectorValues<IValue>>({ [ClusterTypes.TENDBHA]: [] });

  const instanceKey = `instance_${random()}`;
  let modelValueLocal: InstanceBasicInfo;
  instanceWithSelectorMemo[instanceKey] = {};

  const rules = [
    {
      validator: (value: string) => Boolean(_.trim(value)),
      message: t('不能为空'),
    },
    {
      validator: (value: string) => {
        if (props.type === 'instance') {
          return ipPort.test(value);
        }
        if (props.type === 'ip') {
          return ipv4.test(value);
        }
        return true;
      },
      message: t('格式不正确'),
    },
    {
      validator: (value: string) =>
        checkMysqlInstances({
          bizId: window.PROJECT_CONFIG.BIZ_ID,
          instance_addresses: [value],
        }).then((data) => {
          if (data.length < 1) {
            return false;
          }

          const [instanceData] = data;
          instanceWithSelectorMemo[instanceKey][instanceData.instance_address] = true;
          if (
            !modelValue.value?.instance_address ||
            modelValueLocal?.instance_address !== instanceData.instance_address
          ) {
            modelValueLocal = _.cloneDeep({
              ...instanceData,
              related_instances: data.map((item) => ({
                cluster_id: item.cluster_id,
                instance_address: item.instance_address,
              })),
            });
            modelValue.value = modelValueLocal;
            emits('instanceChange', modelValueLocal as Required<InstanceBasicInfo>);
          }
          return true;
        }),
      message: t('实例不存在'),
    },
    {
      validator: () => {
        if (!props.checkDuplicate) {
          return true;
        }
        const currentClusterSelectMap = instanceWithSelectorMemo[instanceKey];
        const otherClusterMemoMap = { ...instanceWithSelectorMemo };
        delete otherClusterMemoMap[instanceKey];

        const otherClusterIdMap = Object.values(otherClusterMemoMap).reduce(
          (result, item) => ({
            ...result,
            ...item,
          }),
          {} as Record<string, boolean>,
        );

        const currentSelectClusterIdList = Object.keys(currentClusterSelectMap);
        for (let i = 0; i < currentSelectClusterIdList.length; i++) {
          if (otherClusterIdMap[currentSelectClusterIdList[i]]) {
            return false;
          }
        }
        return true;
      },
      message: t('实例/IP重复'),
    },
  ];

  watch(
    () => modelValue.value,
    () => {
      if (!modelValue.value || !modelValue.value.ip) {
        return;
      }

      if (props.type === 'instance') {
        localValue.value = `${modelValue.value.ip}:${modelValue.value.port}`;
      } else if (props.type === 'ip') {
        localValue.value = modelValue.value.ip;
      } else {
        localValue.value = `${modelValue.value.bk_cloud_id}:${modelValue.value.ip}:${modelValue.value.port}`;
      }
      if (modelValueLocal?.ip !== modelValue.value?.ip) {
        setTimeout(() => {
          inputRef.value.getValue();
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleClickSeletor = () => {
    isShowInstanceSelecotr.value = true;
  };

  // 批量选择
  const handleInstancesChange = (selected: InstanceSelectorValues<IValue>) => {
    selectedIntances.value = selected;
    const list = _.flatMap(Object.values(selected));
    if (props.type === 'instance') {
      localValue.value = list[0].instance_address;
    } else if (props.type === 'ip') {
      localValue.value = list[0].ip;
    } else {
      localValue.value = list[0].instance_address;
    }

    window.changeConfirm = true;
    setTimeout(() => {
      inputRef.value.getValue();
    });
  };

  const handleInputError = (value: boolean) => {
    emits('error', value);
  };

  onBeforeUnmount(() => {
    delete instanceWithSelectorMemo[instanceKey];
  });

  defineExpose<Exposes>({
    getValue() {
      return inputRef.value.getValue().then(() => modelValue.value);
    },
    focus() {
      inputRef.value.focus();
    },
  });
</script>
<style lang="less" scoped>
  .cluster-name-with-selector {
    &:hover {
      :deep(.edit-btn-wraper) {
        display: block;
      }
    }
  }

  .edit-btn-wraper {
    display: none;

    .edit-btn {
      display: flex;
      width: 24px;
      height: 40px;
      align-items: center;

      .edit-btn-inner {
        display: flex;
        width: 24px;
        height: 24px;
        cursor: pointer;
        border-radius: 2px;
        align-items: center;
        justify-content: center;

        .select-icon {
          font-size: 16px;
          color: #979ba5;
        }

        &:hover {
          background: #f0f1f5;

          .select-icon {
            color: #3a84ff;
          }
        }
      }
    }
  }
</style>
