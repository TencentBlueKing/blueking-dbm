<template>
  <EditableTableColumn
    ref="editableTableColumn"
    :append-rules="rules"
    :field="field"
    fixed="left"
    :label="label || t('目标集群')"
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
    <EditInput
      v-model="modelValue.master_domain"
      :placeholder="t('请输入或选择集群')" />
    <ClusterSelector
      :key="clusterTypes.join(',')"
      v-model:is-show="isShowClusterSelector"
      :cluster-types="clusterTypes"
      :selected="selected as MappedProps"
      :tab-list-config="tabListConfig"
      @change="handelClusterChange" />
  </EditableTableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import { filterClusters } from '@services/source/dbbase';

  import { domainRegex } from '@common/regex';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';
  import { Column as EditableTableColumn, Input as EditInput } from '@components/editable-table/Index.vue';

  type MappedProps = {
    [K in keyof Props['selected']]: MongodbModel[];
  };

  interface Props {
    clusterTypes: string[];
    selected: Record<
      string,
      {
        id: number;
        master_domain: string;
      }[]
    >;
    label?: string;
    field?: string;
    tabListConfig?: Record<string, TabConfig>;
  }

  interface Emits {
    (e: 'batch-edit', value: MongodbModel[]): void;
  }

  withDefaults(defineProps<Props>(), {
    label: '',
    field: 'cluster.master_domain',
    tabListConfig: undefined,
  });
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
      trigger: 'blur',
      message: t('目标集群不存在'),
    },
  ];

  const isShowClusterSelector = ref(false);

  const { loading: isLoading, run: runFilterClusters } = useRequest(filterClusters<MongodbModel>, {
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
