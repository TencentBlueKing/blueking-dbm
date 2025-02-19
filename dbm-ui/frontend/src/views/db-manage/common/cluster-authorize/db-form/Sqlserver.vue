<template>
  <DbForm
    ref="formRef"
    class="cluster-authorize"
    form-type="vertical"
    :model="formData">
    <TargetInstances
      ref="targetInstancesRef"
      v-model="formData.target_instances"
      :account-type="accountType"
      :cluster-types="clusterTypes"
      :data="selected" />
    <PermissionRules
      v-model="formData.sqlserver_users"
      :account-type="accountType"
      property="sqlserver_users" />
  </DbForm>
</template>

<script setup lang="ts">
  import type { PermissionRule } from '@services/types';

  import { AccountTypes, ClusterTypes, TicketTypes } from '@common/const';

  import PermissionRules from '@views/db-manage/common/cluster-authorize/components/permission-rules/Index.vue';
  import TargetInstances from '@views/db-manage/common/cluster-authorize/components/TargetInstances.vue';

  interface Props {
    clusterTypes?: string[];
    rules?: PermissionRule['rules'];
    selected?: {
      cluster_name: string;
      cluster_type: ClusterTypes;
      db_module_name?: string;
      isMaster?: boolean;
      master_domain: string;
    }[];
    user?: string;
  }

  interface Exposes {
    getValue: () => Promise<{
      params: {
        cluster_type: ClusterTypes;
        sqlserver_users: {
          access_dbs: string[];
          user: string;
        }[];
        target_instances: string[];
      };
      ticketType: TicketTypes;
    }>;
  }

  const props = withDefaults(defineProps<Props>(), {
    clusterTypes: () => [ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE],
    rules: () => [],
    selected: () => [],
    user: '',
  });

  const accountType = AccountTypes.SQLSERVER;
  const targetInstancesRef = ref<InstanceType<typeof TargetInstances>>();
  const formRef = ref();
  const formData = reactive({
    sqlserver_users: [] as { rules: PermissionRule['rules']; user: string }[],
    target_instances: [] as string[],
  });

  watch(
    () => [props.user, props.rules],
    () => {
      formData.sqlserver_users = [
        {
          rules: props.rules,
          user: props.user,
        },
      ];
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    async getValue() {
      await formRef.value.validate();
      return {
        params: {
          cluster_type: targetInstancesRef.value!.getClusterType(),
          sqlserver_users: formData.sqlserver_users.map((item) => ({
            access_dbs: item.rules.map((rule) => rule.access_db),
            user: item.user,
          })),
          target_instances: formData.target_instances,
        },
        ticketType: TicketTypes.SQLSERVER_AUTHORIZE_RULES,
      };
    },
  });
</script>
