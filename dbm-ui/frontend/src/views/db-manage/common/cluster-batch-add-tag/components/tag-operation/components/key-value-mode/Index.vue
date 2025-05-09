<template>
  <div class="key-value-mode-main">
    <KeyValuePair
      v-for="(item, index) in pairList"
      :key="item.id"
      ref="keyValuePairsRef"
      :data="item"
      :exclude-keys="excludeKeyList"
      :key-value-map="keyValueMap"
      @add="() => handleAdd(index)"
      @delete="() => handleDelete(index)"
      @select-key="handleSelectKey" />
  </div>
</template>
<script setup lang="ts">
  import { random } from '@utils';

  import type { KeyValueMapType, TagsPairType } from '../../Index.vue';

  import KeyValuePair from './components/KeyValuePair.vue';

  interface Props {
    data?: TagsPairType;
    keyValueMap: KeyValueMapType;
  }

  interface Exposes {
    getValue: (isIgnoreVerify?: boolean) => Promise<TagsPairType | null>;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
  });

  const generateRowData = () => ({
    id: random(),
    key: '',
    label: '',
    value: '' as string | number,
  });

  const pairList = ref([generateRowData()]);
  const keyValuePairsRef = ref<InstanceType<typeof KeyValuePair>[]>();

  const excludeKeyList = ref<string[]>([]);

  watch(
    () => props.data,
    () => {
      if (props.data && Object.keys(props.data).length > 0) {
        pairList.value = Object.entries(props.data).reduce<typeof pairList.value>((results, item) => {
          results.push({
            id: random(),
            key: item[0],
            label: item[1].label,
            value: item[1].value as number,
          });
          return results;
        }, []);
        nextTick(() => {
          handleSelectKey();
        });
      }
    },
    { immediate: true },
  );

  watch(
    () => props.keyValueMap,
    () => {
      handleSelectKey();
    },
    { deep: true },
  );

  const handleSelectKey = () => {
    excludeKeyList.value = keyValuePairsRef.value!.reduce<string[]>((results, item) => {
      const key = item.getSelectedKey();
      if (key) {
        results.push(key);
      }
      return results;
    }, []);
  };

  const handleAdd = (index: number) => {
    pairList.value.splice(index + 1, 0, generateRowData());
    nextTick(() => {
      handleSelectKey();
    });
  };

  const handleDelete = (index: number) => {
    pairList.value.splice(index, 1);
    nextTick(() => {
      handleSelectKey();
    });
  };

  defineExpose<Exposes>({
    async getValue(isIgnoreVerify = false) {
      let pairList = await Promise.all(keyValuePairsRef.value!.map((item) => item.getValue()));
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
    width: 100%;
    flex-direction: column;
    gap: 16px;
  }
</style>
