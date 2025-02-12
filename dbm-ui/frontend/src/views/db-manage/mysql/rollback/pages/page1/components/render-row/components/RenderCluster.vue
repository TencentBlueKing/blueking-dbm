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
    :placeholder="placeholder || t('请输入集群域名或从表头批量选择')"
    :rules="rules" />
</template>

<script lang="ts">
  const clusterIdMemo: { [key: string]: Record<string, boolean> } = {};

  interface Props {
    modelValue?: IDataRow['clusterData'];
    placeholder?: string;
    unique?: boolean;
  }

  interface Emits {
    (e: 'change', data: IDataRow['clusterData']): void;
  }

  interface Exposes {
    getValue: () => Promise<{
      cluster_id: number;
    }>;
  }
</script>
<script setup lang="ts">
  import { onBeforeUnmount, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { queryClusters } from '@services/source/mysqlCluster';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import { random } from '@utils';

  import type { IDataRow } from '../Index.vue';

  const props = withDefaults(defineProps<Props>(), {
    modelValue: () => ({
      id: 0,
      domain: '',
    }),
    placeholder: '',
    unique: false,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const editRef = ref<InstanceType<typeof TableEditInput>>();
  const localClusterId = ref(0);
  const localDomain = ref('');

  const instanceKey = `render_cluster_${random()}`;
  clusterIdMemo[instanceKey] = {};

  const rules = [
    {
      validator: (domain: string) => {
        if (domain) {
          return true;
        }
        return false;
      },
      message: t('待回档集群不能为空'),
    },
    {
      validator: (domain: string) =>
        queryClusters({
          cluster_filters: [
            {
              immute_domain: domain,
            },
          ],
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        }).then((data) => {
          if (data.length > 0) {
            const {
              id,
              master_domain: domain,
              bk_cloud_id: cloudId,
              bk_cloud_name: cloudName,
              cluster_type: clusterType,
            } = data[0];
            localClusterId.value = id;
            emits('change', {
              id,
              domain,
              cloudId,
              cloudName,
              clusterType,
            });
            clusterIdMemo[instanceKey] = {
              [id]: true,
            };
            return true;
          }
          emits('change', {
            id: 0,
            domain: '',
            cloudId: undefined,
            cloudName: undefined,
            clusterType: '',
          });
          return false;
        }),
      message: t('待回档集群不存在'),
    },
    {
      validator: () => {
        if (!props.unique) {
          return true;
        }
        const otherClusterMemoMap = { ...clusterIdMemo };
        delete otherClusterMemoMap[instanceKey];
        const otherClusterIdMap = Object.values(otherClusterMemoMap).reduce(
          (result, item) => ({
            ...result,
            ...item,
          }),
          {} as Record<string, boolean>,
        );
        return !otherClusterIdMap[localClusterId.value];
      },
      message: t('待回档集群重复'),
    },
  ];

  // 同步外部值
  watch(
    () => props.modelValue,
    () => {
      const { id = 0, domain = '' } = props.modelValue || {};
      localClusterId.value = id;
      localDomain.value = domain;
      if (id) {
        clusterIdMemo[instanceKey] = {
          [id]: true,
        };
      } else {
        clusterIdMemo[instanceKey] = {};
      }
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
      const result = {
        cluster_id: localClusterId.value,
      };
      // 用户输入未完成验证
      if (editRef.value) {
        return editRef.value!.getValue().then(() => result);
      }
      // 用户输入错误
      if (!localClusterId.value) {
        return Promise.reject();
      }
      return Promise.resolve(result);
    },
  });
</script>
