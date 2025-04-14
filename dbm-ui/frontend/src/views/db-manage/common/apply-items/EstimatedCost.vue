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
  <BkFormItem
    v-db-console="'common.specCostEstimate'"
    class="estimated-cost-item"
    :label="t('成本预估')">
    <BkLoading :loading="specCostEstimateLoading">
      <span
        v-if="estimatedCost !== undefined"
        class="estimated-cost">
        {{ t('n元/月', { n: estimatedCost }) }}
      </span>
      <span
        v-else
        class="estimated-cost-placeholder">
        {{ t('请先配置资源') }}
      </span>
    </BkLoading>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { specCostEstimate } from '@services/source/dbresourceResource';

  import { checkDbConsole } from '@utils';

  interface Props {
    params: {
      db_type: string;
      resource_spec: {
        [key: string]: {
          count: number;
          spec_id: number | string;
        };
      };
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const {
    data: estimatedCost,
    loading: specCostEstimateLoading,
    run: runSpecCostEstimate,
  } = useRequest(specCostEstimate, {
    debounceInterval: 200,
    manual: true,
  });

  watch(
    () => props.params.resource_spec,
    () => {
      if (!checkDbConsole('common.specCostEstimate')) {
        return;
      }
      const resouceSpec = Object.entries(props.params.resource_spec).reduce<
        ServiceParameters<typeof specCostEstimate>['resource_spec']
      >((prev, [key, specInfo]) => {
        if (specInfo.count && specInfo.spec_id) {
          return Object.assign(prev, {
            [key]: {
              count: specInfo.count,
              spec_id: specInfo.spec_id,
            },
          });
        }
        return prev;
      }, {});
      if (Object.keys(resouceSpec).length > 0) {
        runSpecCostEstimate({
          db_type: props.params.db_type,
          resource_spec: resouceSpec,
        });
      }
    },
    {
      deep: true,
    },
  );
</script>

<style lang="less" scoped>
  .estimated-cost-item {
    font-size: 12px;

    .estimated-cost {
      font-weight: bolder;
      color: #000;
    }

    .estimated-cost-placeholder {
      color: #c4c6cc;
    }
  }
</style>
