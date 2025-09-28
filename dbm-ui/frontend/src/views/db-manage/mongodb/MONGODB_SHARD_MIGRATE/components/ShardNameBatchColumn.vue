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
    :append-rules="rules"
    field="batchShard.renderText"
    fixed="left"
    :label="t('目标分片')"
    :loading="isLoading"
    :min-width="350"
    required>
    <template #headAppend>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-host-select"
        @click="handleBatchSelectorShow">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <EditableTextarea
      v-model="modelValue.renderText"
      :placeholder="t('请输入分片，多个分片用分隔符输入')"
      @change="handleInputChange">
      <template #append>
        <span v-bk-tooltips="t('选择分片')">
          <span
            class="batch-host-select"
            @click="handleCellSelectorShow">
            <DbIcon type="host-select" />
          </span>
        </span>
      </template>
    </EditableTextarea>
  </EditableColumn>
  <InstanceSelector
    v-model:is-show="isBatchSelectorShow"
    :cluster-types="['MongodbShard']"
    hide-manual-input
    :selected="batchSelectedInstances"
    :tab-list-config="tabListConfig"
    @change="handleBatchSelectChange" />
  <InstanceSelector
    v-model:is-show="isCellSelectorShow"
    :cluster-types="['MongodbShard']"
    hide-manual-input
    :selected="cellSelectedInstances"
    :tab-list-config="tabListConfig"
    @change="handleCellClusterChange" />
</template>
<script lang="tsx" setup>
  import _ from 'lodash';
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getMongoTopoList } from '@services/source/mongodb';
  import { getMongoShard } from '@services/source/mongodbToolbox';

  import { ClusterTypes } from '@common/const';
  import { batchSplitRegex } from '@common/regex';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  type MongodbShardModel = ServiceReturnType<typeof getMongoShard>['results'][number];

  interface Props {
    selected: {
      instance_address: string;
    }[];
    selectedMap: Record<string, boolean>;
  }

  type Emits = (e: 'batch-edit', list: MongodbShardModel[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    current_spec_id: number;
    renderText: string;
    shards: { [shard_name: string]: MongodbShardModel };
  }>({
    required: true,
  });

  const { t } = useI18n();

  const tabListConfig = {
    MongodbShard: [
      {
        tableConfig: {
          disabledRowConfig: {
            handler: (data: MongodbShardModel, selected?: Record<string, MongodbShardModel[]>) => {
              if (!selected) {
                return true;
              }
              const shardList = Object.values(selected['MongodbShard'] || {});
              if (shardList.length === 0) {
                return false;
              }
              return data.cluster_id !== shardList[0].cluster_id;
            },
            tip: t('不能跨集群选择分片，请先清空已有集群的分片'),
          },
        },
        topoConfig: {
          getTopoList: (params: ServiceParameters<typeof getMongoTopoList>) =>
            getMongoTopoList({ ...params, cluster_type: ClusterTypes.MONGO_SHARED_CLUSTER }),
        },
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  const getDefaultSelected = () => ({
    MongodbShard: [],
  });

  const isLoading = ref(false);
  const isBatchSelectorShow = ref(false);
  const isCellSelectorShow = ref(false);

  const batchSelectedInstances = shallowRef(getDefaultSelected());

  const cellSelectedInstances = computed<InstanceSelectorValues<IValue>>(() => ({
    MongodbShard: Object.values(modelValue.value.shards) as unknown as IValue[],
  }));

  const selectedCounter = computed(() => _.countBy(props.selected, 'shard_name'));

  const rules = [
    {
      message: '',
      trigger: 'blur',
      validator: (value: string) => {
        const list = value.split(batchSplitRegex);
        const seen = new Set<string>();
        const repeats = new Set<string>();
        for (const shardName of list) {
          if (seen.has(shardName) || selectedCounter.value[shardName] > 1) {
            repeats.add(shardName);
          }
          seen.add(shardName);
        }
        return repeats.size > 0 ? t('分片名xx重复', [Array.from(repeats).join(',')]) : true;
      },
    },
    {
      message: '',
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        const notFounds: string[] = [];
        value.split(batchSplitRegex).forEach((item) => {
          if (!props.selectedMap[item]) {
            notFounds.push(item);
          }
        });
        return notFounds.length ? t('分片名xx不存在', [notFounds.join(',')]) : true;
      },
    },
  ];

  watch(
    modelValue,
    () => {
      if (modelValue.value.renderText && _.isEmpty(modelValue.value.shards)) {
        isLoading.value = true;
        const shardNames = modelValue.value.renderText.split(batchSplitRegex);
        getMongoShard({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          shard_names: shardNames.join(','),
        })
          .then((shardListResult) => {
            if (shardListResult.results.length > 0) {
              let shards = {} as UnwrapRef<typeof modelValue>['shards'];
              shardListResult.results.forEach((item) => {
                shards = {
                  ...shards,
                  [item.shard_name]: item,
                };
              });
              modelValue.value.shards = shards;
              modelValue.value.current_spec_id = shardListResult.results[0].related_instance[0].spec_config.id;
            }
          })
          .finally(() => {
            isLoading.value = false;
          });
      }
    },
    {
      immediate: true,
    },
  );

  const handleBatchSelectorShow = () => {
    batchSelectedInstances.value = getDefaultSelected();
    isBatchSelectorShow.value = true;
  };

  const handleCellSelectorShow = () => {
    isCellSelectorShow.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = {
      current_spec_id: 0,
      renderText: value
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter((line) => line.length > 0)
        .join('\n'),
      shards: {},
    };
  };

  const handleBatchSelectChange = (selected: Record<string, MongodbShardModel[]>) => {
    const list = Object.values(selected).flatMap((selectedList) => selectedList);
    emits('batch-edit', list);
  };

  const handleCellClusterChange = (selected: Record<string, MongodbShardModel[]>) => {
    const list = Object.values(selected).flatMap((selectedList) => selectedList);
    handleInputChange(list.map((item) => item.shard_name).join('\n'));
  };
</script>
<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
