<template>
  <EditableColumn
    ref="editableColumnRef"
    :append-rules="rules"
    :field="field"
    fixed="left"
    :label="label || t('目标集群')"
    :loading="isLoading"
    :min-width="350"
    required>
    <template #headAppend>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-select-button"
        @click="handleShowClusterSelector">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <EditableInput
      v-model="modelValue.master_domain"
      :placeholder="t('请输入或选择集群')"
      @change="handleChange" />
    <ClusterSelector
      :key="clusterTypes.join(',')"
      v-model:is-show="isShowClusterSelector"
      :cluster-types="clusterTypes"
      :selected="selectedClusters"
      :tab-list-config="tabListConfig"
      @change="handelClusterChange" />
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';

  interface Props {
    clusterTypes?: string[];
    field?: string;
    label?: string;
    selected: {
      cluster_type: string;
      id: number;
      master_domain: string;
    }[];
    // eslint-disable-next-line vue/require-default-prop
    setCurrentSpecIdMethod?: (data: MongodbModel) => number;
    tabListConfig?: Record<string, TabConfig>;
  }

  type Emits = (e: 'batch-edit', value: MongodbModel[]) => void;

  const props = withDefaults(defineProps<Props>(), {
    clusterTypes: () => [ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER],
    field: 'cluster.master_domain',
    label: '',
    tabListConfig: undefined,
  });
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<
    Partial<
      {
        current_spec_id: number;
      } & ServiceReturnType<typeof filterClusters>[number]
    >
  >({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('集群域名格式不正确'),
      trigger: 'change',
      validator: (value: string) => !value || domainRegex.test(value),
    },
    {
      message: t('cluster重复', [props.label]),
      trigger: 'change',
      validator: (value: string) => !value || props.selected.filter((item) => item.master_domain === value).length < 2,
    },
    {
      message: t('cluster不存在', [props.label]),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.id),
    },
  ];

  const editableColumnRef = useTemplateRef('editableColumnRef');
  const isShowClusterSelector = ref(false);

  const selectedClusters = computed(() => ({
    [ClusterTypes.MONGO_REPLICA_SET]: props.selected.filter(
      (item) => item.cluster_type === ClusterTypes.MONGO_REPLICA_SET,
    ) as MongodbModel[],
    [ClusterTypes.MONGO_SHARED_CLUSTER]: props.selected.filter(
      (item) => item.cluster_type === ClusterTypes.MONGO_SHARED_CLUSTER,
    ) as MongodbModel[],
  }));

  const { loading: isLoading, run: queryCluster } = useRequest(filterClusters<MongodbModel>, {
    manual: true,
    onSuccess(data) {
      if (data.length > 0) {
        modelValue.value = Object.assign(data[0]!, {
          current_spec_id: props.setCurrentSpecIdMethod ? props.setCurrentSpecIdMethod(data[0]!) : 0,
        });
      } else {
        // 集群不存在，触发校验
        editableColumnRef.value?.validate();
      }
    },
  });

  watch(
    modelValue,
    () => {
      if (modelValue.value.master_domain && !modelValue.value.id) {
        queryCluster({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: props.clusterTypes.join(','),
          exact_domain: modelValue.value.master_domain,
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: string) => {
    modelValue.value = {
      bk_biz_id: 0,
      bk_cloud_id: 0,
      bk_cloud_name: '',
      cluster_name: '',
      cluster_spec: { id: 0 },
      cluster_type: '',
      current_spec_id: 0,
      db_module_id: 0,
      db_module_name: '',
      db_type: '',
      id: 0,
      major_version: '',
      master_domain: value,
      mongos: [],
    } as unknown as MongodbModel;
  };

  const handleShowClusterSelector = () => {
    isShowClusterSelector.value = true;
  };

  const handelClusterChange = (selected: Record<string, MongodbModel[]>) => {
    const clusterList = Object.values(selected).flatMap((selectedList) => selectedList);
    emits('batch-edit', clusterList);
  };
</script>

<style lang="less" scoped>
  .batch-select-button {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
