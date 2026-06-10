<template>
  <BkSelect
    v-model="localValue"
    :clearable="false"
    :disabled="!!versionSeriesId"
    filterable
    :placeholder="t('请选择xx', [t('系列')])"
    @change="handleValueChange">
    <BkOption
      v-for="system in seriesList"
      :key="system.value"
      :label="system.label"
      :value="system.value">
      <span class="mr-3">{{ system.label }}</span>
      <BkTag
        v-if="system.isNew"
        size="small"
        style="background: #f8b64f"
        theme="warning"
        type="filled">
        New
      </BkTag>
    </BkOption>
    <template #extension>
      <EditSeries
        :distribution-id="distributionId"
        :existed-list="existedNames"
        @confirm="handleConfirm">
        <div class="default-display-main">
          <DbIcon
            class="add-series-icon"
            type="plus-circle" />
          <span>{{ t('新增系列') }}</span>
        </div>
      </EditSeries>
    </template>
  </BkSelect>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getVersionSeriesList } from '@services/source/version';

  import EditSeries from '../../EditSeries.vue';

  interface Props {
    distributionId?: number;
    versionSeriesId?: number;
  }

  interface Exposes {
    getCurrentLabel: () => string;
  }

  interface Emits {
    (e: 'addVersion'): void;
    (e: 'valueChange'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    distributionId: undefined,
    versionSeriesId: undefined,
  });

  const emits = defineEmits<Emits>();

  const localValue = defineModel<number | undefined>({
    default: undefined,
  });

  const { t } = useI18n();

  const editInputRef = ref();
  const isEdit = ref(false);
  const seriesList = ref<{ isNew?: boolean; label: string; value: number }[]>([]);

  const existedNames = computed(() => seriesList.value.map((item) => item.label.toLocaleLowerCase()));
  const currentVersionLabel = computed(
    () => seriesList.value.find((item) => item.value === localValue.value)?.label || '',
  );

  const { run: runGetVersionSeriesList } = useRequest(getVersionSeriesList, {
    manual: true,
    onSuccess(data) {
      seriesList.value = data.map((item) => ({
        label: item.name,
        value: item.id,
      }));
    },
  });

  watch(isEdit, () => {
    if (isEdit.value) {
      nextTick(() => {
        editInputRef.value.focus();
      });
    }
  });

  watch(
    () => props.versionSeriesId,
    () => {
      if (props.versionSeriesId !== undefined) {
        localValue.value = props.versionSeriesId;
        runGetVersionSeriesList({
          distribution: props.distributionId!,
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleValueChange = () => {
    emits('valueChange');
  };

  const handleConfirm = (id: number, name: string) => {
    seriesList.value.push({
      isNew: true,
      label: name,
      value: id,
    });
    nextTick(() => {
      localValue.value = id;
    });
    emits('addVersion');
  };

  defineExpose<Exposes>({
    getCurrentLabel() {
      return currentVersionLabel.value;
    },
  });
</script>
<style lang="less">
  .default-display-main {
    font-family: MicrosoftYaHei, Arial, sans-serif;
    color: #4d4f56;
    cursor: pointer;

    .add-series-icon {
      margin-right: 5px;
      font-size: 14px;
      color: #979ba5;
    }
  }
</style>
