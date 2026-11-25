<template>
  <div class="key-value-mode-main">
    <BkButton
      v-if="!pairList.length"
      class="add-default"
      :disabled="disabled"
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
        :biz-id="bizId"
        :data="item"
        :disabled="disabled"
        :exclude-keys="excludeKeyList"
        :key-value-map="keyValueMap"
        @add="() => handleAdd(index)"
        @change="() => emits('change')"
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
    /** 标签候选查询的业务 ID，管理页跳转链接跟随该业务 */
    bizId: number;
    data?: TagsPairType[];
    disabled?: boolean;
    keyValueMap: KeyValueMapType;
  }

  interface Exposes {
    getValue: (isIgnoreVerify?: boolean) => Promise<TagsPairType[] | null>;
  }

  type Emits = (e: 'change') => void;

  const props = withDefaults(defineProps<Props>(), {
    allowEmpty: true,
    data: undefined,
    disabled: false,
  });

  const emits = defineEmits<Emits>();

  const generateRowData = () => ({
    id: random(),
    key: '',
    value: '',
  });

  const { t } = useI18n();

  const pairList = ref([generateRowData()]);
  const keyValuePairsRef = ref<InstanceType<typeof KeyValuePair>[]>();

  const excludeKeyList = ref<string[]>([]);

  watch(
    () => props.data,
    () => {
      // 业务切换等场景 data 被清空时，重置回一条空白行
      pairList.value =
        props.data && props.data.length > 0
          ? props.data.reduce<typeof pairList.value>((results, item) => {
              results.push({
                id: random(),
                key: item.key,
                value: item.value,
              });
              return results;
            }, [])
          : [generateRowData()];
      nextTick(() => {
        handleSelectKey();
      });
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

    emits('change');
    pairList.value.splice(index, 1);
    nextTick(() => {
      handleSelectKey();
    });
  };

  defineExpose<Exposes>({
    async getValue(isIgnoreVerify = false) {
      let pairList = await Promise.all(keyValuePairsRef.value!.map((item) => item.getValue(isIgnoreVerify)));
      if (isIgnoreVerify) {
        pairList = pairList.filter((item) => !!item);
      } else {
        if (pairList.some((item) => !item)) {
          return null;
        }
        // 全空行是选填留白，过滤掉；半填行已被各 pair 的 form-item 校验拦截
        pairList = pairList.filter((item) => !!(item!.key || item!.value));
      }
      pairList.forEach((item) => {
        if (item!.isNew) {
          const tempItem = item as { isNew?: boolean };
          delete tempItem.isNew;
        }
      });
      return pairList as TagsPairType[];
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
