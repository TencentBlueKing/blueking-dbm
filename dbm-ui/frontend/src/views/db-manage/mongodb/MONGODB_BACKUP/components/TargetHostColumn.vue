<template>
  <EditableColumn
    ref="editableTableColumn"
    :append-rules="rules"
    field="target_host"
    :label="t('目标主机')"
    :min-width="300"
    required>
    <EditableInput
      v-model="modelValue"
      :disabled="disabled"
      :placeholder="t('请输入或选择主机')">
      <template #append>
        <span
          v-bk-tooltips="{
            content: t('选择主机'),
            disabled: disabled,
          }"
          class="host-selector-button"
          :class="{ 'host-selector-button-disabled': disabled }"
          :disabled="disabled"
          @click="handleShowSelector">
          <DbIcon type="host-select" />
        </span>
      </template>
    </EditableInput>
    <InstanceSelector
      v-model:is-show="isShowSelector"
      :cluster-types="['mongoCluster']"
      :selected="selected"
      :tab-list-config="tabListConfig"
      @change="handleInstanceSelectChange" />
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { checkInstance } from '@services/source/dbbase';

  import { ClusterTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  interface Props {
    clusterId?: number;
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();
  const editableTableColumnRef = useTemplateRef('editableTableColumn');

  const rules = [
    {
      message: t('目标主机输入格式有误'),
      trigger: 'change',
      validator: (value: string) => ipv4.test(value),
    },
    {
      message: t('目标主机不存在'),
      trigger: 'change',
      validator: (value: string) => {
        if (props.clusterId) {
          return checkInstance({
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            cluster_ids: [props.clusterId],
            instance_addresses: [value],
          }).then((instance) => instance.length > 0);
        }
        return true;
      },
    },
  ];

  const tabListConfig = computed(
    () =>
      ({
        mongoCluster: [
          {
            tableConfig: {
              multiple: false,
            },
            topoConfig: {
              filterClusterId: props.clusterId,
            },
          },
        ],
      }) as unknown as Record<ClusterTypes, PanelListType>,
  );

  const isShowSelector = ref(false);

  const selected = shallowRef<Record<string, IValue[]>>({
    mongoCluster: [] as IValue[],
  });

  const disabled = computed(() => !props.clusterId);

  watch(
    () => props.clusterId,
    () => {
      editableTableColumnRef.value?.validate();
    },
  );

  const handleShowSelector = () => {
    if (disabled.value) {
      return;
    }
    isShowSelector.value = true;
  };

  const handleInstanceSelectChange = (data: InstanceSelectorValues<IValue>) => {
    modelValue.value = data.mongoCluster[0].ip;
    selected.value.mongoCluster = data.mongoCluster;
  };
</script>

<style lang="less" scoped>
  .host-selector-button {
    width: 24px;
    font-size: 16px;
    text-align: center;
    cursor: pointer;
    border-radius: 2px;

    &:hover {
      color: #3a84ff;
      background: #f0f1f5;
    }
  }

  .host-selector-button-disabled {
    color: #dcdee5;
    cursor: not-allowed;

    &:hover {
      color: #dcdee5;
      background: #f0f1f5;
    }
  }
</style>
