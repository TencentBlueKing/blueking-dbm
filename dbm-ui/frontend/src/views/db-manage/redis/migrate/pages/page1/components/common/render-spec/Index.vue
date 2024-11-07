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
    <div class="render-spec-box">
      <TableEditSelect
        ref="selectRef"
        v-model="localValue"
        :list="selectList"
        :placeholder="t('请输入或从表头批量选择')"
        :rules="rules"
        @change="(value) => handleChange(value as number)">
        <template #default="{ optionItem, index }">
          <SpecPanel
            :data="selectList[index].specData"
            hide-qps
            placement="right">
            <div class="target-spec-select-option">
              <div
                v-overflow-tips
                class="option-name">
                {{ optionItem.label }}
              </div>
              <!-- <BkTag
                  v-if="index === 0"
                  class="ml-4"
                  size="small"
                  theme="info">
                  {{ t('推荐') }}
                </BkTag> -->
              <BkTag
                v-if="(optionItem.value as number) === currentSpecId"
                class="ml-4"
                size="small"
                theme="info">
                {{ t('当前版本') }}
              </BkTag>
            </div>
          </SpecPanel>
        </template>
      </TableEditSelect>
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  import { ClusterTypes } from '@common/const';

  import TableEditSelect, { type IListItem } from '@components/render-table/columns/select/index.vue';
  import SpecPanel from '@components/render-table/columns/spec-display/Panel.vue';

  import { specClusterMachineMap } from '@views/db-manage/redis/common/const';

  // import SpecPanel from './SpecPanel.vue';

  interface Props {
    data?: {
      cloudId: number;
    };
    isLoading?: boolean;
    selectedSpecId?: number;
    currentSpecId?: number;
  }

  interface Exposes {
    getValue: () => Promise<string>;
  }

  const props = defineProps<Props>();
  const selectRef = ref();
  const localValue = ref(0);
  const selectList = ref<IListItem[]>([]);

  const { t } = useI18n();

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('规格不能为空'),
    },
  ];

  watchEffect(() => {
    localValue.value = props.selectedSpecId || 0;
  });

  watch(
    () => props.data,
    () => {
      if (props.data) {
        getResourceSpecList({
          spec_cluster_type: ClusterTypes.REDIS,
          spec_machine_type: specClusterMachineMap[ClusterTypes.REDIS_INSTANCE],
          limit: -1,
          offset: 0,
        }).then((specResult) => {
          const specList = specResult.results.map((item) => ({
            value: item.spec_id,
            label: item.spec_name,
            specData: {
              name: item.spec_name,
              cpu: item.cpu,
              id: item.spec_id,
              mem: item.mem,
              count: 0,
              storage_spec: item.storage_spec,
            },
          }));
          selectList.value = specList;
          if (specList.length) {
            if (!props.selectedSpecId) {
              localValue.value = specList[0].value;
            }
            getSpecResourceCount({
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: props.data!.cloudId,
              spec_ids: specList.map((item) => item.specData.id),
            }).then((countData) => {
              selectList.value = selectList.value.map((item) => ({
                ...item,
                count: countData[item.specData.id],
              }));
            });
          }
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: number) => {
    localValue.value = value;
  };

  defineExpose<Exposes>({
    getValue() {
      return selectRef.value
        .getValue()
        .then(() => Number(localValue.value))
        .catch(() => Promise.reject(Number(localValue.value)));
    },
  });
</script>

<style lang="less">
  .target-spec-select-option {
    display: flex;
    align-items: center;
    width: 100%;

    .option-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
</style>
<style lang="less" scoped>
  .render-spec-box {
    line-height: 20px;
    color: #63656e;
  }

  .eye {
    font-size: 15px;
    color: #3a84ff;

    &:hover {
      cursor: pointer;
    }
  }
</style>
