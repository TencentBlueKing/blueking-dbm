<template>
  <div
    ref="rootRef"
    v-bk-tooltips="{
      disabled: !Boolean(text),
      content: text,
      allowHtml: true,
      extCls: 'db-app-select-tooltips',
    }"
    class="db-app-select-text">
    <div
      class="db-app-select-name"
      :style="{
        'max-width': text ? '175px' : 'unset',
        flex: text ? '1 0 auto' : 'unset',
      }">
      {{ data.name }}
    </div>
    <div class="db-app-select-desc">
      <div>(#{{ data.bk_biz_id }}</div>
      <div
        v-if="data.english_name"
        class="db-app-select-en-name">
        , {{ data.english_name }}
      </div>
      <div>)</div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { onMounted, ref } from 'vue';

  import { getBizs } from '@services/source/cmdb';

  import { calcTextWidth } from '@utils';

  defineProps<{
    data: ServiceReturnType<typeof getBizs>[number];
  }>();

  const rootRef = ref<HTMLElement>();
  const text = ref('');

  onMounted(() => {
    setTimeout(() => {
      const renderText = rootRef.value!.innerText.replace(/\n/g, '');

      const width = calcTextWidth(renderText, rootRef.value);
      const { width: maxWidth } = rootRef.value!.getBoundingClientRect();

      text.value = width > maxWidth ? renderText : '';
    });
  });
</script>
