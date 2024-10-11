<template>
  <BkSelect
    v-model="selected"
    @toggle="handleToggle">
    <template #trigger>
      <div
        ref="businessSelectorRef"
        class="business-selector">
        <div>{{ bizIdMap.get(selected as number)?.name }}</div>
        <div
          ref="triangleRef"
          class="triangle"></div>
      </div>
    </template>
    <BkOption
      v-for="item in sortedBizList"
      :key="item.bk_biz_id"
      :label="`${item.name}(#${item.bk_biz_id}, ${item.english_name})`"
      :value="item.bk_biz_id">
      {{ `${item.name}(#${item.bk_biz_id}, ${item.english_name})` }}
      <div style="margin-left: auto">
        <DbIcon
          v-if="favorBizIdSet.has(item.bk_biz_id)"
          class="unfavor-btn"
          style="color: #ffb848"
          type="star-fill"
          @click.stop="() => handleUnfavor(item.bk_biz_id)" />
        <DbIcon
          v-else
          class="favor-btn"
          type="star"
          @click.stop="() => handleFavor(item.bk_biz_id)" />
      </div>
    </BkOption>
  </BkSelect>
</template>

<script setup lang="tsx">
  import { cloneDeep } from 'lodash';
  import { defineEmits, ref } from 'vue';

  import { useGlobalBizs } from '@stores';

  interface Emits {
    (e: 'change', value: number): void;
  }

  const emit = defineEmits<Emits>();

  const { bizs: bizList, currentBizInfo, bizIdMap } = useGlobalBizs();
  const triangleRef = useTemplateRef('triangleRef');
  const favorBizIdSet = ref<Set<number>>(new Set());
  const selected = ref(currentBizInfo?.bk_biz_id);

  const sortedBizList = computed(() => {
    const clonedBizList = cloneDeep(bizList);

    return clonedBizList.sort((item1, item2) => {
      const isItem1Favored = favorBizIdSet.value.has(item1.bk_biz_id) ? 1 : 0;
      const isItem2Favored = favorBizIdSet.value.has(item2.bk_biz_id) ? 1 : 0;

      return isItem2Favored - isItem1Favored;
    });
  });

  watch(selected, (newValue) => {
    emit('change', newValue as number);
  });

  const handleFavor = (bkBizId: number) => {
    favorBizIdSet.value.add(bkBizId);
  };

  const handleUnfavor = (bkBizId: number) => {
    favorBizIdSet.value.delete(bkBizId);
  };

  const handleToggle = () => {
    triangleRef.value?.classList.toggle('up');
  };
</script>

<style lang="less" scoped>
  .business-selector {
    cursor: pointer;
    color: #3a84ff;
    display: flex;
    align-items: center;
    font-size: 14px;
    width: 360px;

    .triangle {
      width: 0;
      height: 0;
      border-left: 4.875px solid transparent;
      border-right: 4.875px solid transparent;
      border-top: 6px solid #3a84ff;
      transition: transform 0.3s ease;
      margin-left: 7px;

      &.up {
        transform: rotate(180deg);
      }
    }
  }
</style>
