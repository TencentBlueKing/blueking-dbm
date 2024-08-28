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
    v-model="localDomain"
    :placeholder="t('请输入集群域名或从表头批量选择')"
    :rules="rules" />
</template>
<script lang="ts">
  const clusterIdMemo: { [key: string]: Record<string, boolean> } = {};
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { queryClusters } from '@services/source/mysqlCluster';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import { random } from '@utils';

  interface Props {
    modelValue?: {
      id: number;
      domain: string;
      type?: string;
    };
    onlyOneType?: boolean;
    clusterTypes?: string[];
  }

  interface Emits {
    (e: 'idChange', value: number): void;
  }

  interface Exposes {
    getValue: () => Promise<{
      cluster_id: number;
    }>;
  }

  const props = withDefaults(defineProps<Props>(), {
    modelValue: undefined,
    onlyOneType: false,
    clusterTypes: () => [],
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const instanceKey = `render_cluster_${random()}`;
  clusterIdMemo[instanceKey] = {};

  const editRef = ref();

  const localClusterId = ref(0);
  const localDomain = ref('');

  let isSkipInputFinish = false;

  const rules = [
    {
      validator: (value: string) => {
        if (value) {
          return true;
        }
        return false;
      },
      message: t('目标集群不能为空'),
    },
    {
      validator: (value: string) =>
        queryClusters({
          cluster_filters: [
            {
              immute_domain: value,
            },
          ],
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        }).then((data) => {
          if (data.length > 0) {
            localClusterId.value = data[0].id;
            if (!isSkipInputFinish) {
              emits('idChange', data[0].id);
            }
            return true;
          }
          return false;
        }),
      message: t('目标集群不存在'),
    },
    {
      validator: () => {
        if (!props.onlyOneType) {
          return true;
        }
        const types = new Set(props.clusterTypes.filter((item) => !!item));
        return types.size === 1;
      },
      message: t('只允许提交一种集群类型'),
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

  // 同步外部值
  watch(
    () => props.modelValue,
    () => {
      if (props.modelValue) {
        localClusterId.value = props.modelValue.id;
        localDomain.value = props.modelValue.domain;
      }
    },
    {
      immediate: true,
      deep: true,
    },
  );

  // 获取关联集群
  watch(
    localClusterId,
    () => {
      if (!localClusterId.value) {
        clusterIdMemo[instanceKey] = {};
        return;
      }
      clusterIdMemo[instanceKey] = { [localClusterId.value]: true };
    },
    {
      immediate: true,
    },
  );

  onBeforeUnmount(() => {
    delete clusterIdMemo[instanceKey];
  });

  defineExpose<Exposes>({
    getValue() {
      isSkipInputFinish = true;
      return editRef.value.getValue().then(() => {
        isSkipInputFinish = false;
        return {
          cluster_id: localClusterId.value,
        };
      });
    },
  });
</script>
