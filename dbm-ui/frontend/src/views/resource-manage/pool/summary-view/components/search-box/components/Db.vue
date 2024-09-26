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

  interface Props {
    model: Record<string, string>;
  }

  interface Emits {
    (e: 'change'): void;
  }

  interface Exposes {
    getValue: () => {
      db_type: string;
    };
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const localValue = ref<string>(DBTypes.REDIS);
  const dbTypeList = shallowRef<
    {
      id: string;
      name: string;
    }[]
  >([]);

  useRequest(fetchDbTypeList, {
    onSuccess(data) {
      dbTypeList.value = [{ id: 'PUBLIC', name: t('通用') }, ...data];
    },
  });

  watch(
    () => props.model,
    () => {
      if (props.model.db_type) {
        localValue.value = props.model.db_type;
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = () => {
    emits('change');
  };

  defineExpose<Exposes>({
    getValue: () => ({
      db_type: localValue.value,
    }),
  });
</script>
