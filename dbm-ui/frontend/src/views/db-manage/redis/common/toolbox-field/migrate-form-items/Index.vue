<template>
  <BkFormItem
    :label="t('升级类型')"
    property="updateType"
    required>
    <CardCheckbox
      v-model="modelValue.architectureType"
      :desc="t('如 TendisCache 等，迁移过程保持规格、版本不变')"
      icon="cluster"
      style="width: 400px"
      :title="t('集群架构')"
      :true-value="ArchitectureType.CLUSTER" />
    <CardCheckbox
      v-model="modelValue.architectureType"
      class="ml-8"
      :desc="t('支持部分或整机所有实例成对迁移至新主机，版本规格可变')"
      :disabled-tooltips="t('单节点仅支持原地升级')"
      icon="gaokeyong"
      style="width: 400px"
      :title="t('主从架构')"
      :true-value="ArchitectureType.MASTER_SLAVE" />
  </BkFormItem>
  <BkFormItem
    :label="t('迁移类型')"
    property="updateType"
    required>
    <CardCheckbox
      v-model="modelValue.migrateType"
      :desc="t('只迁移目标实例')"
      icon="fill-1"
      style="width: 400px"
      :title="t('实例迁移')"
      :true-value="MigrateType.INSTANCE" />
    <CardCheckbox
      v-model="modelValue.migrateType"
      class="ml-8"
      :desc="t('主机关联的所有实例一并迁移')"
      :disabled="modelValue.architectureType === ArchitectureType.CLUSTER"
      icon="host"
      style="width: 400px"
      :title="t('整机迁移')"
      :true-value="MigrateType.MACHINE" />
  </BkFormItem>
</template>

<script lang="ts">
  export const ArchitectureType = {
    CLUSTER: 'cluster',
    MASTER_SLAVE: 'masterSlave',
  };

  export const MigrateType = {
    INSTANCE: 'instance',
    MACHINE: 'machine',
  };
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  const modelValue = defineModel<{
    architectureType: string;
    migrateType: string;
  }>({
    required: true,
  });
  const { t } = useI18n();
  const router = useRouter();

  watch(
    () => modelValue.value.architectureType,
    () => {
      const routeMap = {
        [ArchitectureType.CLUSTER]: TicketTypes.REDIS_CLUSTER_INS_MIGRATE,
        [ArchitectureType.MASTER_SLAVE]: TicketTypes.REDIS_SINGLE_INS_MIGRATE,
      };
      router.push({
        name: routeMap[modelValue.value.architectureType],
      });
    },
  );
</script>
