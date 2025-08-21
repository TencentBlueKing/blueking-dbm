<template>
  <div>
    <div
      v-for="item in data"
      :key="item.id"
      class="result-item"
      @click="handleGo(item)">
      <div class="value-text">
        <TextHighlight
          :keyword="keyWord"
          :text="getMatchText(item)" />
        <span
          v-if="item.cluster_domain"
          class="intro">
          （{{ item.cluster_domain }}）
        </span>
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
  import TextHighlight from '@components/text-highlight/Index.vue';

  interface Props {
    bizIdNameMap: Record<number, string>;
    data: {
      bk_biz_id: number;
      cluster_domain: string;
      cluster_id: number;
      cluster_type: string;
      id: number;
      ip: string;
      name: string;
      port: string;
    }[];
    keyWord: string;
  }

  const props = defineProps<Props>();

  const handleRedirect = useRedirect();

  const getMatchText = (data: Props['data'][number]) => {
    if (data.name?.indexOf(props.keyWord) > -1) {
      return data.name;
    }
    return `${data.ip}:${data.port}`;
  };

  const handleGo = (data: Props['data'][number]) => {
    systemSearchCache.appendItem(getMatchText(data));

    handleRedirect(
      data.cluster_type,
      {
        instance: `${data.ip}:${data.port}`,
      },
      data.bk_biz_id,
    );
  };
</script>
