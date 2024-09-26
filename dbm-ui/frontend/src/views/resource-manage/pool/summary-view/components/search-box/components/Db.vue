<template>
  <BkSelect
    v-model="localValue"
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

  import { DBTypes } from '@common/const';

  interface Emits {
    (e: 'change', value: string): void;
  }

  interface Exposes {
    getValue: () => {
      db_type: string;
    };
  }

  const emits = defineEmits<Emits>();

  const localValue = ref(DBTypes.REDIS);

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

  const handleChange = (value: string) => {
    emits('change', value);
  };

  defineExpose<Exposes>({
    getValue: () => ({
      db_type: localValue.value,
    }),
  });
</script>
