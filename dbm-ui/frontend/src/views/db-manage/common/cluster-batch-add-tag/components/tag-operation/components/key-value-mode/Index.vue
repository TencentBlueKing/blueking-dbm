<template>
  <div class="key-value-mode-main">
    <BkButton
      v-if="!pairList.length"
      class="add-default"
      size="small"
      text
      theme="primary"
      @click="handleAddDefaultRow">
      <DbIcon type="add" />
      <span class="ml-4">{{ t('添加') }}</span>
    </BkButton>
    <template v-else>
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
    </template>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { random } from '@utils';

  import type { KeyValueMapType, TagsPairType } from '../../Index.vue';

  import KeyValuePair from './components/KeyValuePair.vue';

  interface Props {
    allowEmpty?: boolean;
    data?: TagsPairType;
    keyValueMap: KeyValueMapType;
  }

  interface Exposes {
    getValue: (isIgnoreVerify?: boolean) => Promise<TagsPairType | null>;
  }

  const props = withDefaults(defineProps<Props>(), {
    allowEmpty: true,
    data: undefined,
  });

  const generateRowData = () => ({
    id: random(),
    key: '',
    label: '',
    value: '' as string | number,
  });

  const { t } = useI18n();

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

  const handleAddDefaultRow = () => {
    pairList.value.push(generateRowData());
  };

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
    if (pairList.value.length === 1 && !props.allowEmpty) {
      return;
    }

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

    .add-default {
      width: 64px;
      margin-top: 8px;
      margin-left: -12px;
      font-size: 12px;
    }
  }
</style>
