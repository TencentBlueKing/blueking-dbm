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
      :placeholder="t('请输入集群域名或从表头批量选择')"
      :rules="rules"
      @error="handleErrorMessageChange"
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
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { findRelatedClustersByClusterIds, queryClusters } from '@services/source/mysqlCluster';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import { random } from '@utils';

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const instanceKey = `render_cluster_instance_${random()}`;
  clusterIdMemo[instanceKey] = {};

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

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
      message: '目标集群不能为空',
    },
    {
      validator: (value: string) =>
        queryClusters({
          cluster_filters: [
            {
              immute_domain: value,
              cluster_type: ClusterTypes.TENDBHA,
            },
          ],
          bk_biz_id: currentBizId,
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

  // 通过 ID 获取关联集群
  const fetchRelatedClustersByClusterIds = () => {
    isRelateLoading.value = true;
    findRelatedClustersByClusterIds({
      cluster_ids: [localClusterId.value],
      bk_biz_id: currentBizId,
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
    () => props.modelValue,
    () => {
      const { id = 0, domain = '' } = props.modelValue || {};
      localClusterId.value = id;
      localDomain.value = domain;
      isShowEdit.value = !id;
    },
    {
      immediate: true,
    },
  );

  // 获取关联集群
  watch(
    localClusterId,
    () => {
      if (!localClusterId.value) {
        return;
      }
      clusterIdMemo[instanceKey][localClusterId.value] = true;
      fetchRelatedClustersByClusterIds();
    },
    {
      immediate: true,
    },
  );

  // 切换编辑状态
  const handleShowEdit = () => {
    isShowEdit.value = true;
    nextTick(() => {
      editRef.value.focus();
    });
  };

  // 提交编辑
  const handleEditSubmit = (value: string) => {
    if (!value) {
      return;
    }

    isShowEdit.value = false;
  };

  const handleErrorMessageChange = (isError: boolean) => {
    isShowEdit.value = isError;
  };

  const handleFocus = () => {
    isSkipInputFinish = false;
  };

  onBeforeUnmount(() => {
    clusterIdMemo[instanceKey] = {};
  });

  defineExpose<Exposes>({
    getValue(isSubmit = false) {
      isSkipInputFinish = isSubmit;
      const result = {
        cluster_ids: _.uniq([localClusterId.value, ...relatedClusterList.value.map((listItem) => listItem.id)]),
      };

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
