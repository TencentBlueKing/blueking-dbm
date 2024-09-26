<template>
  <BkSelect
    v-model="localValue"
    :clearable="false"
    @change="handleChange">
    <BkOption
      v-for="biz in bizList"
      :key="biz.bk_biz_id"
      :label="biz.display_name"
      :value="`${biz.bk_biz_id}`" />
  </BkSelect>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getBizs } from '@services/source/cmdb';

  interface Emits {
    (e: 'change'): void;
  }

  interface Exposes {
    getValue: () => {
      for_biz: number;
    };
  }

  const emits = defineEmits<Emits>();

  const localValue = ref('0');

  const { t } = useI18n();

  const bizList = shallowRef<
    {
      bk_biz_id: number;
      display_name: string;
    }[]
  >([]);

  useRequest(getBizs, {
    onSuccess(data) {
      const cloneData = data.map((item) => ({
        bk_biz_id: item.bk_biz_id,
        display_name: item.display_name,
      }));
      cloneData.unshift({
        bk_biz_id: 0,
        display_name: t('公共资源池'),
      });
      bizList.value = cloneData;
    },
  });

  const handleChange = (value: string) => {
    localValue.value = value;
    emits('change');
  };

  defineExpose<Exposes>({
    getValue: () => ({
      for_biz: Number(localValue.value),
    }),
  });
</script>
