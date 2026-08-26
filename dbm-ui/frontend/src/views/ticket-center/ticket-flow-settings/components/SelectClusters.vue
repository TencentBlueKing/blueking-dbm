<template>
  <DbForm
    form-type="vertical"
    :model="formModel">
    <FormItemWithHint
      ref="formItemRef"
      class="mb-48"
      :label="t('集群')"
      :model="modelValue"
      property="cluster_ids"
      required
      :rules="clusterRepeatRules">
      <DbTagInput
        v-model="selectedDomains"
        :content-width="500"
        :list="tagInputList"
        multiple
        :placeholder="t('输入域名（多域名以换行、空格、竖线、; 分隔，回车完成输入）')"
        @change="handleChange" />
      <template #hint>
        {{ t('同一集群仅可归属一条按集群子策略') }}
      </template>
    </FormItemWithHint>
  </DbForm>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { queryAllTypeCluster } from '@services/source/dbbase';
  import { checkTicketFlowConfigClusterRepeat, type ClusterIdItem } from '@services/source/ticket';

  import { DBTypes, queryClusterTypes } from '@common/const';

  import FormItemWithHint from '@components/form-item-with-hint/Index.vue';

  interface Props {
    bizId: number;
    /** 当前编辑的子策略 id，仅编辑态传入（用于后端重复校验排除自身） */
    configId?: number;
    dbType: DBTypes;
    /** 当前编辑的单据类型（用于后端重复校验入参） */
    ticketType: string;
  }

  interface Exposes {
    clearValidate: () => void;
    /** 校验并返回 cluster_ids 结构（含 id/immute_domain） */
    getValue: () => Promise<ClusterIdItem[]>;
  }

  const props = defineProps<Props>();

  // 父组件仅存集群 id 列表
  const modelValue = defineModel<number[]>({
    required: true,
  });

  const { t } = useI18n();

  const formItemRef = ref<InstanceType<typeof FormItemWithHint>>();

  // BkForm 值上下文：property=cluster_ids 由此取值做 required + 重复校验，
  // 直接派生自 modelValue，无需手动同步
  const formModel = computed(() => ({ cluster_ids: modelValue.value }));

  // 全量集群列表（id/immute_domain），用于回填、转换与组装提交结构
  const clusterList = ref<ClusterIdItem[]>([]);

  const tagInputList = computed(() =>
    clusterList.value.map((item) => ({ id: item.immute_domain, name: item.immute_domain })),
  );

  const { run: fetchData } = useRequest(queryAllTypeCluster, {
    manual: true,
    onSuccess(list) {
      clusterList.value = list.map((item) => ({ id: item.id, immute_domain: item.immute_domain }));
    },
  });

  // 按集群子策略重复校验：blur / 提交时调后端拦截重复集群；
  // 缓存最近一次入参与错误，blur 恢复时复用避免多调一次接口
  const repeatValidateCache = ref<{ clusterIds: string; error: string }>({ clusterIds: '', error: '' });

  const clusterRepeatRules = [
    {
      trigger: 'blur',
      validator: async (value: number[]) => {
        if (!value?.length || !props.bizId || !props.ticketType) return true;
        const clusterIds = value.join(',');
        if (repeatValidateCache.value.clusterIds === clusterIds) {
          return repeatValidateCache.value.error || true;
        }
        const result = await checkTicketFlowConfigClusterRepeat({
          bk_biz_id: props.bizId,
          cluster_ids: clusterIds,
          config_id: props.configId,
          ticket_type: props.ticketType,
        });
        const repeatDomains = (result || [])
          .filter((item) => item.validate)
          .map((item) => clusterList.value.find((cluster) => cluster.id === item.id)?.immute_domain)
          .filter((domain): domain is string => !!domain);
        const error =
          repeatDomains.length === 0
            ? ''
            : t('集群 clusters 已在其他按集群子策略中，不可重复', { clusters: repeatDomains.join('、') });
        repeatValidateCache.value = { clusterIds, error };
        return error || true;
      },
    },
  ];

  // id ↔ 域名 互查
  const getDomainById = (id: number) => clusterList.value.find((item) => item.id === id)?.immute_domain;
  const getIdByDomain = (domain: string) => clusterList.value.find((item) => item.immute_domain === domain)?.id;

  // DbTagInput 以域名驱动，modelValue 以 id 存储
  const selectedDomains = computed<string[]>({
    get: () => modelValue.value.map(getDomainById).filter((domain): domain is string => !!domain),
    set: (domains: string[]) => {
      modelValue.value = domains.map(getIdByDomain).filter((id): id is number => id !== undefined);
    },
  });

  watch(
    () => props.bizId,
    () => {
      if (props.bizId) {
        fetchData({
          bk_biz_id: props.bizId,
          cluster_types: queryClusterTypes[props.dbType as keyof typeof queryClusterTypes].join(','),
          limit: -1,
        });
      }
    },
    {
      immediate: true,
    },
  );

  // 延迟到 nextTick 校验：避免 model 变更后 FormItemWithHint 内部 watch 立即 clearValidate
  const handleChange = () => {
    nextTick(() => formItemRef.value?.validate?.());
  };

  defineExpose<Exposes>({
    clearValidate: () => formItemRef.value?.clearValidate?.(),
    async getValue() {
      // validate 失败会 reject，由父组件捕获后不提交
      await formItemRef.value?.validate?.();
      return modelValue.value
        .map((id) => clusterList.value.find((item) => item.id === id))
        .filter((item): item is ClusterIdItem => !!item);
    },
  });
</script>
