<template>
  <div class="key-value-pair-main">
    <div class="key-select-wraper">
      <BkSelect
        v-model="pairInfo.key"
        auto-focus
        class="key-select"
        :class="{ 'is-key-verify-failed': !isVerifyKeyPassed }"
        :clearable="false"
        filterable
        :placeholder="t('请选择标签键')"
        @change="handleKeyChange">
        <BkOption
          v-for="item in keyList"
          :id="item.value"
          :key="item.value"
          :name="item.label">
          <span class="mr-6">{{ item.label }}</span>
          <BkTag
            v-if="item.isNew"
            size="small"
            theme="success">
            NEW
          </BkTag>
        </BkOption>
        <template #extension>
          <div class="tag-key-extension-main">
            <div
              v-if="showCreateTag"
              class="create-tag-main">
              <BkInput
                v-model="inputTagKey"
                class="input-box"
                :placeholder="t('请输入标签')"
                size="small"
                @enter="handleConfirmCreateTag" />
              <BkButton
                :disabled="!inputTagKey"
                text
                @click="handleConfirmCreateTag">
                <DbIcon
                  class="confirm-icon"
                  :style="{ color: inputTagKey ? '#2dcb56' : '#979ba5' }"
                  type="check-line" />
              </BkButton>
              <BkButton
                text
                @click="() => (showCreateTag = false)">
                <DbIcon
                  class="cancel-icon"
                  type="close" />
              </BkButton>
            </div>
            <template v-else>
              <BkButton
                text
                @click="() => (showCreateTag = true)">
                <DbIcon
                  class="operate-icon"
                  type="plus-circle" />
                <span class="ml-5">
                  {{ t('新建标签') }}
                </span>
              </BkButton>
              <div class="split-line"></div>
              <BkButton
                text
                @click="handleGoTagManagePage">
                <DbIcon
                  class="operate-icon"
                  type="link" />
                <span class="ml-5">{{ t('跳转管理页') }}</span>
              </BkButton>
            </template>
          </div>
        </template>
      </BkSelect>
      <DbIcon
        v-if="!isVerifyKeyPassed"
        v-bk-tooltips="t('必填')"
        class="error-icon"
        type="exclamation-fill" />
    </div>
    <div
      class="value-input-wraper"
      :class="{ 'is-key-verify-failed': !isVerifyValuePassed }">
      <BkInput
        v-if="isKeyNewCreated"
        v-model="pairInfo.value"
        class="value-input"
        :placeholder="t('请输入标签值')"
        @change="handleValueChange" />
      <BkSelect
        v-else
        v-model="pairInfo.value"
        auto-focus
        class="value-input"
        :clearable="false"
        filterable
        :placeholder="t('请选择标签值')"
        @change="handleValueChange">
        <BkOption
          v-for="item in valueList"
          :id="item.value"
          :key="item.value"
          :name="item.label">
          <span class="mr-6">{{ item.label }}</span>
          <BkTag
            v-if="item.isNew"
            size="small"
            theme="success">
            NEW
          </BkTag>
        </BkOption>
        <template #extension>
          <div class="tag-key-extension-main">
            <div
              v-if="showCreateValue"
              class="create-tag-main">
              <BkInput
                v-model="inputTagValue"
                class="input-box"
                :placeholder="t('请输入标签值')"
                size="small"
                @enter="handleConfirmCreateValue" />
              <BkButton
                :disabled="!inputTagValue"
                text
                @click="handleConfirmCreateValue">
                <DbIcon
                  class="confirm-icon"
                  :style="{ color: inputTagValue ? '#2dcb56' : '#979ba5' }"
                  type="check-line" />
              </BkButton>
              <BkButton
                text
                @click="() => (showCreateValue = false)">
                <DbIcon
                  class="cancel-icon"
                  type="close" />
              </BkButton>
            </div>
            <template v-else>
              <BkButton
                text
                @click="() => (showCreateValue = true)">
                <DbIcon
                  class="operate-icon"
                  type="plus-circle" />
                <span class="ml-5">
                  {{ t('追加标签值') }}
                </span>
              </BkButton>
            </template>
          </div>
        </template>
      </BkSelect>
      <DbIcon
        v-if="!isVerifyValuePassed"
        v-bk-tooltips="t('必填')"
        class="error-icon"
        type="exclamation-fill" />
    </div>
    <div class="operation-icon-main">
      <DbIcon
        class="add-icon"
        type="plus-fill"
        @click="handleAdd" />
      <DbIcon
        class="delete-icon ml-10"
        type="minus-fill"
        @click="handleDelete" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { createTag } from '@services/source/tag';

  import { tagKeyRegex, tagValueRegex } from '@common/regex';

  import { messageError } from '@utils';

  interface Props {
    data: typeof pairInfo.value;
    excludeKeys: string[];
    keyValueMap: Record<
      string,
      {
        id: number;
        value: string;
      }[]
    >;
  }

  interface Emits {
    (e: 'add'): void;
    (e: 'delete'): void;
    (e: 'selectKey'): void;
  }

  interface Exposes {
    getSelectedKey: () => string;
    getValue: () => Promise<Record<
      string,
      {
        label: string;
        value: string | number;
      }
    > | null>;
  }

  type OptionType = {
    isNew?: boolean;
    label: string;
  };

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const router = useRouter();

  const pairInfo = ref({
    key: '',
    label: '',
    value: '' as string | number,
  });
  const isVerifyKeyPassed = ref(true);
  const isVerifyValuePassed = ref(true);
  const showCreateTag = ref(false);
  const showCreateValue = ref(false);
  const inputTagKey = ref('');
  const inputTagValue = ref('');
  const isKeyNewCreated = ref(false);
  const keyList = ref<Array<{ value: string } & OptionType>>([]);
  const valueList = ref<Array<{ value: number | string } & OptionType>>([]);

  let isValueNewCreated = false;

  watch(
    () => [props.keyValueMap, props.excludeKeys],
    () => {
      if (props.keyValueMap && Object.keys(props.keyValueMap).length) {
        keyList.value = Object.keys(props.keyValueMap).reduce<typeof keyList.value>((results, key) => {
          if (!props.excludeKeys.includes(key) || pairInfo.value.key === key) {
            results.push({
              label: key,
              value: key,
            });
          }
          return results;
        }, []);
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.data,
    () => {
      pairInfo.value = props.data;
    },
    { immediate: true },
  );

  watch(
    () => [pairInfo.value.key, props.keyValueMap],
    () => {
      if (pairInfo.value.key) {
        const currentKeyInfo = keyList.value.find((item) => item.value === pairInfo.value.key);
        if (currentKeyInfo) {
          isKeyNewCreated.value = !!currentKeyInfo.isNew;
        }

        if (props.keyValueMap?.[pairInfo.value.key]) {
          valueList.value =
            props.keyValueMap[pairInfo.value.key].map((item) => ({
              label: item.value,
              value: item.id,
            })) ?? [];
        }
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => pairInfo.value.value,
    () => {
      if (pairInfo.value.value) {
        const currentValueInfo = valueList.value.find((item) => item.value === pairInfo.value.value);
        if (currentValueInfo) {
          isValueNewCreated = !!currentValueInfo.isNew;
        }
      }
    },
    {
      immediate: true,
    },
  );

  const handleKeyChange = (key: string) => {
    emits('selectKey');
    isVerifyKeyPassed.value = !!key;
    pairInfo.value.value = '';
  };

  const handleValueChange = (value: string) => {
    if (isKeyNewCreated.value) {
      pairInfo.value.label = value;
    } else {
      const valueItem = valueList.value.find((item) => item.value === value)!;
      pairInfo.value.label = valueItem.label;
    }
    isVerifyValuePassed.value = !!value;
  };

  const handleAdd = () => {
    emits('add');
  };

  const handleDelete = () => {
    emits('delete');
  };

  const handleConfirmCreateTag = () => {
    const selectKeyList = keyList.value.map((item) => item.value);
    if (selectKeyList.includes(inputTagKey.value)) {
      messageError(t('标签键重复'));
      return;
    }

    if (!tagKeyRegex.test(inputTagKey.value)) {
      messageError(t('标签键为1-50个字符，支持英文字母、数字或汉字，中划线(-)，下划线(_)，点(.)'));
      return;
    }

    pairInfo.value.key = inputTagKey.value;
    keyList.value.unshift({
      isNew: true,
      label: inputTagKey.value,
      value: inputTagKey.value,
    });
    inputTagKey.value = '';
    showCreateTag.value = false;
  };

  const handleConfirmCreateValue = () => {
    if (!pairInfo.value.key) {
      messageError(t('请先选择标签键'));
      return;
    }

    if (props.keyValueMap[pairInfo.value.key].some((item) => item.value === inputTagValue.value)) {
      messageError(t('标签值重复'));
      return;
    }

    if (!tagValueRegex.test(inputTagValue.value)) {
      messageError(t('标签值为1-100个字符，支持英文字母、数字或汉字，中划线(-)，下划线(_)，点(.)'));
      return;
    }

    pairInfo.value.label = inputTagValue.value;
    pairInfo.value.value = inputTagValue.value;
    valueList.value.unshift({
      isNew: true,
      label: inputTagValue.value,
      value: inputTagValue.value,
    });
    inputTagValue.value = '';
    showCreateValue.value = false;
  };

  const handleGoTagManagePage = () => {
    const pageUrl = router.resolve({
      name: 'businessClusterTag',
    });
    window.open(pageUrl.href);
  };

  defineExpose<Exposes>({
    getSelectedKey() {
      return pairInfo.value.key;
    },
    async getValue() {
      if (!pairInfo.value.key || !pairInfo.value.value) {
        isVerifyKeyPassed.value = !!pairInfo.value.key;
        isVerifyValuePassed.value = !!pairInfo.value.value;
        return null;
      }
      if (isKeyNewCreated.value || isValueNewCreated) {
        // 需要创建标签并获取到id
        const tagInfo = await createTag({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          tags: [
            {
              key: pairInfo.value.key,
              value: pairInfo.value.value as string,
            },
          ],
          type: 'cluster',
        });
        pairInfo.value.value = tagInfo[0].id;
      }

      return {
        [pairInfo.value.key]: {
          label: pairInfo.value.label,
          value: pairInfo.value.value,
        },
      };
    },
  });
</script>
<style lang="less" scoped>
  .key-value-pair-main {
    display: flex;
    width: 100%;
    align-items: center;
    user-select: none;

    .key-select-wraper {
      position: relative;

      .key-select {
        width: 238px;

        &.is-key-verify-failed {
          :deep(.bk-input) {
            border-color: #ea3636;
          }

          :deep(.angle-down) {
            display: none !important;
          }
        }
      }
    }

    .value-input-wraper {
      position: relative;
      flex: 1;
      margin-right: 8px;
      margin-left: 14px;

      &.is-key-verify-failed {
        :deep(.bk-input) {
          border-color: #ea3636;
        }

        :deep(.bk-tag-input-trigger) {
          border-color: #ea3636;
        }

        :deep(.angle-down) {
          display: none !important;
        }
      }

      .value-input {
        width: 100%;
      }
    }

    .error-icon {
      position: absolute;
      top: 10px;
      right: 10px;
      display: flex;
      font-size: 14px;
      color: #ea3636;
    }

    .operation-icon-main {
      font-size: 14px;
      color: #979ba5;
      cursor: pointer;

      .add-icon,
      .delete-icon {
        &:hover {
          color: #63656e;
        }
      }
    }
  }
</style>
<style lang="less">
  .tag-key-extension-main {
    display: flex;
    width: 100%;
    height: 100%;
    align-items: center;
    justify-content: space-around;
    background-color: #fafbfd;

    .operate-icon {
      font-size: 14px;
    }

    .split-line {
      width: 1px;
      height: 16px;
      background: #dcdee5;
    }

    .create-tag-main {
      display: flex;
      width: 100%;
      height: 100%;
      align-items: center;
      justify-content: space-around;
      padding: 0 8px;
      gap: 8px;

      .input-box {
        flex: 1;
      }

      .confirm-icon {
        font-size: 16px;
        cursor: pointer;
      }

      .cancel-icon {
        font-size: 20px;
        color: #979ba5;
        cursor: pointer;
      }
    }
  }
</style>
