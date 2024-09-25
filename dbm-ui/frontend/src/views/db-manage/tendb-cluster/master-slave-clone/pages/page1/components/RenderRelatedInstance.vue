<template>
  <RenderText
    :data="relatedInstace"
    :loading="loading"
    :placeholder="t('输入主机后自动生成')" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getTendbclusterMachineList } from '@services/source/tendbcluster';

  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  interface Props {
    ip: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const relatedInstace = computed(() => {
    const spiderMachineList = spiderMachineListResult.value?.results || [];
    if (spiderMachineList.length) {
      return spiderMachineList[0].related_instances.map((instanceItem) => instanceItem.instance).join('\n');
    }
    return '';
  });

  const {
    loading,
    data: spiderMachineListResult,
    run: getSpiderMachineListRun,
  } = useRequest(getTendbclusterMachineList, {
    manual: true,
  });

  watch(
    () => props.ip,
    (newIp) => {
      if (newIp) {
        getSpiderMachineListRun({
          ip: newIp,
          instance_role: 'remote_slave',
        });
      }
    },
  );
</script>
