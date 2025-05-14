<template>
  <EditableColumn
    ref="editableTableColumn"
    :append-rules="rules"
    field="cluster.master_domain"
    fixed="left"
    :label="t('目标集群')"
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
    <EditableInput
      v-model="modelValue.master_domain"
      :placeholder="t('请输入或选择集群')" />
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

  import RedisModel from '@services/model/redis/redis';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes, TicketTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector, { type TabItem } from '@components/cluster-selector/Index.vue';

  interface Props {
    selected: {
      id: number;
      master_domain: string;
    }[];
  }

  type Emits = (e: 'batch-edit', value: RedisModel[]) => void;

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
      message: t('目标集群不存在'),
      trigger: 'blur',
      validator: () => Boolean(modelValue.value.id),
    },
    {
      message: t('目标集群重复'),
      trigger: 'blur',
      validator: (value: string) => props.selected.filter((item) => item.master_domain === value).length < 2,
    },
  ];

  const editableTableColumnRef = useTemplateRef('editableTableColumn');

  const isShowClusterSelector = ref(false);
  const isLoading = ref(false);

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      disabledRowConfig: [
        {
          handler: (data: RedisModel) =>
            data.operations.some((item) =>
              [TicketTypes.REDIS_DESTROY, TicketTypes.REDIS_INSTANCE_DESTROY].includes(item.ticket_type as TicketTypes),
            ),
          tip: t('集群删除中无法选择'),
        },
      ],
    },
  } as unknown as Record<ClusterTypes, TabItem>;

  const selectedClusters = computed<Record<string, RedisModel[]>>(() => ({
    [ClusterTypes.REDIS]: props.selected.map(
      (currentCluster) =>
        ({
          id: currentCluster.id,
          master_domain: currentCluster.master_domain,
        }) as RedisModel,
    ),
  }));

  watch(
    () => modelValue.value.master_domain,
    () => {
      if (!modelValue.value.id && modelValue.value.master_domain) {
        isLoading.value = true;
        modelValue.value.id = undefined;
        filterClusters<RedisModel>({
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

  const handelClusterChange = (selected: Record<string, RedisModel[]>) => {
    const clusterList = Object.values(selected).flatMap((selectedList) => selectedList);
    emits('batch-edit', clusterList);
  };
</script>
