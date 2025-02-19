<template>
  <BkTable
    :border="['outer', 'row', 'col']"
    :data="[{}]">
    <BkTableColumn :label="t('回档 DB')">
      <RenderDbName
        :model-value="localDBName"
        required
        @change="handleDbNameChange" />
    </BkTableColumn>
    <BkTableColumn :label="t('忽略 DB')">
      <RenderDbName
        :model-value="localDbIgnoreName"
        @change="handleDnIgnoreNameChange" />
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="tsx">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import RenderDbName from '@views/db-manage/sqlserver/common/DbName.vue';

  interface Props {
    dbIgnoreName: string[];
    dbName: string[];
  }

  type Emits = (
    e: 'change',
    value: {
      dbIgnoreName: Props['dbIgnoreName'];
      dbName: Props['dbName'];
    },
  ) => void;

  interface Expose {
    refresh(): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const localDBName = ref(props.dbName);
  const localDbIgnoreName = ref(props.dbIgnoreName);

  const handleChange = () => {
    if (localDbIgnoreName.value === props.dbName && localDbIgnoreName.value === props.dbIgnoreName) {
      return;
    }
    if (!localDbIgnoreName.value) {
      emits('change', {
        dbIgnoreName: localDbIgnoreName.value,
        dbName: localDBName.value,
      });
      return;
    }
  };

  const handleDbNameChange = (value: string[]) => {
    localDBName.value = value;
    handleChange();
  };

  const handleDnIgnoreNameChange = (value: string[]) => {
    localDbIgnoreName.value = value;
    handleChange();
  };

  defineExpose<Expose>({
    refresh() {
      handleChange();
    },
  });
</script>
