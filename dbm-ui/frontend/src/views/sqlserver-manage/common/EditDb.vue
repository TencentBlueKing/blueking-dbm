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

  import RenderDbName from '@views/sqlserver-manage/common/DbName.vue';

  interface Props {
    dbName: string[];
    dbIgnoreName: string[];
  }

  interface Emits {
    (
      e: 'change',
      value: {
        dbName: Props['dbName'];
        dbIgnoreName: Props['dbIgnoreName'];
      },
    ): void;
  }

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
        dbName: localDBName.value,
        dbIgnoreName: localDbIgnoreName.value,
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
