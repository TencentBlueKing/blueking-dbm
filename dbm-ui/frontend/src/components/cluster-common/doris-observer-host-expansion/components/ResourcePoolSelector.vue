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
  <div class="expansion-resource-pool-selector">
    <BkLoading :loading="recommendSpecLoading">
      <div class="form-block">
        <div class="form-block-item">
          <div class="form-block-title">
            {{ t('xx节点规格', { name: data.label.toLocaleLowerCase() }) }}
            <span class="required-flag">*</span>
          </div>
          <BkSelect
            :loading="isResourceSpecLoading"
            :model-value="specId || undefined"
            @change="handleSpecChange">
            <BkOption
              v-for="item in resourceSpecList?.results"
              :key="item.spec_id"
              :label="item.spec_name"
              :popover-delay="0"
              :value="item.spec_id">
              <BkPopover
                :offset="20"
                placement="right"
                theme="light"
                width="580">
                <div style="display: flex; width: 100%; align-items: center">
                  <div>{{ item.spec_name }}</div>
                  <BkTag style="margin-left: auto">{{ specCountMap[item.spec_id] }}</BkTag>
                </div>
                <template #content>
                  <SpecDetail :data="item" />
                </template>
              </BkPopover>
            </BkOption>
          </BkSelect>
        </div>
        <div class="form-block-item">
          <div class="form-block-title">
            <I18nT keypath="扩容至（当前n台）">
              {{ originalHostNums }}
            </I18nT>
            <span class="required-flag">*</span>
          </div>
          <BkInput
            :min="originalHostNums"
            :model-value="machinePairCnt || undefined"
            type="number"
            @change="handleMachinePairCntChange" />
        </div>
      </div>
    </BkLoading>
    <div
      v-if="estimateCapacity > 0"
      class="disk-tips mt-16">
      <span style="padding-right: 4px"> {{ t('预估容量（以最小配置计算）') }}: </span>
      <span class="number">{{ estimateCapacity + data.totalDisk }}</span>
      <span>G</span>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed, ref, shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { fetchRecommendSpec, getResourceSpecList } from '@services/source/dbresourceSpec';

  import type { TExpansionNode } from '@components/cluster-common/host-expansion/Index.vue';
  import SpecDetail from '@components/cluster-common/SpecDetailForPopover.vue';

  interface Props {
    data: TExpansionNode;
    cloudInfo: {
      id: number;
      name: string;
    };
  }

  interface Emits {
    (e: 'change', value: TExpansionNode['resourceSpec'], expansionDisk: TExpansionNode['expansionDisk']): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const specId = ref(props.data.resourceSpec.spec_id);
  const machinePairCnt = ref(props.data.resourceSpec.count + props.data.originalHostList.length);
  const specCountMap = shallowRef<Record<number, number>>({});

  const originalHostNums = computed(() => props.data.originalHostList.length);

  // 资源池预估容量
  const estimateCapacity = computed(() => {
    if (machinePairCnt.value < 1) {
      return 0;
    }
    const currentSpec = _.find(resourceSpecList.value?.results, (item) => item.spec_id === specId.value);
    if (!currentSpec) {
      return 0;
    }
    const storage = currentSpec.storage_spec.reduce((result, item) => result + item.size, 0);
    return storage * machinePairCnt.value;
  });

  const { run: fetchSpecResourceCount } = useRequest(getSpecResourceCount, {
    manual: true,
    onSuccess(data) {
      specCountMap.value = data;
    },
  });

  const { loading: isResourceSpecLoading, data: resourceSpecList } = useRequest(getResourceSpecList, {
    defaultParams: [
      {
        spec_cluster_type: props.data.specClusterType,
        spec_machine_type: props.data.specMachineType,
      },
    ],
    onSuccess(data) {
      fetchSpecResourceCount({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: props.cloudInfo.id,
        spec_ids: data.results.map((item) => item.spec_id),
      });
    },
  });

  // 推荐规格
  const { loading: recommendSpecLoading } = useRequest(fetchRecommendSpec, {
    defaultParams: [
      {
        cluster_id: props.data.clusterId,
        role: props.data.role,
      },
    ],
  });

  const triggerChange = () => {
    emits(
      'change',
      {
        spec_id: specId.value,
        count: Math.max(machinePairCnt.value - originalHostNums.value, 0),
      },
      estimateCapacity.value,
    );
  };

  const handleSpecChange = (value: number) => {
    specId.value = value;
    triggerChange();
  };

  const handleMachinePairCntChange = (value: string) => {
    machinePairCnt.value = Number(value);
    triggerChange();
  };
</script>
<style lang="less">
  .expansion-resource-pool-selector {
    font-size: 12px;

    .form-block {
      display: flex;

      .form-block-title {
        margin-bottom: 6px;
        line-height: 20px;

        .required-flag {
          color: #ea3636;
        }
      }

      .form-block-item {
        flex: 1;

        & ~ .form-block-item {
          margin-left: 32px;
        }
      }
    }

    .disk-tips {
      color: #63656e;
    }
  }
</style>
