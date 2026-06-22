<template>
  <EditableColumn
    ref="editableColumnRef"
    :append-rules="rules"
    :field="field"
    fixed="left"
    :label="label"
    :loading="loading"
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
  import { useRequest } from 'vue-request';

  import SqlserverHaModel from '@services/model/sqlserver/sqlserver-ha';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';

  import { t } from '@locales/index';

  interface Props {
    /**
     * @description 是否允许重复选择集群
     * @default false
     */
    allowRepeat?: boolean;
    clusterTypes: string[];
    field?: string;
    label?: string;
    selected: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
    }[];
    tabListConfig?: Record<string, TabConfig>;
  }

  interface Emits {
    (e: 'batch-edit', value: SqlserverHaModel[]): void;
    (e: 'request-success'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    allowRepeat: false,
    field: 'cluster.master_domain',
    label: t('目标集群'),
    tabListConfig: undefined,
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<Partial<ServiceReturnType<typeof filterClusters>[number]>>({
    required: true,
  });

  const editableColumnRef = useTemplateRef('editableColumnRef');

  const selectedClusters = computed<Record<string, SqlserverHaModel[]>>(() => ({
    [ClusterTypes.SQLSERVER_HA]: props.selected.filter(
      (item) => item.cluster_type === ClusterTypes.SQLSERVER_HA,
    ) as SqlserverHaModel[],
    [ClusterTypes.SQLSERVER_SINGLE]: props.selected.filter(
      (item) => item.cluster_type === ClusterTypes.SQLSERVER_SINGLE,
    ) as SqlserverHaModel[],
  }));

  const rules = [
    {
      message: t('集群域名格式不正确'),
      trigger: 'change',
      validator: (value: string) => !value || domainRegex.test(value),
    },
    {
      message: t('cluster重复', [props.label]),
      trigger: 'change',
      validator: (value: string) =>
        props.allowRepeat || !value || props.selected.filter((item) => item.master_domain === value).length < 2,
    },
    {
      message: t('cluster不存在', [props.label]),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.id),
    },
  ];

  const isShowClusterSelector = ref(false);

  const { loading, run: queryCluster } = useRequest(filterClusters<SqlserverHaModel>, {
    manual: true,
    onSuccess(data) {
      const [currentCluster] = data;
      if (currentCluster) {
        modelValue.value = currentCluster;
        emits('request-success');
      } else {
        // 集群不存在，触发校验
        editableColumnRef.value?.validate();
      }
    },
  });

  const handleChange = (value: string) => {
    modelValue.value = {
      id: 0,
      master_domain: value,
    } as SqlserverHaModel;
  };

  const handleShowClusterSelector = () => {
    isShowClusterSelector.value = true;
  };

  const handelClusterChange = (selected: Record<string, SqlserverHaModel[]>) => {
    const clusterList = Object.values(selected).flatMap((selectedList) => selectedList);
    emits('batch-edit', clusterList);
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.master_domain && !modelValue.value.id) {
        queryCluster({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: props.clusterTypes.join(','),
          db_type: DBTypes.SQLSERVER,
          exact_domain: modelValue.value.master_domain,
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  .batch-select-button {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
