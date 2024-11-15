<template>
  <div>
    <div
      v-for="item in data"
      :key="item.name"
      class="result-item"
      @click="handleGo(item)">
      <TextOverflowLayout>
        <div class="value-text">
          <HightLightText
            class="keyword-highlight"
            :key-word="keyWord"
            :text="item.name" />
          <div class="intro">（{{ item.immute_domain }}）</div>
        </div>
      </TextOverflowLayout>
      <div class="biz-text">
        {{ bizIdNameMap[item.bk_biz_id] }}
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { systemSearchCache } from '@common/cache';

  import { useRedirect } from '@components/system-search/hooks/useRedirect';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import HightLightText from './components/HightLightText.vue';

  interface Props {
    keyWord: string;
    data: {
      bk_biz_id: number;
      cluster_type: string;
      id: number;
      immute_domain: string;
      name: string;
    }[];
    bizIdNameMap: Record<number, string>;
  }

  defineProps<Props>();

  const handleRedirect = useRedirect();

  const handleGo = (data: Props['data'][number]) => {
    systemSearchCache.appendItem(data.name);

    handleRedirect(
      data.cluster_type,
      {
        name: data.name,
      },
      data.bk_biz_id,
    );
  };
</script>
