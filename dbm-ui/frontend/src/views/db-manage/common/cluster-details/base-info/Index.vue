<template>
  <div
    ref="root"
    class="cluster-detail-base-info">
    <slot />
  </div>
</template>
<script lang="ts">
  import InfoItem from './InfoItem.vue';

  export { InfoItem };
</script>
<script setup lang="ts">
  const rootRef = useTemplateRef('root');

  onMounted(() => {
    setTimeout(() => {
      let maxLabelWidth = 0;
      const allLabelEleList = rootRef.value!.querySelectorAll('.cluster-detail-base-info-item > .label');
      allLabelEleList.forEach((item) => {
        maxLabelWidth = Math.max(maxLabelWidth, item.getBoundingClientRect().width);
      });
      allLabelEleList.forEach((item) => {
        // eslint-disable-next-line no-param-reassign
        (item as HTMLDivElement).style.width = `${Math.ceil(maxLabelWidth)}px`;
      });
    });
  });
</script>
<style lang="less">
  .cluster-detail-base-info {
    display: flex;
    padding-top: 20px;
    flex-wrap: wrap;
  }
</style>
