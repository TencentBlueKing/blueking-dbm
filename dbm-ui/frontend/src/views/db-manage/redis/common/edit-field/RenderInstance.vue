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
    ref="editRef"
    v-model="localValue"
    :placeholder="t('请输入或从表头批量选择')"
    :rules="rules"
    @focus="handleFocus"
    @input="(value: string | number) => handleInputChange(value as string)" />
</template>

<script lang="ts">
  const instanceMemo: { [key: string]: Record<string, boolean> } = {};
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getRedisInstances } from '@services/source/redis';

  import { ipPort } from '@common/regex';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import { random } from '@utils';

  interface IHostInfo {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
    port: number;
  }

  interface Props {
    data?: string;
  }

  interface Emits {
    (e: 'inputFinish', value: string): void;
  }

  interface Exposes {
    getValue: (isSubmit?: boolean) => Promise<IHostInfo>;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    inputed: () => [],
  });
  const emits = defineEmits<Emits>();

  const instanceKey = `render_cluster_${random()}`;
  instanceMemo[instanceKey] = {};

  const { t } = useI18n();

  const localValue = ref();
  const editRef = ref();

  let isSkipInputFinish = false;

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('目标实例不能为空'),
    },
    {
      validator: (value: string) => ipPort.test(value),
      message: t('目标实例输入格式有误'),
    },
    {
      validator: async (value: string) => {
        const listResult = await getRedisInstances({ instance_address: value });
        if (listResult.results.length && !isSkipInputFinish) {
          emits('inputFinish', value);
        }
        return listResult.results.length > 0;
      },
      message: t('目标实例不存在'),
    },
    {
      validator: (value: string) => {
        const currentClusterSelectMap = instanceMemo[instanceKey];
        const otherClusterMemoMap = { ...instanceMemo };
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
      message: t('目标实例重复'),
    },
  ];

  watchEffect(() => {
    localValue.value = props.data;
  });

  watch(
    localValue,
    () => {
      if (!localValue.value) {
        return;
      }
      instanceMemo[instanceKey] = {};
      instanceMemo[instanceKey][localValue.value] = true;
    },
    {
      immediate: true,
    },
  );

  const handleInputChange = (value: string) => {
    if (value === '') {
      instanceMemo[instanceKey] = {};
    }
  };

  const handleFocus = () => {
    isSkipInputFinish = false;
  };

  onBeforeUnmount(() => {
    delete instanceMemo[instanceKey];
  });

  defineExpose<Exposes>({
    getValue(isSubmit = false) {
      isSkipInputFinish = isSubmit;
      return editRef.value
        .getValue()
        .then(() => localValue.value)
        .catch(() =>
          Promise.reject({
            module: localValue.value,
          }),
        );
    },
  });
</script>
