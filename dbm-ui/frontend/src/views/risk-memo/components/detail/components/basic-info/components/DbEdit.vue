<template>
  <div class="db-edit-value-main">
    <div
      v-if="!isEdit"
      class="display-mian">
      <div class="value-display">
        {{ displayText }}
      </div>
      <DbIcon
        v-if="!readonly"
        class="edit-main"
        type="edit"
        @click="handleClickEdit" />
    </div>
    <BkSelect
      v-else
      ref="editValueRef"
      v-model="localValue"
      class="db-select"
      :clearable="false"
      :list="dbList"
      show-on-init
      @toggle="handleSelectToggle" />
  </div>
</template>
<script setup lang="ts">
  import { DBTypeInfos } from '@common/const';

  interface Props {
    readonly?: boolean;
    value?: string;
  }

  type Emits = (e: 'change', value: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    readonly: false,
    value: '',
  });

  const emits = defineEmits<Emits>();

  const editValueRef = ref<any>(null);
  const isEdit = ref(false);
  const localValue = ref('');

  const dbList = Object.values(DBTypeInfos).map((item) => ({
    label: item.name,
    value: item.id,
  }));

  const dbListMap = dbList.reduce<Record<string, string>>(
    (dataMap, item) =>
      Object.assign(dataMap, {
        [item.value]: item.label,
      }),
    {},
  );

  const displayText = computed(() => dbListMap[localValue.value]);

  watch(
    () => props.value,
    () => {
      localValue.value = props.value;
    },
    {
      immediate: true,
    },
  );

  const handleClickEdit = () => {
    isEdit.value = true;
  };

  const handleSelectToggle = (isShow: boolean) => {
    if (!isShow) {
      if (localValue.value !== props.value) {
        emits('change', localValue.value);
      }
      isEdit.value = false;
    }
  };
</script>
<style lang="less">
  .db-edit-value-main {
    width: 100%;
    display: flex;
    align-items: center;
    font-size: 12px;

    .display-mian {
      width: 100%;
      display: flex;
      align-items: center;

      &:hover {
        .edit-main {
          display: block;
        }
      }

      .value-display {
        flex: 1;
        flex-grow: 0;
        flex-shrink: 1;
        flex-basis: auto;
        max-width: calc(100% - 20px);
        overflow-wrap: break-word;
      }

      .tags-display {
        min-width: 100px;
      }

      .edit-main {
        width: 12px;
        height: 12px;
        color: #979ba5;
        font-size: 12px;
        cursor: pointer;
        margin-left: 4px;
        display: none;

        &:hover {
          color: #3a84ff;
        }
      }
    }

    .db-select {
      width: 100%;
    }
  }
</style>
