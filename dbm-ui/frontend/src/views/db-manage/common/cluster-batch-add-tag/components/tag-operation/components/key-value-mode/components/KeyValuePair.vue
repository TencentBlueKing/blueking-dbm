<template>
  <div class="key-value-pair-main">
    <div class="key-select-wraper">
      <CreateValidateSelect
        ref="keySelectRef"
        v-model="pairInfo.key"
        class="key-select"
        :disabled="disabled"
        :options="keyList"
        :placeholder="t('请选择或输入name', { name: t('标签键') })"
        :required="hasAnyValue"
        :rules="keyRules"
        @change="handleKeyChange">
        <template #extension>
          <div class="tag-key-extension-main">
            <BkButton
              text
              @click="handleGoTagManagePage">
              <DbIcon
                class="operate-icon"
                type="link" />
              <span class="ml-5">{{ t('跳转管理页') }}</span>
            </BkButton>
          </div>
        </template>
      </CreateValidateSelect>
    </div>
    <div class="value-input-wraper">
      <CreateValidateSelect
        ref="valueSelectRef"
        v-model="pairInfo.value"
        class="value-input"
        :disabled="disabled"
        :options="valueList"
        :placeholder="t('请选择或输入name', { name: t('标签值') })"
        :required="hasAnyValue"
        :rules="valueRules"
        @change="handleValueChange">
      </CreateValidateSelect>
    </div>
    <div
      v-if="!disabled"
      class="operation-icon-main">
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
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { getBusinessHref } from '@utils';

  import type { TagsPairType } from '../../../Index.vue';

  import CreateValidateSelect from './CreateValidateSelect.vue';

  interface Props {
    /** 标签候选查询的业务 ID，管理页跳转链接跟随该业务 */
    bizId: number;
    data: typeof pairInfo.value;
    disabled?: boolean;
    excludeKeys: string[];
    keyValueMap: Record<string, string[]>;
  }

  interface Emits {
    (e: 'add'): void;
    (e: 'delete'): void;
    (e: 'selectKey'): void;
    (e: 'change'): void;
  }

  interface Exposes {
    getSelectedKey: () => string;
    getValue: (isIgnoreVerify?: boolean) => Promise<({ isNew?: boolean } & TagsPairType) | null>;
  }

  interface OptionType {
    isNew?: boolean;
    label: string;
  }

  type KeyOptionType = { value: string } & OptionType;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const router = useRouter();

  const keySelectRef = ref<ComponentExposed<typeof CreateValidateSelect>>();
  const valueSelectRef = ref<ComponentExposed<typeof CreateValidateSelect>>();
  const pairInfo = ref({
    key: '',
    value: '',
  });
  const keyList = ref<KeyOptionType[]>([]);
  const valueList = ref<Array<{ value: string } & OptionType>>([]);

  // 整行任一有值才要求成对填写；全空行是选填标签的空行，应放行
  const hasAnyValue = computed(() => Boolean(pairInfo.value.key || pairInfo.value.value));
  // 只在「自己是空的那一侧」报错：key 空但 value 有值 → key 报错，反之亦然；
  // 有值的一侧不报错，避免 key 有值时 key 上反而显示错误
  const keyPairRule = {
    message: t('集群标签的键和值需同时填写'),
    trigger: 'blur',
    // 读父级 pairInfo（已随 v-model 同步），避免子组件 formData 的 watch 时序
    validator: () => Boolean(pairInfo.value.key) || !pairInfo.value.value,
  };
  const valuePairRule = {
    message: t('集群标签的键和值需同时填写'),
    trigger: 'blur',
    validator: () => Boolean(pairInfo.value.value) || !pairInfo.value.key,
  };

  const keyRules = [
    {
      message: t('格式不正确，请勿使用空格或特殊符号'),
      trigger: 'blur',
      // 支持中文、字母、数字、连字符、下划线、点号；空行放行，必填交给 keyPairRule
      validator: (value: string) => !value || /^[\u4e00-\u9fa5a-zA-Z0-9\-_.]+$/.test(value),
    },
    {
      message: t('name不能重复', { name: t('标签键') }),
      trigger: 'blur',
      validator: (value: string) =>
        !value ||
        (props.excludeKeys.filter((item) => item === value).length <= 1 &&
          (isKeyNewCreated || props.data.key === value)),
    },
    keyPairRule,
  ];

  const valueRules = [
    {
      message: t('格式不正确，请勿使用空格或特殊符号'),
      trigger: 'blur',
      // 支持中文、字母、数字、连字符、下划线、点号；空行放行，必填交给 valuePairRule
      validator: (value: string) => !value || /^[\u4e00-\u9fa5a-zA-Z0-9\-_.]+$/.test(value),
    },
    valuePairRule,
  ];

  let isKeyNewCreated = false;
  let isValueNewCreated = false;

  watch(
    () => props.keyValueMap,
    () => {
      if (props.keyValueMap && Object.keys(props.keyValueMap).length) {
        keyList.value = Object.keys(props.keyValueMap).reduce<typeof keyList.value>((results, key) => {
          results.push({
            label: key,
            value: key,
          });
          return results;
        }, []);
      }
    },
    {
      deep: true,
      immediate: true,
    },
  );

  watch(
    () => props.excludeKeys,
    () => {
      nextTick(() => {
        const totalList = (keySelectRef.value?.getTotalList() as KeyOptionType[]) ?? [];
        const filteredList =
          totalList.filter((item) => !props.excludeKeys.includes(item.value) || pairInfo.value.key === item.value) ??
          [];
        keySelectRef.value?.tmpUpdateList(filteredList);
      });
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
        if (props.keyValueMap?.[pairInfo.value.key]) {
          valueList.value =
            props.keyValueMap[pairInfo.value.key].map((item) => ({
              label: item,
              value: item,
            })) ?? [];
        } else {
          valueList.value = [];
        }
      }
    },
    {
      immediate: true,
    },
  );

  // 配对规则读 pairInfo，key/value 任一变化都要让两侧重新校验才能刷新错误态
  const revalidatePair = () => {
    nextTick(() => {
      keySelectRef.value?.validate();
      valueSelectRef.value?.validate();
    });
  };

  const handleKeyChange = (_: string, isNew: boolean) => {
    isKeyNewCreated = isNew;
    pairInfo.value.value = '';
    emits('selectKey');
    emits('change');
    // 换 key 会清空 value，先清掉旧的配对错误，不要一选 key 就提示半填
    nextTick(() => {
      keySelectRef.value?.clearValidate();
      valueSelectRef.value?.clearValidate();
    });
  };

  const handleValueChange = (value: string, isNew: boolean) => {
    isValueNewCreated = isNew;
    if (isNew) {
      pairInfo.value.value = value;
    } else {
      const valueItem = valueList.value.find((item) => item.value === value)!;
      pairInfo.value.value = valueItem.value;
    }
    emits('change');
    revalidatePair();
  };

  const handleAdd = () => {
    emits('add');
  };

  const handleDelete = () => {
    emits('delete');
  };

  const handleGoTagManagePage = () => {
    const pageRoute = router.resolve({
      name: 'businessClusterTag',
    });
    const pageUrl = getBusinessHref(pageRoute.href, props.bizId);
    window.open(pageUrl);
  };

  defineExpose<Exposes>({
    getSelectedKey() {
      return pairInfo.value.key;
    },
    async getValue(isIgnoreVerify = false) {
      if (isIgnoreVerify) {
        return {
          key: pairInfo.value.key,
          value: pairInfo.value.value,
        };
      }
      const validateResult = await Promise.all([keySelectRef.value?.validate(), valueSelectRef.value?.validate()]);
      if (!validateResult.every((item) => item)) {
        return null;
      }

      return {
        isNew: isKeyNewCreated || isValueNewCreated,
        key: pairInfo.value.key,
        value: pairInfo.value.value as string,
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

    .key-select {
      width: 238px;
    }

    .value-input-wraper {
      position: relative;
      flex: 1;
      margin-right: 8px;
      margin-left: 14px;

      .value-input {
        width: 100%;
      }
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
