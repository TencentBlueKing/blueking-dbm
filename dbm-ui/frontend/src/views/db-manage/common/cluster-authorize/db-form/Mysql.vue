<template>
  <DbForm
    ref="formRef"
    class="cluster-authorize"
    form-type="vertical"
    :model="formData"
    :rules="formRules">
    <SourceIps
      ref="sourceIpsRef"
      v-model="formData.source_ips" />
    <TargetClusters
      ref="targetClustersRef"
      v-model="formData.target_instances"
      :account-type="accountType"
      :cluster-types="clusterTypes"
      :data="selected" />
    <FormItemSelectRules
      v-model:access-dbs="formData.access_dbs"
      v-model:rules="formData.rules"
      v-model:user="formData.user"
      :account-type="accountType" />
  </DbForm>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { HostInfo, PermissionRule } from '@services/types';

  import { AccountTypes, ClusterTypes } from '@common/const';

  import FormItemSelectRules from '../components/select-permission-rules/form-item-select/Index.vue';
  import SourceIps, { type SourceIp } from '../components/SourceIps.vue';
  import TargetClusters from '../components/TargetClusters.vue';

  interface Props {
    accountType: AccountTypes;
    user?: string;
    accessDbs?: string[];
    selected: {
      master_domain: string;
      cluster_name: string;
      db_module_name?: string;
      isMaster?: boolean;
    }[];
    clusterTypes: ClusterTypes[];
  }

  interface Exposes {
    init: (data: {
      clusterType: ClusterTypes;
      clusterList: NonNullable<Props['selected']>;
      sourceIpList: HostInfo[];
    }) => void;
    getValue: () => Promise<{
      user: string;
      access_dbs: string[];
      source_ips: SourceIp[];
      bizId: number;
    }>;
    formData: typeof formData;
  }

  const props = withDefaults(defineProps<Props>(), {
    user: '',
    accessDbs: () => [],
    selected: () => [],
    clusterTypes: () => [ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE],
  });

  const { t } = useI18n();

  const formRules = {
    source_ips: [
      {
        trigger: 'change',
        message: t('请添加访问源'),
        validator: (value: string[]) => value.length > 0,
      },
    ],
    target_instances: [
      {
        trigger: 'change',
        message: t('请添加目标集群'),
        validator: (value: string[]) => value.length > 0,
      },
    ],
    user: [
      {
        required: true,
        trigger: 'blur',
        message: t('请选择账户名'),
      },
    ],
    access_dbs: [
      {
        trigger: 'blur',
        message: t('请选择访问DB'),
        validator: (value: string[]) => value.length > 0,
      },
    ],
    rules: [
      {
        trigger: 'change',
        message: t('请添加权限规则'),
        validator: (value: PermissionRule['rules']) => value.length > 0,
      },
    ],
  };

  const targetClustersRef = ref<InstanceType<typeof TargetClusters>>();
  const sourceIpsRef = ref<InstanceType<typeof SourceIps>>();
  const formRef = ref();
  const formData = reactive({
    source_ips: [] as SourceIp[],
    target_instances: [] as string[],
    user: '',
    access_dbs: [] as string[],
    rules: [] as PermissionRule['rules'],
  });

  watch(
    () => [props.user, props.accessDbs],
    () => {
      formData.user = props.user;
      formData.access_dbs = props.accessDbs;
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    init(data: Parameters<Exposes['init']>[number]) {
      nextTick(() => {
        const { clusterType, clusterList, sourceIpList } = data;
        sourceIpsRef.value?.init(sourceIpList);
        targetClustersRef.value?.init(clusterType, clusterList);
      });
    },
    async getValue() {
      await formRef.value.validate();
      return {
        user: formData.user,
        access_dbs: formData.access_dbs,
        source_ips: formData.source_ips,
        target_instances: formData.target_instances,
        cluster_type: targetClustersRef.value!.getClusterType(),
        bizId: window.PROJECT_CONFIG.BIZ_ID,
      };
    },
    formData,
  });
</script>
