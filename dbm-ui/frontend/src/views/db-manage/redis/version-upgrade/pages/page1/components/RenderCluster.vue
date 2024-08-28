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
  <div
    class="render-cluster-width-relate-cluster"
    :class="{
      'is-editing': isShowEdit,
    }">
    <TableEditInput
      v-show="isShowEdit"
      ref="editRef"
      v-model="localDomain"
      :multi-input="false"
      :rules="rules"
      @error="handleError"
      @focus="handleFocus"
      @submit="handleEditSubmit" />
    <div
      v-show="!isShowEdit"
      @click="handleShowEdit">
      <div class="render-cluster-domain">
        <span>{{ localDomain }}</span>
      </div>
      <div
        v-if="relatedClusterList.length > 0"
        class="related-cluster-list">
        <div
          v-for="item in relatedClusterList"
          :key="item.id">
          {{ item.master_domain }}
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
  const clusterIdMemo: { [key: string]: Record<string, boolean> } = {};
</script>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import { getRedisList } from '@services/source/redis';
  import { findRelatedClustersByClusterIds } from '@services/source/redisToolbox';

  import { ClusterTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import { random } from '@utils';

  import type { IDataRow } from './Row.vue';

  interface Props {
    data: IDataRow;
  }

  interface Emits {
    (e: 'input-finish', value: RedisModel): void;
  }

  interface Exposes {
    getValue: (isSubmit?: boolean) => Promise<number[]>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const instanceKey = `render_cluster_instance_${random()}`;
  clusterIdMemo[instanceKey] = {};

  const editRef = ref();
  const localClusterId = ref(0);
  const localDomain = ref('');
  const isShowEdit = ref(true);
  const isRelateLoading = ref(false);
  const relatedClusterList = shallowRef<
    Array<{
      id: number;
      master_domain: string;
    }>
  >([]);

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
      validator: (value: string) => domainRegex.test(value),
      message: t('目标集群输入格式有误'),
    },
    {
      validator: (value: string) =>
        getRedisList({
          exact_domain: value,
        }).then((data) => {
          const { results } = data;
          if (results.length > 0) {
            localClusterId.value = results[0].id;
            if (!isSkipInputFinish) {
              emits('input-finish', results[0]);
            }
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

  // 通过 ID 获取关联集群
  const fetchRelatedClustersByClusterIds = () => {
    if (props.data.clusterType !== ClusterTypes.REDIS_INSTANCE) {
      return;
    }
    isRelateLoading.value = true;
    findRelatedClustersByClusterIds({
      cluster_ids: [localClusterId.value],
    })
      .then((data) => {
        if (data.length < 1) {
          return;
        }
        const clusterData = data[0];
        relatedClusterList.value = clusterData.related_clusters;
      })
      .finally(() => {
        isRelateLoading.value = false;
      });
  };

  // 同步外部值
  watch(
    () => props.data,
    () => {
      const { clusterId, cluster } = props.data;
      localClusterId.value = clusterId;
      localDomain.value = cluster;
      isShowEdit.value = !clusterId;
    },
    {
      immediate: true,
    },
  );

  watch(
    localClusterId,
    () => {
      if (localClusterId.value) {
        clusterIdMemo[instanceKey] = { [localClusterId.value]: true };
        return;
      }
      clusterIdMemo[instanceKey] = {};
    },
    {
      immediate: true,
    },
  );

  // 获取关联集群
  watchEffect(() => {
    if (!localClusterId.value || props.data.clusterType !== ClusterTypes.REDIS_INSTANCE) {
      return;
    }
    fetchRelatedClustersByClusterIds();
  });

  // 切换编辑状态
  const handleShowEdit = () => {
    isShowEdit.value = true;
    nextTick(() => {
      editRef.value.focus();
    });
  };

  const handleFocus = () => {
    isSkipInputFinish = false;
  };

  // 提交编辑
  const handleEditSubmit = () => {
    isShowEdit.value = false;
  };

  const handleError = (result: boolean) => {
    isShowEdit.value = result;
  };

  onBeforeUnmount(() => {
    delete clusterIdMemo[instanceKey];
  });

  defineExpose<Exposes>({
    getValue(isSubmit = false) {
      isSkipInputFinish = isSubmit;
      const result = _.uniq([localClusterId.value, ...relatedClusterList.value.map((listItem) => listItem.id)]);
      return editRef.value.getValue().then(() => result);
    },
  });
</script>

<style lang="less" scoped>
  .render-cluster-width-relate-cluster {
    position: relative;
    padding: 10px 0;

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
