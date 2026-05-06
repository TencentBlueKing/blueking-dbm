<template>
  <BkSelect
    v-model="modelValue"
    allow-create
    class="spec-manage-biz-selector"
    collapse-tags
    enable-virtual-render
    filterable
    :list="bizList"
    multiple
    v-bind="attrs"
    multiple-mode="tag"
    :placeholder="t('请选择指定业务，或直接输入业务名（多业务以换行、空格、; 、| 分隔，回车完成输入）')"
    @change="handleChange" />
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { useGlobalBizs } from '@stores';

  import { batchInputSplitRegex } from '@common/regex';

  type Emits = (e: 'change') => void;

  const emits = defineEmits<Emits>();
  const modelValue = defineModel<number[]>();

  const attrs = useAttrs();
  const { t } = useI18n();
  const { bizNameMap, bizs } = useGlobalBizs();

  const bizList = bizs.map((item) => ({
    label: item.name,
    value: item.bk_biz_id,
  }));

  const handleChange = (list: (number | string)[]) => {
    const bizNames: string[] = [];
    const bizIds: number[] = [];
    if (list.length) {
      list.forEach((item) => {
        if (typeof item === 'string') {
          bizNames.push(item);
        } else {
          bizIds.push(item);
        }
      });
      if (bizNames.length) {
        const hadnledList = bizNames.map((item) => item.split(batchInputSplitRegex));
        const handledBizs = _.flatMap(hadnledList).reduce<number[]>((results, item) => {
          if (bizNameMap[item] !== undefined) {
            results.push(bizNameMap[item]);
          }
          return results;
        }, []);
        const appendBizs = _.difference(handledBizs, bizIds);
        bizIds.push(...appendBizs);
      }
    }

    modelValue.value = bizIds;
    emits('change');
  };
</script>

<style lang="less">
  .spec-manage-biz-selector {
    .bk-select-tag-wrapper {
      flex: 1;
    }
  }
</style>
