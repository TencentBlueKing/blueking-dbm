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
    accessDbs?: string[];
    clusterTypes: string[];
    selected: {
      cluster_name: string;
      cluster_type: ClusterTypes;
      db_module_name?: string;
      isMaster?: boolean;
      master_domain: string;
    }[];
    user?: string;
  }

  interface Exposes {
    formData: typeof formData;
    getValue: () => Promise<{
      params: {
        access_dbs: string[];
        bizId: number;
        source_ips: SourceIp[];
        user: string;
      };
      ticketType: TicketTypes;
    }>;
    init: (data: {
      clusterList: NonNullable<Props['selected']>;
      clusterType: ClusterTypes;
      sourceIpList: HostInfo[];
    }) => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    accessDbs: () => [],
    clusterTypes: () => [ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE],
    selected: () => [],
    user: '',
  });

  const accountType = AccountTypes.MYSQL;
  const targetInstancesRef = ref<InstanceType<typeof TargetInstances>>();
  const sourceIpsRef = ref<InstanceType<typeof SourceIps>>();
  const formRef = ref();
  const formData = reactive({
    access_dbs: [] as string[],
    rules: [] as PermissionRule['rules'],
    source_ips: [] as SourceIp[],
    target_instances: [] as string[],
    user: '',
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
    formData,
    async getValue() {
      await formRef.value.validate();
      return {
        params: {
          access_dbs: formData.access_dbs,
          bizId: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: targetInstancesRef.value!.getClusterType(),
          source_ips: formData.source_ips,
          target_instances: formData.target_instances,
          user: formData.user,
        },
        ticketType: TicketTypes.MYSQL_AUTHORIZE_RULES,
      };
    },
    init(data: Parameters<Exposes['init']>[number]) {
      nextTick(() => {
        const { clusterList, clusterType, sourceIpList } = data;
        sourceIpsRef.value?.init(sourceIpList);
        targetInstancesRef.value?.init(clusterType, clusterList);
      });
    },
  });
</script>
