<template>
  <div>
    <div
      v-for="item in data"
      :key="item.immute_domain"
      class="result-item"
      @click="handleGo(item)">
      <div class="value-text">
        <HightLightText
          :key-word="keyWord"
          :text="item.immute_domain" />
        <div class="intro">
          (域名)
        </div>
      </div>
      <div class="biz-text">
        {{ bizIdNameMap[item.bk_biz_id] }}
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { systemSearchCache } from '@common/cache';

  import { useRedirect } from '@components/system-search/hooks/useRedirect';

  import HightLightText from './components/HightLightText.vue';

  interface Props {
    keyWord: string,
    data: {
      bk_biz_id: number,
      cluster_type: string,
      id: number,
      immute_domain: string,
      name: string
    }[],
    bizIdNameMap: Record<number, string>
  }

  defineProps<Props>();

  const handleRedirect = useRedirect();

  const handleGo = (data: Props['data'][number]) => {
    systemSearchCache.appendItem(data.immute_domain);

    handleRedirect(
      data.cluster_type,
      {
        domain: data.immute_domain,
      },
      data.bk_biz_id,
    );
  };
</script>

