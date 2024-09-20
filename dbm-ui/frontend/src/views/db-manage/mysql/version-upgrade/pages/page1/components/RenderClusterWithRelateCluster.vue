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
    <span v-show="isShowEdit">
      <TableEditInput
        ref="editRef"
        :model-value="localClusterInfo"
        @cluster-change="handleEditSubmit"
        @error="handleErrorMessageChange" />
    </span>
    <div
      v-show="!isShowEdit"
      @click="handleShowEdit">
      <div class="render-cluster-domain">
        <span>{{ localClusterInfo.domain }}</span>
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

  import { findRelatedClustersByClusterIds } from '@services/source/mysqlCluster';

  import { useGlobalBizs } from '@stores';

  import TableEditInput from '@views/db-manage/mysql/common/edit-field/ClusterNameWithSelector.vue';

  import { random } from '@utils';

  interface Props {
    modelValue?: {
      id: number;
      domain: string;
    };
  }

  interface Emits {
    (e: 'idChange', clusterId: number): void;
  }

  interface Exposes {
    getValue: () => Array<number>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const instanceKey = `render_cluster_instance_${random()}`;
  clusterIdMemo[instanceKey] = {};

  const { currentBizId } = useGlobalBizs();

  const editRef = ref();

  const localClusterInfo = ref({
    id: 0,
    domain: '',
  });

  const isShowEdit = ref(true);
  const isRelateLoading = ref(false);
  const relatedClusterList = shallowRef<
    Array<{
      id: number;
      master_domain: string;
    }>
  >([]);

  // 通过 ID 获取关联集群
  const fetchRelatedClustersByClusterIds = () => {
    isRelateLoading.value = true;
    findRelatedClustersByClusterIds({
      cluster_ids: [localClusterInfo.value.id],
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
      localClusterInfo.value = {
        id,
        domain,
      };
      isShowEdit.value = !id;
    },
    {
      immediate: true,
    },
  );

  // 获取关联集群
  watch(
    () => localClusterInfo.value.id,
    (clusterId) => {
      if (!clusterId) {
        return;
      }
      clusterIdMemo[instanceKey][clusterId] = true;
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
  const handleEditSubmit = (info: { id: number; domain: string }) => {
    if (!info.domain) {
      return;
    }

    const { id, domain } = info;
    localClusterInfo.value = {
      id,
      domain,
    };
    emits('idChange', id);
    isShowEdit.value = false;
  };

  const handleErrorMessageChange = (isError: boolean) => {
    isShowEdit.value = isError;
  };

  onBeforeUnmount(() => {
    clusterIdMemo[instanceKey] = {};
  });

  defineExpose<Exposes>({
    getValue() {
      const result = {
        cluster_ids: _.uniq([localClusterInfo.value.id, ...relatedClusterList.value.map((listItem) => listItem.id)]),
      };
      // 用户输入未完成验证
      if (editRef.value) {
        return editRef.value.getValue().then(() => result);
      }
      // 用户输入错误
      if (!localClusterInfo.value.id) {
        return Promise.reject();
      }
      return Promise.resolve(result);
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
