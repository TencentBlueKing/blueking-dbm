<template>
  <EditableTableColumn
    ref="editableTableColumn"
    :append-rules="rules"
    field="cluster.master_domain"
    fixed="left"
    :label="t('目标集群')"
    :loading="isLoading"
    required>
    <template #headAppend>
      <BkButton
        text
        theme="primary"
        @click="handleShowClusterSelector">
        <DbIcon type="batch-host-select" />
      </BkButton>
    </template>
    <EditInput
      v-model="modelValue.master_domain"
      :placeholder="t('请输入或选择集群')" />
    <ClusterSelector
      v-model:is-show="isShowClusterSelector"
      :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER, ClusterTypes.MONGO_REPLICA_SET]"
      :selected="selectedClusters"
      @change="handelClusterChange" />
  </EditableTableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';
  import { Column as EditableTableColumn, Input as EditInput } from '@components/editable-table/Index.vue';

  interface Emits {
    (e: 'batch-edit', value: MongodbModel[]): void;
  }

  interface Exposes {
    setSelectedCluster: (clusterType: string, domain: string) => void;
    resetSelectedCluster: () => void;
  }

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<Partial<ServiceReturnType<typeof filterClusters>[number]>>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      validator: (value: string) => domainRegex.test(value),
      trigger: 'change',
      message: t('目标集群输入格式有误'),
    },
    {
      validator: () => Boolean(modelValue.value.id),
      trigger: 'change',
      message: t('目标集群不存在'),
    },
  ];

  const editableTableColumnRef = useTemplateRef('editableTableColumn');
  const isShowClusterSelector = ref(false);
  const isLoading = ref(false);

  const selectedClusters = shallowRef<{ [key: string]: MongodbModel[] }>({
    [ClusterTypes.MONGO_REPLICA_SET]: [],
    [ClusterTypes.MONGO_SHARED_CLUSTER]: [],
  });

  watch(
    () => modelValue.value.master_domain,
    () => {
      if (!modelValue.value.id && modelValue.value.master_domain) {
        isLoading.value = true;
        modelValue.value.id = undefined;
        filterClusters<MongodbModel>({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          exact_domain: modelValue.value.master_domain,
        })
          .then((data) => {
            if (data.length > 0) {
              [modelValue.value] = data;
            }
          })
          .finally(() => {
            isLoading.value = false;
            editableTableColumnRef.value!.validate();
          });
      }
    },
    {
      immediate: true,
    },
  );

  const handleShowClusterSelector = () => {
    isShowClusterSelector.value = true;
  };

  const handelClusterChange = (selected: { [key: string]: MongodbModel[] }) => {
    selectedClusters.value = selected;
    const clusterList = Object.values(selected).flatMap((selectedList) => selectedList);
    emits('batch-edit', clusterList);
  };

  defineExpose<Exposes>({
    setSelectedCluster(clusterType: string, domain: string) {
      const clustersArr = selectedClusters.value[clusterType!];
      selectedClusters.value[clusterType!] = clustersArr.filter((item) => item.master_domain !== domain);
    },
    resetSelectedCluster() {
      selectedClusters.value[ClusterTypes.MONGO_SHARED_CLUSTER] = [];
      selectedClusters.value[ClusterTypes.MONGO_REPLICA_SET] = [];
    },
  });
</script>
