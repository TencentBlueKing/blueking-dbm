<template>
  <EditableColumn
    :label="t('关联主库主机')"
    :loading="isLoading"
    readonly
    :width="200">
    <EditableBlock :placeholder="t('输入主机后自动生成')">
      {{ masterIp }}
    </EditableBlock>
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { queryMasterSlavePairs } from '@services/source/redisToolbox';

  interface Props {
    relatedClusters: {
      id: number;
    }[];
    slaveIp: string;
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<Record<string, ServiceReturnType<typeof queryMasterSlavePairs>[number]['masters']>>({
    required: true,
  });

  const { t } = useI18n();

  const isLoading = ref(false);

  const masterIp = computed(() => modelValue.value[props.slaveIp]?.ip || '');

  watch(
    () => props.relatedClusters,
    () => {
      if (props.relatedClusters.length > 0) {
        Promise.all(
          props.relatedClusters.map((item) =>
            queryMasterSlavePairs({
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              cluster_id: item.id,
            }),
          ),
        )
          .then((retArr) => {
            const slaveMasterMap = { ...modelValue.value };
            retArr.forEach((pairs) => {
              if (pairs !== null) {
                pairs.forEach((item) => {
                  slaveMasterMap[item.slave_ip] = item.masters;
                });
              }
            });
            modelValue.value = slaveMasterMap;
          })
          .finally(() => {
            isLoading.value = false;
          });
      }
    },
  );
</script>
