<template>
  <DbQuickSearch
    v-model="searchSelectValue"
    class="mb-16"
    :data="searchSelectData"
    parse-url
    :placeholder="t('请输入或选择条件搜索')" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { SearchAttrs } from '@hooks';

  import { ipPort, ipv4 } from '@common/regex';

  import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

  export type SearchSelectList = QuickSearchProps['data'];

  interface Props {
    isHost?: boolean;
    searchAttrs: SearchAttrs;
    type?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    isHost: false,
    type: '',
  });

  const searchSelectValue = defineModel<Record<string, string>>({
    default: () => ({}),
  });

  const { t } = useI18n();

  const isHideStatus = computed(() => (props.type && props.type === 'redis') || props.isHost);

  const searchSelectData = computed(() => {
    const basicSelct = [
      {
        id: props.isHost ? 'ip' : 'instance',
        name: props.isHost ? 'IP' : t('IP 或 IP:Port'),
        type: 'multiple-input',
        validator: (value: string) => ipPort.test(value) || ipv4.test(value) || t('格式错误'),
      },
      {
        id: 'status',
        list: [
          {
            label: t('正常'),
            value: 'running',
          },
          {
            label: t('异常'),
            value: 'unavailable',
          },
          {
            label: t('重建中'),
            value: 'loading',
          },
        ],
        name: t('实例状态'),
        type: 'multiple',
      },
      {
        id: 'bk_cloud_id',
        list: (props.searchAttrs.bk_cloud_id || []).map((item) => ({
          label: item.name,
          value: item.id,
        })),
        name: t('管控区域'),
        type: 'multiple',
      },
    ] as QuickSearchProps['data'];
    if (isHideStatus.value) {
      basicSelct.splice(1, 1);
    }
    return basicSelct;
  });
</script>
