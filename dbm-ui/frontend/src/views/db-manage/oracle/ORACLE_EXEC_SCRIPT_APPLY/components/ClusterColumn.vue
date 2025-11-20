<template>
  <EditableColumn
    ref="editableTableColumn"
    :append-rules="rules"
    field="cluster.master_domain"
    fixed="left"
    :label="t('集群')"
    :loading="isLoading"
    :min-width="300"
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
      :placeholder="t('请输入或选择集群')" />
    <ClusterSelector
      v-model:is-show="isShowClusterSelector"
      :cluster-types="[ClusterTypes.ORACLE_PRIMARY_STANDBY, ClusterTypes.ORACLE_SINGLE_NONE]"
      :selected="selectedClusters"
      @change="handelClusterChange" />
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import OracalHaModel from '@services/model/oracle/oracle-ha';
  import { filterClusters } from '@services/source/dbbase';

  import { domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  import { ClusterTypes } from '@/common/const';

  interface Props {
    selected: {
      cluster_type: string;
      id: number;
      master_domain: string;
    }[];
  }

  type Emits = (e: 'batch-edit', value: OracalHaModel[]) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<Partial<ServiceReturnType<typeof filterClusters>[number]>>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('目标集群输入格式有误'),
      trigger: 'change',
      validator: (value: string) => domainRegex.test(value),
    },
    {
      message: t('目标集群重复'),
      trigger: 'blur',
      validator: (value: string) => props.selected.filter((item) => item.master_domain === value).length < 2,
    },
    {
      message: t('目标集群不存在'),
      trigger: 'blur',
      validator: () => Boolean(modelValue.value.id),
    },
  ];

  const isShowClusterSelector = ref(false);

  const selectedClusters = computed(() => ({
    [ClusterTypes.ORACLE_PRIMARY_STANDBY]: props.selected.filter(
      (item) => item.cluster_type === ClusterTypes.ORACLE_PRIMARY_STANDBY,
    ) as OracalHaModel[],
    [ClusterTypes.ORACLE_SINGLE_NONE]: props.selected.filter(
      (item) => item.cluster_type === ClusterTypes.ORACLE_SINGLE_NONE,
    ) as OracalHaModel[],
  }));

  const { loading: isLoading, run: runFilterClusters } = useRequest(filterClusters<OracalHaModel>, {
    manual: true,
    onSuccess(data) {
      if (data.length > 0) {
        [modelValue.value] = data;
      }
    },
  });

  watch(
    () => modelValue.value.master_domain,
    () => {
      if (!modelValue.value.id && modelValue.value.master_domain) {
        modelValue.value.id = undefined;
        runFilterClusters({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          exact_domain: modelValue.value.master_domain,
        });
      }
      if (!modelValue.value.master_domain) {
        modelValue.value.id = undefined;
      }
    },
    {
      immediate: true,
    },
  );

  const handleShowClusterSelector = () => {
    isShowClusterSelector.value = true;
  };

  const handelClusterChange = (selected: Record<string, OracalHaModel[]>) => {
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
