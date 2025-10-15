<template>
  <BkFormItem
    :label="t('架构类型')"
    property="architectureType"
    required>
    <CardCheckbox
      v-model="modelValue"
      :desc-list="[t('功能说明：将指定副本集迁移至一组新机器'), t('应用场景：减少机器数量，节省成本时使用')]"
      icon="fubenji"
      style="width: 460px"
      :title="t('副本集迁移')"
      :true-value="TicketTypes.MONGODB_REPLICASET_MIGRATE">
    </CardCheckbox>
    <CardCheckbox
      v-model="modelValue"
      class="ml-8"
      :desc="t('支持部分或整机所有实例成对迁移至新主机，版本规格可变')"
      :desc-list="[
        t('功能说明：将同一集群的指定分片迁移至一组同规格的新机器上'),
        t('使用场景：调整分片分布，均衡机器负载时使用'),
      ]"
      icon="fenpianjiqun"
      style="width: 460px"
      :title="t('分片集群迁移')"
      :true-value="TicketTypes.MONGODB_SHARD_MIGRATE">
    </CardCheckbox>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  const modelValue = defineModel<string>({
    required: true,
  });
  const { t } = useI18n();
  const router = useRouter();

  watch(modelValue, () => {
    router.push({
      name: modelValue.value,
    });
  });
</script>
