<template>
  <BkFormItem
    :label="t('架构类型')"
    property="updateType"
    required>
    <CardCheckbox
      :desc="t('如 TendisCache 等，迁移过程保持规格、版本不变')"
      icon="cluster"
      :model-value="modelValue.architectureType"
      style="width: 400px"
      :title="t('集群架构')"
      :true-value="ArchitectureType.CLUSTER"
      @update:model-value="handleArchitectureTypeChange" />
    <CardCheckbox
      class="ml-8"
      :desc="t('支持部分或整机所有实例成对迁移至新主机，版本规格可变')"
      :disabled-tooltips="t('单节点仅支持原地升级')"
      icon="gaokeyong"
      :model-value="modelValue.architectureType"
      style="width: 400px"
      :title="t('主从架构')"
      :true-value="ArchitectureType.MASTER_SLAVE"
      @update:model-value="handleArchitectureTypeChange" />
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

  import CardCheckbox from '@views/db-manage/common/db-card-checkbox/CardCheckbox.vue';

  const modelValue = defineModel<{
    architectureType: string;
    migrateType: string;
  }>({
    required: true,
  });
  const { t } = useI18n();
  const router = useRouter();

  /**
   * 两种架构是两个页面：选项不改本页数据，直接跳转，有未保存修改时由路由守卫确认，取消离开则选项保持不变。
   * 不能先改选项再跳：本组件在页面 DbForm 内，DbForm 先于本组件的 watch 把选项变化记为修改，取不到切换前的状态
   */
  const handleArchitectureTypeChange = (value: boolean | string) => {
    const routeMap: Record<string, string> = {
      [ArchitectureType.CLUSTER]: TicketTypes.REDIS_CLUSTER_INS_MIGRATE,
      [ArchitectureType.MASTER_SLAVE]: TicketTypes.REDIS_SINGLE_INS_MIGRATE,
    };
    router.push({
      name: routeMap[value as string],
    });
  };
</script>
