<template>
  <DbForm
    ref="formRef"
    class="cluster-authorize"
    form-type="vertical"
    :model="formData"
    :rules="formRules">
    <TargetClusters
      ref="targetClustersRef"
      v-model="formData.target_instances"
      :account-type="accountType"
      :cluster-types="clusterTypes"
      :data="selected" />
    <SelectorSelectRules
      v-model:rules="formData.rules"
      v-model:user="formData.user"
      :account-type="accountType" />
  </DbForm>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { PermissionRule } from '@services/types';

  import { AccountTypes, ClusterTypes } from '@common/const';

  import SelectorSelectRules from '../components/select-permission-rules/selector-select/Index.vue';
  import TargetClusters from '../components/TargetClusters.vue';

  interface Props {
    accountType: AccountTypes;
    user?: string;
    selected?: {
      master_domain: string;
      cluster_name: string;
      db_module_name?: string;
      isMaster?: boolean;
    }[];
    clusterTypes?: ClusterTypes[];
    rules?: PermissionRule['rules'];
  }

  interface Exposes {
    getValue: () => Promise<{
      target_instances: string[];
      cluster_type: ClusterTypes;
      sqlserver_users: {
        user: string;
        access_dbs: string[];
      }[];
    }>;
  }

  const props = withDefaults(defineProps<Props>(), {
    user: '',
    selected: () => [],
    clusterTypes: () => [ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE],
    rules: () => [],
  });

  const { t } = useI18n();

  const formRules = {
    target_instances: [
      {
        trigger: 'change',
        message: t('请添加目标集群'),
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
  const formRef = ref();
  const formData = reactive({
    target_instances: [] as string[],
    user: '',
    rules: [] as PermissionRule['rules'][],
  });

  watch(
    () => [props.user, props.rules],
    () => {
      formData.user = props.user;
      formData.rules = [props.rules];
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    async getValue() {
      await formRef.value.validate();
      return {
        target_instances: formData.target_instances,
        cluster_type: targetClustersRef.value!.getClusterType(),
        sqlserver_users: formData.rules.map((rule) => ({
          user: formData.user,
          access_dbs: rule.map((mapItem) => mapItem.access_db),
        })),
      };
    },
  });
</script>
