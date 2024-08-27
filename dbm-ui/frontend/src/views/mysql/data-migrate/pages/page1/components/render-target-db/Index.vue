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
  <BkLoading :loading="loading">
    <RenderText
      :key="refreshKey"
      ref="targetDbsRef"
      :data="targetDbList.length"
      :placeholder="t('自动生成')"
      :rules="rules"
      style="color: #3a84ff; cursor: pointer"
      @click="handleOpenTargetDbSlider" />
  </BkLoading>
  <DbSideslider
    v-model:is-show="isShowTargetDbSlider"
    class="silder-main"
    :show-footer="false"
    :width="900">
    <template #header>
      <div class="header-main">
        <span>{{ t('最终DB') }}</span>
        <span class="split-line" />
        <span
          v-overflow-tips
          class="cluster-name"
          >{{ data.sourceCluster }}</span
        >
      </div>
    </template>
    <TargetDbPreview
      :data="data"
      @change="handleTargetDbChange" />
  </DbSideslider>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { showDatabasesWithPatterns } from '@services/source/remoteService';

  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import TargetDbPreview, { type DbsType } from './TargetDbPreview.vue';

  interface Props {
    data: {
      sourceCluster: string;
      sourceClusterId: number;
      targetClusters: number[];
      dbs: string[];
      ignoreDbs: string[];
    };
  }

  interface Emits {
    (e: 'change', value: DbsType): void;
  }

  interface Exposes {
    getValue: () => Promise<string[]>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const targetDbsRef = ref();
  const targetDbList = ref<string[]>([]);
  const existedDbNameList = ref<string[]>([]);
  const isShowTargetDbSlider = ref(false);

  // 处理rules中的message无法展示最新值的问题
  const refreshKey = computed(() => existedDbNameList.value.join('_'));

  const rules = computed(() => [
    {
      validator: () => targetDbList.value.length > 0,
      message: t('不能为空'),
    },
    {
      validator: () => existedDbNameList.value.length === 0,
      message: t('在目标集群已存在 DB： xx，请先修改名称', { n: existedDbNameList.value.join(',') }),
    },
  ]);

  const { loading, run: fetchDatabasesWithPattern } = useRequest(showDatabasesWithPatterns, {
    manual: true,
    onSuccess(dataList) {
      const clusterDbsMap: Record<string, boolean> = {};
      dataList.forEach((item) => {
        if (item.cluster_id === props.data.sourceClusterId) {
          targetDbList.value = item.databases;
        } else {
          const { databases } = item;
          databases.forEach((name) => {
            Object.assign(clusterDbsMap, {
              [name]: true,
            });
          });
        }
      });
      const dbNames = targetDbList.value.filter((name) => clusterDbsMap[name]);
      existedDbNameList.value = dbNames;
    },
  });

  watch(
    () => props.data,
    () => {
      const { sourceClusterId, targetClusters, dbs, ignoreDbs } = props.data;
      if (sourceClusterId || targetClusters.length > 0) {
        const infos = [sourceClusterId, ...targetClusters].map((id) => ({
          cluster_id: id,
          dbs,
          ignore_dbs: ignoreDbs,
        }));
        fetchDatabasesWithPattern({ infos });
      }
    },
    {
      immediate: true,
      deep: true,
    },
  );

  const handleTargetDbChange = (dbs: DbsType) => {
    emits('change', dbs);
  };

  const handleOpenTargetDbSlider = () => {
    if (!props.data.sourceCluster) {
      return;
    }

    isShowTargetDbSlider.value = true;
  };

  defineExpose<Exposes>({
    async getValue() {
      await targetDbsRef.value.getValue();
      return Promise.resolve(targetDbList.value);
    },
  });
</script>
<style lang="less" scoped>
  .silder-main {
    :deep(.bk-sideslider-footer) {
      box-shadow: none;
    }
  }
  .header-main {
    width: 100%;
    display: flex;
    align-items: center;
    .split-line {
      width: 1px;
      height: 14px;
      background: #dcdee5;
      margin: 0 8px;
    }

    .cluster-name {
      flex: 1;
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
      color: #979ba5;
      margin-right: 16px;
    }
  }
</style>
