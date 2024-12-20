<template>
  <EditableTableColumn
    ref="editableTableColumn"
    :append-rules="rules"
    field="target_host"
    :label="t('目标主机')"
    :loading="isLoading"
    :min-width="300"
    required>
    <EditInput
      v-model="modelValue"
      :disabled="disabled"
      :placeholder="t('请输入或选择主机')">
      <template #append>
        <span v-bk-tooltips="t('选择主机')">
          <BkButton
            class="host-selector-btn"
            :disabled="disabled"
            size="small"
            @click="handleShowSelector">
            <DbIcon type="host-select" />
          </BkButton>
        </span>
      </template>
    </EditInput>
    <InstanceSelector
      v-model:is-show="isShowSelector"
      :cluster-types="['mongoCluster']"
      :selected="selected"
      :tab-list-config="tabListConfig"
      @change="handleInstanceSelectChange" />
  </EditableTableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { checkInstance } from '@services/source/dbbase';

  import { ClusterTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import { Column as EditableTableColumn, Input as EditInput } from '@components/editable-table/Index.vue';
  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  interface Props {
    clusterId: number;
    disabled: boolean;
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      validator: (value: string) => ipv4.test(value),
      trigger: 'change',
      message: t('目标主机输入格式有误'),
    },
    {
      validator: async (value: string) => {
        isLoading.value = true;
        return checkInstance({
          instance_addresses: [value],
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_ids: [props.clusterId],
        })
          .then((instance) => instance.length > 0)
          .finally(() => {
            isLoading.value = false;
          });
      },
      trigger: 'change',
      message: t('目标主机不存在'),
    },
  ];

  const tabListConfig = computed(
    () =>
      ({
        mongoCluster: [
          {
            topoConfig: {
              filterClusterId: props.clusterId,
            },
            tableConfig: {
              multiple: false,
            },
          },
        ],
      }) as unknown as Record<ClusterTypes, PanelListType>,
  );

  const isShowSelector = ref(false);
  const isLoading = ref(false);

  const selected = shallowRef<Record<string, IValue[]>>({
    mongoCluster: [] as IValue[],
  });

  const handleShowSelector = () => {
    isShowSelector.value = true;
  };

  const handleInstanceSelectChange = (data: InstanceSelectorValues<IValue>) => {
    modelValue.value = data.mongoCluster[0].ip;
    selected.value.mongoCluster = data.mongoCluster;
  };
</script>

<style lang="less" scoped>
  .host-selector-btn {
    width: 24px;
    font-size: 16px;
    border: none;
    border-radius: 2px;

    &:hover {
      color: #3a84ff;
      background: #f0f1f5;
    }
  }
</style>
