<template>
  <div class="db-edit-value-main">
    <div
      v-if="!isEdit"
      class="display-mian">
      <div class="value-display">
        {{ displayText }}
      </div>
      <AuthTemplate
        v-if="!readonly"
        action-id="risk_memo_manage"
        :biz-id="bizId"
        :permission="managePermission">
        <DbIcon
          class="edit-main"
          type="edit"
          @click="handleClickEdit" />
      </AuthTemplate>
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
    bizId?: number;
    managePermission?: boolean;
    readonly?: boolean;
    value?: string;
  }

  type Emits = (e: 'change', value: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    bizId: 0,
    managePermission: true,
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
    display: flex;
    width: 100%;
    font-size: 12px;
    align-items: center;

    .display-mian {
      display: flex;
      width: 100%;
      margin-top: 0;
      align-items: center;

      .value-display {
        flex: 0 1 auto;
        max-width: calc(100% - 20px);
        overflow-wrap: break-word;
        word-break: break-all;
      }

      .tags-display {
        min-width: 100px;
      }

      .edit-main {
        margin-left: 4px;
        font-size: 12px;
        color: #979ba5;
        cursor: pointer;

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
