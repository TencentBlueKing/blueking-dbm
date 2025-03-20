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
    field="spec_id"
    :label="t('新机规格')"
    :loading="loading"
    :min-width="200"
    required>
    <EditableSelect
      v-model="modelValue"
      filterable
      :list="specList">
      <template #option="{ item }">
        <SpecPanel :data="item.specData">
          <template #hover>
            <div class="spec-display">
              <div v-overflow-tips>
                {{ item.label }}
              </div>
              <div class="count">
                {{ item.specData.count }}
              </div>
            </div>
          </template>
        </SpecPanel>
      </template>
    </EditableSelect>
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';
  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  import SpecPanel, { type SpecInfo } from './components/Panel.vue';

  interface Props {
    rowData: {
      host: {
        bk_cloud_id: number;
        bk_host_id: number;
        cluster_id: number;
        cluster_type: MongodbInstanceModel['cluster_type'];
        ip: string;
        machine_type: MongodbInstanceModel['machine_type'];
        master_domain: string;
        related_clusters: {
          id: number;
          master_domain: string;
        }[];
        shard: string;
        spec_config: MongodbInstanceModel['spec_config'];
      };
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<number>({
    required: true,
  });

  const { t } = useI18n();

  const specList = ref<
    {
      isCurrentSpec?: boolean;
      label: string;
      specData: SpecInfo;
      value: string | number;
    }[]
  >([]);

  const { loading, run: fetchSpecResourceCount } = useRequest(getSpecResourceCount, {
    manual: true,
    onSuccess(data) {
      specList.value.forEach((item) => {
        Object.assign(item.specData, {
          count: data[item.specData.id],
        });
      });
    },
  });

  const { run: fetchResourceSpecList } = useRequest(getResourceSpecList, {
    manual: true,
    onSuccess(data) {
      specList.value = data.results.map((item) => ({
        label: item.spec_name,
        specData: {
          count: 0,
          cpu: item.cpu,
          id: item.spec_id,
          mem: item.mem,
          name: item.spec_name,
          storage_spec: item.storage_spec,
        },
        value: item.spec_id,
      }));
      fetchSpecResourceCount({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: props.rowData.host.bk_cloud_id!,
        spec_ids: specList.value.map((item) => item.specData.id),
      });
    },
  });

  watch(
    () => props.rowData.host.machine_type,
    (value) => {
      if (value) {
        fetchResourceSpecList({
          limit: -1,
          offset: 0,
          spec_cluster_type: 'mongodb',
          spec_machine_type: value,
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less" scoped>
  .spec-display {
    display: flex;
    width: 100%;
    flex: 1;
    align-items: center;
    justify-content: space-between;

    .count {
      height: 16px;
      min-width: 20px;
      font-size: 12px;
      line-height: 16px;
      color: @gray-color;
      text-align: center;
      background-color: #f0f1f5;
      border-radius: 2px;
    }
  }
</style>
