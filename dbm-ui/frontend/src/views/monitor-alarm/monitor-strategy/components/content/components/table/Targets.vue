<template>
  <div>
    <span v-if="targetsDisplay.length === 0">{{ t('业务下全部对象') }}</span>
    <TagBlock
      v-else
      :data="targetsDisplay"
      theme="info" />
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';

  import { MonitorTargetLevel } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  interface Props {
    row: MonitorPolicyModel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const commonOptions = [
    { id: 'eq', name: 'in' },
    { id: 'neq', name: 'not in' },
    { id: 'include', name: 'like' },
    { id: 'exclude', name: 'not like' },
    { id: 'reg', name: 'regex' },
    { id: 'nreg', name: 'nregex' },
  ];
  const promqlOptions = [
    { id: '=', name: 'in' },
    { id: '!=', name: 'not in' },
    { id: '=~', name: 'like' },
    { id: '!~', name: 'not like' },
    { id: '=~', name: 'regex' },
    { id: '!~', name: 'nregex' },
  ];
  const optionMap = Object.fromEntries(commonOptions.concat(promqlOptions).map((item) => [item.id, item.name]));

  const targetsDisplay = computed(() => {
    if (props.row.isChild) {
      const targetItems = props.row.targets
        .filter((item) => item.level === MonitorTargetLevel.CLUSTER)
        .map((item) => item.rule);
      const customItems = props.row.custom_conditions.map((item) => ({
        key: item.key,
        method: item.method,
        value: item.value,
      }));
      return targetItems
        .concat(customItems)
        .filter((item) => item.value.length > 0)
        .map((item) => `${item.key} ${optionMap[item.method]} ${item.value.join(',')}`);
    }
    return [];
  });
</script>
