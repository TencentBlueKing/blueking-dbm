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
    :is-show-blur="isShowBlur"
    :placeholder="t('请输入或选择集群')"
    :rules="rules"
    @submit="handleInputFinish">
    <template #suspend>
      <slot name="blur" />
    </template>
  </TableEditInput>
</template>

<script lang="ts">
  const clusterIdMemo: { [key: string]: Record<string, boolean> } = {};
</script>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { getMongoList } from '@services/source/mongodb';

  import { domainRegex } from '@common/regex';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import { random } from '@utils';

  interface Props {
    data?: string;
    isShowBlur?: boolean;
  }

  interface Emits {
    (e: 'inputFinish', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<number>;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    isShowBlur: false,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const localClusterId = ref();
  const localValue = ref(props.data);
  const editRef = ref();

  const instanceKey = `render_cluster_${random()}`;
  clusterIdMemo[instanceKey] = {};

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('目标集群不能为空'),
    },
    {
      validator: (value: string) => domainRegex.test(value),
      message: t('目标集群输入格式有误'),
    },
    {
      validator: (value: string) =>
        getMongoList({
          exact_domain: value,
        }).then((data) => {
          if (data.results.length > 0) {
            localClusterId.value = data.results[0].id;
            return true;
          }
          return false;
        }),
      message: t('目标集群不存在'),
    },
    {
      validator: () => {
        const currentClusterSelectMap = clusterIdMemo[instanceKey];
        const otherClusterMemoMap = { ...clusterIdMemo };
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
      message: t('目标集群重复'),
    },
  ];

  // 获取关联集群
  watch(
    localClusterId,
    () => {
      if (!localClusterId.value) {
        return;
      }
      clusterIdMemo[instanceKey][localClusterId.value] = true;
    },
    {
      immediate: true,
    },
  );

  const handleInputFinish = (value: string) => {
    const realValue = _.trim(value);
    localValue.value = realValue;
    emits('inputFinish', realValue);
  };

  onBeforeUnmount(() => {
    clusterIdMemo[instanceKey] = {};
  });

  defineExpose<Exposes>({
    getValue() {
      return editRef.value.getValue().then(() => localClusterId.value);
    },
  });
</script>
