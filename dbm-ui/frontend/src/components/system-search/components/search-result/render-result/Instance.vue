<template>
  <div>
    <div
      v-for="item in data"
      :key="item.id"
      class="result-item"
      @click="handleGo(item)">
      <div class="value-text">
        <HightLightText
          :key-word="keyWord"
          :text="getMatchText(item)" />
        <div class="intro">
          ({{ t('实例') }}<span v-if="item.cluster_domain">, {{ item.cluster_domain }}</span
          >)
        </div>
      </div>
      <div class="biz-text">
        {{ bizIdNameMap[item.bk_biz_id] }}
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { systemSearchCache } from '@common/cache';

  import { useRedirect } from '@components/system-search/hooks/useRedirect';

  import HightLightText from './components/HightLightText.vue';

  interface Props {
    keyWord: string;
    data: {
      bk_biz_id: number;
      cluster_id: number;
      cluster_type: string;
      id: number;
      ip: string;
      name: string;
      port: string;
      cluster_domain: string;
    }[];
    bizIdNameMap: Record<number, string>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const handleRedirect = useRedirect();

  const getMatchText = (data: Props['data'][number]) => {
    if (data.name.indexOf(props.keyWord) > -1) {
      return data.name;
    }
    return `${data.ip}:${data.port}`;
  };

  const handleGo = (data: Props['data'][number]) => {
    systemSearchCache.appendItem(data.name);

    handleRedirect(
      data.cluster_type,
      {
        instance: `${data.ip}:${data.port}`,
      },
      data.bk_biz_id,
    );
  };
</script>
