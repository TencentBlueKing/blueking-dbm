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
  <Column
    field="specId"
    :label="t('规格')"
    :loading="loading"
    :min-width="200"
    required>
    <Select
      v-model="modelValue"
      :list="specList">
      <template #option="{ item }">
        <SpecPanel
          :key="item.value"
          :data="item.specData">
          <div
            class="tendb-slave-apply-option-item"
            :class="{
              active: item.value === modelValue,
            }">
            <span>{{ item.label }}</span>
            <MiniTag
              v-if="item.isCurrent"
              :content="t('当前规格')"
              theme="info" />
            <span
              class="spec-display-count"
              :class="{ 'count-active': item.value === modelValue }">
              {{ item.specData.count }}
            </span>
          </div>
        </SpecPanel>
      </template>
    </Select>
  </Column>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  import { Column, Select } from '@components/editable-table/Index.vue';
  import MiniTag from '@components/mini-tag/index.vue';

  import SpecPanel, { type SpecInfo } from './components/Panel.vue';

  interface IListItem {
    value: number;
    label: string;
    isCurrent: boolean;
    specData: SpecInfo;
  }

  interface Props {
    cluster: {
      bk_cloud_id: number;
      cluster_spec: TendbClusterModel['cluster_spec'];
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<number>({
    default: 0,
  });

  const { t } = useI18n();

  const specList = shallowRef<IListItem[]>([]);

  const { run: fetchSpecList, loading } = useRequest(getResourceSpecList, {
    manual: true,
    onSuccess: async ({ results }) => {
      const countResult = await getSpecResourceCount({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: props.cluster.bk_cloud_id,
        spec_ids: results.map((item) => item.spec_id),
      });
      specList.value = results.map((item) => ({
        value: item.spec_id,
        label: item.spec_name,
        isCurrent: false,
        specData: {
          name: item.spec_name,
          cpu: item.cpu,
          id: item.spec_id,
          mem: item.mem,
          count: countResult[item.spec_id],
          storage_spec: item.storage_spec,
        },
      }));
    },
  });

  watch(
    () => props.cluster,
    () => {
      fetchSpecList({
        spec_cluster_type: 'tendbcluster',
        spec_machine_type: 'proxy',
        limit: -1,
        offset: 0,
      });
    },
  );
</script>
<style lang="less" scoped>
  .tendb-slave-apply-option-item {
    display: flex;
    width: 100%;
    align-items: center;

    .spec-display-count {
      height: 16px;
      min-width: 20px;
      margin-left: auto;
      font-size: 12px;
      line-height: 16px;
      color: @gray-color;
      text-align: center;
      background-color: #f0f1f5;
      border-radius: 2px;
    }

    .count-active {
      color: white;
      background-color: #a3c5fd;
    }
  }
</style>
