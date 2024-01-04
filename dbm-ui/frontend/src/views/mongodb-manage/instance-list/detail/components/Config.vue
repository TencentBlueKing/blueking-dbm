<template>
  <div
    v-bkloading="{loading: isLoading}"
    class="config-info">
    <DbOriginalTable
      :columns="columns"
      :data="data.conf_items"
      height="100%"
      :show-overflow-tooltip="false" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getLevelConfig } from '@services/source/configs';
  import type { PayloadType } from '@services/source/instanceview';

  import { useGlobalBizs } from '@stores';

  import type { TableColumnRender } from '@/types/bkui-vue';

  interface Props {
    payload:PayloadType
  }

  const props = defineProps<Props>();
  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const isLoading = ref(false);
  const data = shallowRef({
    name: '',
    version: '',
    description: '',
    conf_items: [],
  } as ServiceReturnType<typeof getLevelConfig>);
  const columns = [{
    label: t('参数项'),
    field: 'conf_name',
    render: ({ cell }: TableColumnRender) => <div class="text-overflow" v-overflow-tips>{cell}</div>,
  }, {
    label: t('参数值'),
    field: 'conf_value',
    render: ({ cell }: TableColumnRender) => <div class="text-overflow" v-overflow-tips>{cell}</div>,
  }, {
    label: t('描述'),
    field: 'description',
    render: ({ cell }: TableColumnRender) => <div class="text-overflow" v-overflow-tips>{cell || '--'}</div>,
  }, {
    label: t('重启实例生效'),
    field: 'need_restart',
    width: 200,
    render: ({ cell }: {cell: number}) => (cell === 1 ? t('是') : t('否')),
  }];

  /**
   * 获取集群配置
   */
  function fetchClusterConfig(payload:PayloadType) {
    isLoading.value = true;
    getLevelConfig(Object.assign(payload, {
      bk_biz_id: currentBizId }))
      .then((res) => {
        console.log(res, '33--');
        data.value = res;
      })
      .finally(() => {
        isLoading.value = false;
      });
  }

  watch(() => props.payload, () => {
    if (props.payload) {
      fetchClusterConfig(props.payload);
    }
  }, {
    immediate: true,
  });
</script>

<style lang="less" scoped>
.config-info {
  height: calc(100% - 96px);
  margin: 24px 0;
}
</style>
