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
      v-model="formData.mongo_users"
      :account-type="accountType"
      property="mongo_users" />
  </DbForm>
</template>

<script setup lang="ts">
  import type { PermissionRule } from '@services/types';

  import { AccountTypes, ClusterTypes, TicketTypes } from '@common/const';

  import PermissionRules from '@views/db-manage/common/cluster-authorize/components/permission-rules/Index.vue';
  import TargetInstances from '@views/db-manage/common/cluster-authorize/components/TargetInstances.vue';

  interface Props {
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
      ticketType: TicketTypes;
      params: {
        target_instances: string[];
        cluster_type: ClusterTypes;
        mongo_users: {
          user: string;
          access_dbs: string[];
        }[];
      };
    }>;
  }

  const props = withDefaults(defineProps<Props>(), {
    user: '',
    selected: () => [],
    clusterTypes: () => [ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER, ClusterTypes.MONGODB],
    rules: () => [],
  });

  const accountType = AccountTypes.MONGODB;
  const targetInstancesRef = ref<InstanceType<typeof TargetInstances>>();
  const formRef = ref();
  const formData = reactive({
    target_instances: [] as string[],
    mongo_users: [] as { user: string; rules: PermissionRule['rules'] }[],
  });

  watch(
    () => [props.user, props.rules],
    () => {
      formData.mongo_users = [
        {
          user: props.user,
          rules: props.rules,
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
        ticketType: TicketTypes.MONGODB_AUTHORIZE_RULES,
        params: {
          target_instances: formData.target_instances,
          cluster_type: targetInstancesRef.value!.getClusterType(),
          mongo_users: formData.mongo_users.map((item) => ({
            user: item.user,
            access_dbs: item.rules.map((rule) => rule.access_db),
          })),
        },
      };
    },
  });
</script>
