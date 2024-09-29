<template>
  <BkSelect
    v-model="modelValue"
    :clearable="false"
    @change="handleChange">
    <BkOption
      v-for="item in dbTypeList"
      :key="item.id"
      :label="item.name"
      :value="item.id" />
  </BkSelect>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchDbTypeList } from '@services/source/infras';

  interface Emits {
    (e: 'change'): void;
  }

  interface Exposes {
    getValue: () => {
      db_type: string;
    };
  }

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    default: 'PUBLIC',
  });

  const { t } = useI18n();

  const dbTypeList = shallowRef<
    {
      id: string;
      name: string;
    }[]
  >([]);

  useRequest(fetchDbTypeList, {
    onSuccess(data) {
      const cloneData = data;
      cloneData.unshift({
        id: 'PUBLIC',
        name: t('通用'),
      });
      dbTypeList.value = cloneData;
    },
  });

  const handleChange = () => {
    nextTick(() => {
      emits('change');
    });
  };

  defineExpose<Exposes>({
    getValue: () => ({
      db_type: modelValue.value,
    }),
  });
</script>
