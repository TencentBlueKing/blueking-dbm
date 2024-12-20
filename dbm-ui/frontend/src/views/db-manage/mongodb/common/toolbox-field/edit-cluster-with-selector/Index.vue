<template>
  <EditableTableColumn
    ref="editableTableColumn"
    :append-rules="rules"
    field="cluster"
    fixed="left"
    :label="t(label)"
    :loading="isLoading"
    :min-width="300"
    required>
    <template #headAppend>
      <BkButton
        text
        theme="primary"
        @click="handleShowHeadClusterSelector">
        <DbIcon type="batch-host-select" />
      </BkButton>
    </template>
    <EditTextarea
      v-model="localValue"
      :placeholder="t('请输入或选择集群')">
      <template #append>
        <span v-bk-tooltips="t('选择集群')">
          <BkButton
            class="cluster-selector-btn"
            size="small"
            @click="handleShowRowClusterSelector">
            <DbIcon type="host-select" />
          </BkButton>
        </span>
      </template>
    </EditTextarea>
    <ClusterSelector
      :key="clusterTypes.join(',')"
      v-model:is-show="isShowHeadClusterSelector"
      :cluster-types="clusterTypes"
      :selected="selected as MappedProps"
      @change="handleHeadClusterChange" />
    <ClusterSelector
      :key="clusterTypes.join(',')"
      v-model:is-show="isShowRowClusterSelector"
      :cluster-types="clusterTypes"
      :selected="rowSelected as MappedProps"
      @change="handleRowClusterChange" />
  </EditableTableColumn>
</template>

<script setup lang="ts" generic="T extends Record<string, any>">
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import { filterClusters } from '@services/source/dbbase';

  import { domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';
  import { Column as EditableTableColumn, Textarea as EditTextarea } from '@components/editable-table/Index.vue';

  type MappedProps = {
    [K in keyof Props['selected']]: MongodbModel[];
  };

  type ClusterItem = ServiceReturnType<typeof filterClusters>[number];

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
  }

  interface Emits {
    (e: 'batch-edit', value: MongodbModel[]): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    label: '目标集群',
  });
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<Partial<ServiceReturnType<typeof filterClusters>[number]>[]>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      validator: (value: ClusterItem[]) => {
        const unValidClusterList = value.filter((item) => !domainRegex.test(item.master_domain));
        if (unValidClusterList.length > 0) {
          return t('目标集群n输入格式有误', { n: unValidClusterList.map((item) => item.master_domain).join('，') });
        }
        return true;
      },
      trigger: 'change',
      message: t('目标集群输入格式有误'),
    },
    {
      validator: (value: ClusterItem[]) => {
        const unValidClusterList = value.filter((item) => Boolean(!item.id));
        if (unValidClusterList.length > 0) {
          return t('目标集群n不存在', { n: unValidClusterList.map((item) => item.master_domain).join('，') });
        }
        return true;
      },
      trigger: 'blur',
      message: t('目标集群不存在'),
    },
  ];

  const isShowHeadClusterSelector = ref(false);
  const isShowRowClusterSelector = ref(false);
  const isLoading = ref(false);
  const localValue = ref('');

  const rowSelected = computed(() => {
    const selectedClusters = props.clusterTypes.reduce<Record<string, MongodbModel[]>>(
      (prevMap, item) =>
        Object.assign({}, prevMap, {
          [item]: [] as MongodbModel[],
        }),
      {},
    );
    modelValue.value.forEach((clusterItem) => {
      const { id, cluster_type: clusterType, master_domain: masterDomain } = clusterItem;
      if (id && clusterType && masterDomain) {
        selectedClusters[clusterType as keyof typeof selectedClusters].push({
          id,
          master_domain: masterDomain,
        } as MongodbModel);
      }
    });
    return selectedClusters;
  });

  watch(localValue, () => {
    const domainList = localValue.value.split('\n').filter((item) => item);
    const minLength = Math.min(domainList.length, modelValue.value.length);
    let clusterList = modelValue.value;
    clusterList = clusterList.slice(0, minLength).map((item, index) => ({
      master_domain: domainList[index],
    }));
    if (domainList.length > clusterList.length) {
      const newClusterList = domainList.slice(minLength).map((item) => ({
        master_domain: item,
      }));
      clusterList.push(...newClusterList);
    } else if (domainList.length < clusterList.length) {
      clusterList = clusterList.slice(0, domainList.length - 1);
    }
    modelValue.value = clusterList;
  });

  watch(
    () => modelValue.value,
    () => {
      localValue.value = modelValue.value.map((item) => item.master_domain || '').join('\n');
      const domainList = modelValue.value.filter((item) => !item.id && item.master_domain);
      if (domainList.length > 0) {
        isLoading.value = true;
        modelValue.value.forEach((item) => {
          Object.assign(item, { id: undefined });
        });
        filterClusters<MongodbModel>({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          exact_domain: domainList.map((item) => item.master_domain).join(','),
        })
          .then((data) => {
            if (data.length > 0) {
              const clusterMap = data.reduce<Record<string, MongodbModel>>(
                (prevMap, dataItem) =>
                  Object.assign({}, prevMap, {
                    [dataItem.master_domain]: dataItem,
                  }),
                {},
              );
              modelValue.value.forEach((item) => {
                if (item.master_domain && clusterMap[item.master_domain]) {
                  Object.assign(item, clusterMap[item.master_domain]);
                }
              });
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

  const handleShowHeadClusterSelector = () => {
    isShowHeadClusterSelector.value = true;
  };

  const handleShowRowClusterSelector = () => {
    isShowRowClusterSelector.value = true;
  };

  const handleHeadClusterChange = (selected: Record<string, MongodbModel[]>) => {
    const clusterList = Object.values(selected).flatMap((selectedList) => selectedList);
    emits('batch-edit', clusterList);
  };

  const handleRowClusterChange = (selected: Record<string, MongodbModel[]>) => {
    const clusterList = Object.values(selected).flatMap((selectedList) => selectedList);
    modelValue.value = clusterList;
  };
</script>

<style lang="less" scoped>
  .cluster-selector-btn {
    width: 24px;
    font-size: 16px;
    border: none;
    border-radius: 2px;

    &:hover {
      color: #3a84ff;
      background: #f0f1f5;
    }
  }
</style>
