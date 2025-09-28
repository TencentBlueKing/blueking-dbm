<template>
  <EditableColumn
    ref="editableTableColumn"
    :append-rules="rules"
    field="batchCluster.renderText"
    fixed="left"
    :label="t('目标集群')"
    :loading="loading"
    :min-width="300"
    required>
    <template #headAppend>
      <BkButton
        text
        theme="primary"
        @click="handleBatchSelectorShow">
        <DbIcon type="batch-host-select" />
      </BkButton>
    </template>
    <EditableTextarea
      v-model="modelValue.renderText"
      :placeholder="t('请输入集群域名_多个集群用分隔符输入')"
      @change="handleInputChange">
      <template #append>
        <span v-bk-tooltips="t('选择集群')">
          <span
            class="batch-host-select"
            @click="handleCellSelectorShow">
            <DbIcon type="host-select" />
          </span>
        </span>
      </template>
    </EditableTextarea>
  </EditableColumn>
  <ClusterSelector
    v-model:is-show="isBatchSelectorShow"
    :cluster-types="[ClusterTypes.MONGO_REPLICA_SET]"
    :selected="batchSelectedClusters"
    @change="handleBatchSelectChange" />
  <ClusterSelector
    v-model:is-show="isCellSelectorShow"
    :cluster-types="[ClusterTypes.MONGO_REPLICA_SET]"
    :selected="cellSelectedClusters"
    @change="handleCellClusterChange" />
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { batchSplitRegex, domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  interface Props {
    selected: {
      id: number;
      master_domain: string;
    }[];
    selectedMap: Record<string, boolean>;
  }

  type Emits = (e: 'batch-edit', value: MongodbModel[]) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    clusters: Record<
      string,
      {
        bk_cloud_id: number;
        cluster_spec: MongodbModel['cluster_spec'];
        cluster_type: string;
        disaster_tolerance_level: string;
        id: number;
        major_version: string;
        master_domain: string;
        mongodb: MongodbModel['mongodb'];
        shard_node_count: number;
      }
    >;
    related_instances: {
      domain: string;
      instances: string[];
    }[];
    renderText: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const isBatchSelectorShow = ref(false);
  const isCellSelectorShow = ref(false);

  const batchSelectedClusters = computed<Record<string, MongodbModel[]>>(() => ({
    [ClusterTypes.MONGO_REPLICA_SET]: props.selected as MongodbModel[],
  }));

  const cellSelectedClusters = computed<Record<string, MongodbModel[]>>(() => ({
    [ClusterTypes.MONGO_REPLICA_SET]: props.selected as MongodbModel[],
  }));

  const selectedCounter = computed(() => _.countBy(props.selected, 'master_domain'));

  const rules = [
    {
      message: t('集群域名格式不正确'),
      trigger: 'blur',
      validator: (value: string) => !value || value.split(batchSplitRegex).every((item) => domainRegex.test(item)),
    },
    {
      message: '',
      trigger: 'blur',
      validator: (value: string) => {
        const list = value.split(batchSplitRegex);
        const seen = new Set<string>();
        const repeats = new Set<string>();
        for (const domain of list) {
          if (seen.has(domain) || selectedCounter.value[domain] > 1) {
            repeats.add(domain);
          }
          seen.add(domain);
        }
        return repeats.size > 0 ? t('目标集群xx重复', [Array.from(repeats).join(',')]) : true;
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
        return notFounds.length ? t('目标集群xx不存在', [notFounds.join(',')]) : true;
      },
    },
  ];

  const { loading, run: queryCluster } = useRequest(filterClusters<MongodbModel>, {
    manual: true,
    onSuccess: (clusterList) => {
      if (clusterList.length > 0) {
        let clusters = {} as UnwrapRef<typeof modelValue>['clusters'];
        clusterList.forEach((item) => {
          clusters = {
            ...clusters,
            [item.master_domain]: {
              bk_cloud_id: item.bk_cloud_id,
              cluster_spec: item.cluster_spec,
              cluster_type: item.cluster_type,
              disaster_tolerance_level: item.disaster_tolerance_level,
              id: item.id,
              major_version: item.major_version,
              master_domain: item.master_domain,
              mongodb: item.mongodb,
              shard_node_count: item.shard_node_count,
            },
          };
        });
        modelValue.value.clusters = clusters;
      }
    },
  });

  watch(
    modelValue,
    () => {
      if (modelValue.value.renderText && _.isEmpty(modelValue.value.clusters)) {
        queryCluster({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: ClusterTypes.MONGO_REPLICA_SET,
          db_type: DBTypes.MONGODB,
          exact_domain: modelValue.value.renderText.split(batchSplitRegex).join(','),
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleBatchSelectorShow = () => {
    isBatchSelectorShow.value = true;
  };

  const handleCellSelectorShow = () => {
    isCellSelectorShow.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = {
      clusters: {},
      related_instances: [],
      renderText: value
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter((line) => line.length > 0)
        .join('\n'),
    };
  };

  const handleBatchSelectChange = (selected: Record<string, MongodbModel[]>) => {
    const clusterList = Object.values(selected).flatMap((selectedList) => selectedList);
    emits('batch-edit', clusterList);
  };

  const handleCellClusterChange = (selected: Record<string, MongodbModel[]>) => {
    const list = Object.values(selected).flatMap((selectedList) => selectedList);
    handleInputChange(list.map((item) => item.master_domain).join('\n'));
  };
</script>

<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
