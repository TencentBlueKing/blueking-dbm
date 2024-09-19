<template>
  <DbForm
    ref="formRef"
    class="cluster-authorize"
    form-type="vertical"
    :model="formData">
    <SourceIps
      ref="sourceIpsRef"
      v-model="formData.source_ips" />
    <TargetInstances
      ref="targetInstancesRef"
      v-model="formData.target_instances"
      :account-type="accountType"
      :cluster-types="clusterTypes"
      :data="selected" />
    <MysqlPermissionRules
      v-model:access-dbs="formData.access_dbs"
      v-model:rules="formData.rules"
      v-model:user="formData.user"
      :account-type="accountType" />
  </DbForm>
</template>

<script setup lang="ts">
  import type { HostInfo, PermissionRule } from '@services/types';

  import { AccountTypes, ClusterTypes, TicketTypes } from '@common/const';

  import MysqlPermissionRules from '@views/db-manage/common/cluster-authorize/components/mysql-permission-rules/Index.vue';
  import SourceIps, { type SourceIp } from '@views/db-manage/common/cluster-authorize/components/SourceIps.vue';
  import TargetInstances from '@views/db-manage/common/cluster-authorize/components/TargetInstances.vue';

  interface Props {
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
      ticketType: TicketTypes;
      params: {
        user: string;
        access_dbs: string[];
        source_ips: SourceIp[];
        bizId: number;
      };
    }>;
    formData: typeof formData;
  }

  const props = withDefaults(defineProps<Props>(), {
    user: '',
    accessDbs: () => [],
    selected: () => [],
    clusterTypes: () => [ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE],
  });

  const accountType = AccountTypes.TENDBCLUSTER;
  const targetInstancesRef = ref<InstanceType<typeof TargetInstances>>();
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
        targetInstancesRef.value?.init(clusterType, clusterList);
      });
    },
    async getValue() {
      await formRef.value.validate();
      return {
        ticketType: TicketTypes.TENDBCLUSTER_AUTHORIZE_RULES,
        params: {
          user: formData.user,
          access_dbs: formData.access_dbs,
          source_ips: formData.source_ips,
          target_instances: formData.target_instances,
          cluster_type: targetInstancesRef.value!.getClusterType(),
          bizId: window.PROJECT_CONFIG.BIZ_ID,
        },
      };
    },
    formData,
  });
</script>
