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
  <BkLoading :loading="isLoading">
    <div
      class="render-cluster-box"
      :style="{ backgroundColor: showDefault ? '#fafbfd' : '#fff' }">
      <span
        v-if="showDefault"
        style="color: #c4c6cc">
        {{ placeholder }}
      </span>
      <template v-else>
        <div
          v-for="item in relatedClusterList"
          :key="item.id"
          v-overflow-tips
          class="cluster-item">
          {{ item.master_domain }}
        </div>
      </template>
    </div>
  </BkLoading>
</template>
<script
  setup
  lang="ts"
  generic="
    T extends {
      ip: string;
    }
  ">
  import { useRequest } from 'vue-request';

  import { checkInstance } from '@services/source/dbbase';

  import { t } from '@locales/index';

  interface Props {
    data?: T;
    role?: string;
    placeholder?: string;
  }

  interface Emits {
    (e: 'change', value: number[]): void;
  }

  interface Exposes {
    getValue: () => Promise<Record<'cluster_ids', number[]>>;
  }

  type InstanceInfos = ServiceReturnType<typeof checkInstance>[number];

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    role: 'master',
    placeholder: t('自动生成'),
  });

  const emits = defineEmits<Emits>();

  const relatedClusterList = shallowRef<InstanceInfos['related_clusters']>([]);

  const showDefault = computed(() => relatedClusterList.value.length === 0);

  const { loading: isLoading, run: fetchChecklInstances } = useRequest(checkInstance, {
    manual: true,
    onSuccess(data) {
      if (data.length === 0) {
        return;
      }

      const [currentData] = data.filter((item) => item.role === props.role);
      relatedClusterList.value = currentData.related_clusters;
      emits(
        'change',
        relatedClusterList.value.map((item) => item.id),
      );
    },
  });

  watch(
    () => props.data,
    (newData, oldData) => {
      if (newData?.ip === oldData?.ip) {
        return;
      }

      relatedClusterList.value = [];
      emits('change', []);
      if (props.data && props.data.ip) {
        fetchChecklInstances({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          instance_addresses: [props.data.ip],
        });
      }
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    getValue() {
      return Promise.resolve({
        cluster_ids: relatedClusterList.value.map((item) => item.id),
      });
    },
  });
</script>
<style lang="less" scoped>
  .render-cluster-box {
    padding: 10px 16px;
    line-height: 20px;
    color: #63656e;

    .cluster-item {
      width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
</style>
