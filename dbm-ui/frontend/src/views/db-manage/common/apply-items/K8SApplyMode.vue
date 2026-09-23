<template>
  <DbFormItem
    :label="t('部署类型')"
    property="details.apply_mode"
    required>
    <CardCheckbox
      v-model="modelValue"
      :desc="t('独立 BCS 集群资源，物理隔离，适合对性能/安全有严格要求的场景')"
      :disabled="exclusiveModeDisabled"
      :disabled-tooltips="t('暂不支持')"
      :title="t('独占集群')"
      true-value="ExclusiveMode" />
    <CardCheckbox
      v-model="modelValue"
      class="ml-8"
      :desc="t('共享 BCS 集群资源，弹性调度，适合常规业务场景')"
      :title="t('共享集群')"
      true-value="SharedMode" />
  </DbFormItem>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes, isExclusiveClusterType } from '@common/const';

  import CardCheckbox from '@views/db-manage/common/db-card-checkbox/CardCheckbox.vue';

  interface Props {
    clusterType: ClusterTypes;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  // 仅白名单集群类型支持独占集群，其余保持置灰
  const exclusiveModeDisabled = computed(() => !isExclusiveClusterType(props.clusterType));
</script>
