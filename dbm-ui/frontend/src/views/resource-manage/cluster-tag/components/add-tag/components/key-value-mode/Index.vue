<template>
  <div class="key-value-mode-main">
    <KeyValuePair
      v-for="(item, index) in pairList"
      :key="item.id"
      ref="keyValuePairsRef"
      :data="item"
      :existed-keys="existedKeys"
      @add="() => handleAdd(index)"
      @delete="() => handleDelete(index)" />
  </div>
</template>
<script setup lang="ts">
  import { random } from '@utils';

  import type { TagsPairType } from '../../Index.vue';

  import KeyValuePair from './components/key-value-pair/Index.vue';

  interface Props {
    data?: TagsPairType;
    existedKeys: Set<string>;
  }

  interface Exposes {
    getValue: (isIgnoreVerify?: boolean) => TagsPairType | null;
  }

  const props = defineProps<Props>();

  const generateRowData = () => ({
    id: random(),
    key: '',
    value: [] as string[],
  });

  const pairList = ref([generateRowData()]);
  const keyValuePairsRef = ref<InstanceType<typeof KeyValuePair>[]>();

  watch(
    () => props.data,
    () => {
      if (props.data && Object.keys(props.data).length > 0) {
        pairList.value = Object.entries(props.data).reduce<typeof pairList.value>((results, item) => {
          results.push({
            id: random(),
            key: item[0],
            value: item[1],
          });
          return results;
        }, []);
      }
    },
    { immediate: true },
  );

  const handleAdd = (index: number) => {
    pairList.value.splice(index + 1, 0, generateRowData());
  };

  const handleDelete = (index: number) => {
    if (pairList.value.length === 1) {
      return;
    }

    pairList.value.splice(index, 1);
  };

  defineExpose<Exposes>({
    getValue(isIgnoreVerify = false) {
      let pairList = keyValuePairsRef.value!.map((item) => item.getValue());
      if (isIgnoreVerify) {
        pairList = pairList.filter((item) => !!item);
      } else {
        if (pairList.some((item) => !item)) {
          return null;
        }
      }

      return Object.values(pairList).reduce<TagsPairType>((results, item) => Object.assign(results, item), {});
    },
  });
</script>
<style lang="less" scoped>
  .key-value-mode-main {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
</style>
