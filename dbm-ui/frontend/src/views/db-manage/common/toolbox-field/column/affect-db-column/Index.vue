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
  <EditableColumn
    field="affectDb"
    :label="t('受影响的 DB')"
    :loading="loading"
    :min-width="160"
    readonly
    :rowspan="rowspan">
    <template #head>
      <span>{{ t('受影响的 DB') }}</span>
      <span
        v-if="enabled"
        class="custom-required" />
    </template>
    <EditableBlock :placeholder="enabled ? t('自动生成') : '--'">
      <BkButton
        v-if="modelValue.length > 0"
        text
        theme="primary"
        @click="handleClick">
        {{ modelValue.length }}
      </BkButton>
    </EditableBlock>
  </EditableColumn>
  <BkSideslider
    v-model:is-show="isShowSlider"
    :width="900">
    <template #header>
      <span>{{ t('受影响的 DB') }}</span>
      <DbTag class="ml-10">{{ t('源集群：') }}{{ cluster.master_domain }}</DbTag>
    </template>
    <BkLoading
      class="affect-db-sideslider"
      :loading="loading">
      <PrimaryTable
        :data="tableData"
        row-key="dbname">
        <TableColumn
          col-key="dbname"
          :min-width="200"
          :title="t('受影响的 DB')">
          <template #title>
            <span>{{ t('受影响的 DB') }}（{{ tableData.length }}）</span>
          </template>
        </TableColumn>
      </PrimaryTable>
    </BkLoading>
  </BkSideslider>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getClusterDatabaseNameList } from '@services/source/remoteService';

  interface Props {
    /** 源集群，按集群查询该集群的全部 DB */
    cluster: {
      id: number;
      master_domain: string;
    };
    // 逻辑备份不需要查询或提交受影响库。
    enabled?: boolean;
    rowspan?: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    enabled: true,
    rowspan: 1,
  });

  /** 该行源集群的全部 DB，只读自动生成，提交时作为受影响的 DB 上送 */
  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  const isShowSlider = ref(false);

  const tableData = computed(() => modelValue.value.map((dbname) => ({ dbname })));

  const { loading, run: fetchDbList } = useRequest(getClusterDatabaseNameList, {
    manual: true,
    onSuccess(data) {
      if (props.enabled) {
        modelValue.value = data[0]?.databases || [];
      }
    },
  });

  watch(
    () => [props.cluster.id, props.enabled],
    () => {
      if (!props.cluster.id || !props.enabled) {
        modelValue.value = [];
        return;
      }
      fetchDbList({
        cluster_ids: [props.cluster.id],
      });
    },
    {
      immediate: true,
    },
  );

  const handleClick = () => {
    isShowSlider.value = true;
  };
</script>
<style lang="less" scoped>
  .custom-required::after {
    margin-left: 4px;
    line-height: 20px;
    color: #ea3636;
    content: '*';
  }
</style>
<style lang="less">
  .affect-db-sideslider {
    margin: 18px 24px;
  }
</style>
