<template>
  <EditableTableColumn
    ref="editableTableColumn"
    :append-rules="rules"
    :field="field"
    fixed="left"
    :label="t(label)"
    :loading="isLoading"
    :min-width="300"
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
      :key="clusterTypes.join(',')"
      v-model:is-show="isShowClusterSelector"
      :cluster-types="clusterTypes"
      :selected="selected as MappedProps"
      @change="handelClusterChange" />
  </EditableTableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import { filterClusters } from '@services/source/dbbase';

  import { domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';
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
  }

  interface Emits {
    (e: 'batch-edit', value: MongodbModel[]): void;
  }

  withDefaults(defineProps<Props>(), {
    label: '目标集群',
    field: 'cluster.master_domain',
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

  const editableTableColumnRef = useTemplateRef('editableTableColumn');
  const isShowClusterSelector = ref(false);
  const isLoading = ref(false);

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
