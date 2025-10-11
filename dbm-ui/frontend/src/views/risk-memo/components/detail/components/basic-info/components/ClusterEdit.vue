<template>
  <div
    class="clusters-edit-value-main"
    :class="{ 'is-error': isError }">
    <div
      v-if="!isEdit"
      class="display-mian">
      <BkTag v-if="isEffectAll">{{ t('全部') }}</BkTag>
      <div
        v-else
        class="value-display">
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
      class="clusters-select"
      :clearable="false"
      collapse-tags
      :list="clusterList"
      multiple
      multiple-mode="tag"
      show-on-init
      @change="handleSelectChange"
      @toggle="handleSelectToggle" />
    <DbIcon
      v-if="isError"
      v-bk-tooltips="t('不能为空')"
      class="error-icon"
      type="exclamation-fill" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { filterClusters } from '@services/source/dbbase';

  import { DBTypes } from '@common/const';

  interface Props {
    bizId?: number;
    dbType?: DBTypes;
    managePermission?: boolean;
    readonly?: boolean;
    value?: string[];
  }

  type Emits = (e: 'change', value: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    bizId: undefined,
    dbType: undefined,
    managePermission: true,
    readonly: false,
    value: () => [],
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const editValueRef = ref<any>(null);
  const isEdit = ref(false);
  const localValue = ref<string[]>([]);
  const isError = ref(false);
  const clusterList = ref<
    {
      label: string;
      value: string;
    }[]
  >([]);

  const displayText = computed(() => {
    const selectListMap = clusterList.value.reduce<Record<string, string>>(
      (dataMap, item) =>
        Object.assign(dataMap, {
          [item.value]: item.label,
        }),
      {},
    );
    return localValue.value.map((item) => selectListMap[item]).join(' , ');
  });

  const isEffectAll = computed(() => props.value.length === 1 && props.value[0] === 'all');

  const { run: runFilterClusters } = useRequest(filterClusters, {
    manual: true,
    onSuccess: (data) => {
      clusterList.value = data.map((item) => ({
        label: item.master_domain,
        value: item.master_domain,
      }));
    },
  });

  watch(
    () => props.value,
    () => {
      localValue.value = props.value;
    },
    {
      immediate: true,
    },
  );

  watch(
    () => [props.bizId, props.dbType],
    () => {
      if (props.bizId && props.dbType) {
        runFilterClusters({
          bk_biz_id: props.bizId,
          db_type: props.dbType,
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleClickEdit = () => {
    isEdit.value = true;
  };

  const handleSelectChange = () => {
    const allIndex = localValue.value.indexOf('all');
    if (allIndex !== -1 && localValue.value.length > 1) {
      localValue.value.splice(allIndex, 1);
    }
    isError.value = false;
  };

  const handleSelectToggle = (isShow: boolean) => {
    if (!isShow) {
      if (!localValue.value.length) {
        isError.value = true;
        return;
      }

      if (localValue.value.join(',') !== props.value.join(',')) {
        emits('change', localValue.value.join(','));
      }
      isEdit.value = false;
    }
  };
</script>
<style lang="less">
  .clusters-edit-value-main {
    width: 100%;
    display: flex;
    align-items: center;
    font-size: 12px;
    position: relative;

    &.is-error {
      .bk-select-tag {
        border-color: #ea3636 !important;
      }

      .angle-down {
        display: none !important;
      }
    }

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

    .clusters-select {
      width: 100%;
    }

    .error-icon {
      position: absolute;
      top: 50%;
      transform: translateY(-50%);
      right: 8px;
      color: #ea3636;
      font-size: 14px;
      cursor: pointer;
      z-index: 9;
    }
  }
</style>
