<template>
  <BkFormItem
    :label="t('架构类型')"
    property="architectureType"
    required>
    <CardCheckbox
      :desc-list="[t('功能说明：将指定副本集迁移至一组新机器'), t('应用场景：减少机器数量，节省成本时使用')]"
      icon="fubenji"
      :model-value="modelValue"
      style="width: 460px"
      :title="t('副本集迁移')"
      :true-value="TicketTypes.MONGODB_REPLICASET_MIGRATE"
      @update:model-value="handleChange">
    </CardCheckbox>
    <CardCheckbox
      class="ml-8"
      :desc="t('支持部分或整机所有实例成对迁移至新主机，版本规格可变')"
      :desc-list="[
        t('功能说明：将同一集群的指定分片迁移至一组同规格的新机器上'),
        t('使用场景：调整分片分布，均衡机器负载时使用'),
      ]"
      icon="fenpianjiqun"
      :model-value="modelValue"
      style="width: 460px"
      :title="t('分片集群迁移')"
      :true-value="TicketTypes.MONGODB_SHARD_MIGRATE"
      @update:model-value="handleChange">
    </CardCheckbox>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@views/db-manage/common/db-card-checkbox/CardCheckbox.vue';

  const modelValue = defineModel<string>({
    required: true,
  });
  const { t } = useI18n();
  const router = useRouter();

  /**
   * 两种架构是两个页面：选项不改本页数据，直接跳转，有未保存修改时由路由守卫确认，取消离开则选项保持不变。
   * 不能先改选项再跳：本组件在页面 DbForm 内，DbForm 先于本组件的 watch 把选项变化记为修改，取不到切换前的状态
   */
  const handleChange = (value: boolean | string) => {
    router.push({
      name: value as string,
    });
  };
</script>
