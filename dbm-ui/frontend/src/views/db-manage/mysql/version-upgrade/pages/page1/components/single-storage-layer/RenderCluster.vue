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
  <div class="render-cluster-with-relate-cluster">
    <TableEditInput
      ref="editRef"
      v-model="localDomain"
      :placeholder="t('请输入集群域名或从表头批量选择')"
      :rules="rules"
      @focus="handleFocus" />
  </div>
</template>

<script lang="ts">
  const clusterIdMemo: { [key: string]: Record<string, boolean> } = {};

  interface Props {
    modelValue?: {
      id: number;
      domain: string;
    };
  }

  interface Emits {
    (e: 'idChange', value: number): void;
  }

  interface Exposes {
    getValue: (isSubmit?: boolean) => Array<number>;
  }
</script>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { queryClusters } from '@services/source/mysqlCluster';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import { random } from '@utils';

  const props = withDefaults(defineProps<Props>(), {
    modelValue: undefined,
  });
  const emits = defineEmits<Emits>();

  const instanceKey = `render_cluster_instance_${random()}`;
  clusterIdMemo[instanceKey] = {};

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

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
      message: '目标集群不能为空',
    },
    {
      validator: (value: string) =>
        queryClusters({
          cluster_filters: [
            {
              immute_domain: value,
              cluster_type: ClusterTypes.TENDBSINGLE,
            },
          ],
          bk_biz_id: currentBizId,
        }).then((data) => {
          if (data.length > 0) {
            if (!isSkipInputFinish) {
              emits('idChange', data[0].id);
            }
            return true;
          }
          return false;
        }),
      message: '目标集群不存在',
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
      message: '目标集群重复',
    },
  ];

  // 同步外部值
  watch(
    () => props.modelValue,
    () => {
      const { id = 0, domain = '' } = props.modelValue || {};
      localClusterId.value = id;
      localDomain.value = domain;
    },
    {
      immediate: true,
    },
  );

  const handleFocus = () => {
    isSkipInputFinish = false;
  };

  defineExpose<Exposes>({
    getValue(isSubmit = false) {
      isSkipInputFinish = isSubmit;
      const result = {
        cluster_ids: [localClusterId.value],
      };

      return editRef.value.getValue().then(() => result);
    },
  });
</script>
<style lang="less" scoped>
  .render-cluster-with-relate-cluster {
    position: relative;

    &.is-editing {
      padding: 0;
    }

    .render-cluster-domain {
      display: flex;
      height: 20px;
      padding-left: 16px;
      line-height: 20px;
      align-items: center;
    }

    .related-cluster-list {
      padding-left: 16px;
      font-size: 12px;
      line-height: 20px;
    }
  }
</style>
