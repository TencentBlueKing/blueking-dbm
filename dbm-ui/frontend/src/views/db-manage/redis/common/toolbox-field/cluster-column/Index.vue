<template>
  <EditableColumn
    ref="editableColumnRef"
    :append-rules="rules"
    :field="field"
    fixed="left"
    :label="label || t('目标集群')"
    :loading="loading"
    :min-width="350"
    required>
    <template #headAppend>
      <BkButton
        text
        theme="primary"
        @click="handleShowClusterSelector">
        <DbIcon type="batch-host-select" />
      </BkButton>
    </template>
    <EditableInput
      v-model="modelValue.master_domain"
      :placeholder="t('请输入或选择集群')"
      @change="handleChange" />
    <ClusterSelector
      v-model:is-show="isShowClusterSelector"
      :cluster-types="[ClusterTypes.REDIS]"
      :selected="selectedClusters"
      :tab-list-config="tabListConfig"
      @change="handelClusterChange" />
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RedisModel from '@services/model/redis/redis';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';

  interface Props {
    field?: string;
    label?: string;
    selected: {
      cluster_type: string;
      id: number;
      master_domain: string;
    }[];
    tabListConfig?: Record<string, TabConfig>;
  }

  interface Emits {
    (e: 'batch-edit', value: RedisModel[]): void;
    (e: 'request-success'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    field: 'cluster.master_domain',
    label: '',
    tabListConfig: undefined,
  });
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<Partial<ServiceReturnType<typeof filterClusters>[number]>>({
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
    [ClusterTypes.REDIS]: props.selected as RedisModel[],
  }));

  const { loading, run: queryCluster } = useRequest(filterClusters<RedisModel>, {
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

  watch(
    modelValue,
    () => {
      if (modelValue.value.master_domain && !modelValue.value.id) {
        queryCluster({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          // cluster_type: ClusterTypes.REDIS,
          db_type: DBTypes.REDIS,
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
      id: 0,
      master_domain: value,
    } as RedisModel;
  };

  const handleShowClusterSelector = () => {
    isShowClusterSelector.value = true;
  };

  const handelClusterChange = (selected: Record<string, RedisModel[]>) => {
    const clusterList = Object.values(selected).flatMap((selectedList) => selectedList);
    emits('batch-edit', clusterList);
  };
</script>
