<template>
  <BkFormItem
    :label="t('推荐套餐')"
    required>
    <CardCheckbox
      v-model="mode"
      :desc="t('自定义配置')"
      :disabled="disabled"
      :disabled-tooltips="t('请先选择版本')"
      :min-width="200"
      :title="t('自定义')"
      true-value="custom" />
    <CardCheckbox
      v-model="mode"
      class="ml-8"
      :desc="t('功能验证、开发调试')"
      :disabled="disabled"
      :disabled-tooltips="t('请先选择版本')"
      :min-width="200"
      :title="t('测试')"
      true-value="basic" />
    <CardCheckbox
      v-model="mode"
      class="ml-8"
      :desc="t('常规生产环境')"
      :disabled="disabled"
      :disabled-tooltips="t('请先选择版本')"
      :min-width="200"
      :title="t('标准')"
      true-value="standard" />
    <CardCheckbox
      v-model="mode"
      class="ml-8"
      :desc="t('高吞吐、大数据量场景')"
      :disabled="disabled"
      :disabled-tooltips="t('请先选择版本')"
      :min-width="200"
      :title="t('高性能')"
      true-value="premium" />
  </BkFormItem>
  <BkFormItem
    label="Qdrant"
    required>
    <PrimaryTable
      bordered
      :data="qdrant"
      row-key="component_name">
      <TableColumn
        col-key="request_cpu"
        :title="t('CPU (核)')">
        <template #default="{ row, rowIndex }: { row: ComponentConfig; rowIndex: number }">
          <DbFormItem
            error-display-type="tooltips"
            :property="`details.qdrant.${rowIndex}.request_cpu`"
            required>
            <BkInput
              v-model="row.request_cpu"
              :disabled="disabled"
              type="number"
              @change="handleSettingChange" />
          </DbFormItem>
        </template>
      </TableColumn>
      <TableColumn
        col-key="request_memory"
        :title="t('内存 (GB)')">
        <template #default="{ row, rowIndex }: { row: ComponentConfig; rowIndex: number }">
          <DbFormItem
            error-display-type="tooltips"
            :property="`details.qdrant.${rowIndex}.request_memory`"
            required>
            <BkInput
              v-model="row.request_memory"
              :disabled="disabled"
              type="number"
              @change="handleSettingChange" />
          </DbFormItem>
        </template>
      </TableColumn>
      <TableColumn
        col-key="storage"
        :title="t('存储 (GiB)')">
        <template #default="{ row, rowIndex }: { row: ComponentConfig; rowIndex: number }">
          <DbFormItem
            error-display-type="tooltips"
            :property="`details.qdrant.${rowIndex}.storage`"
            required>
            <BkInput
              v-model="row.storage"
              :disabled="disabled"
              type="number"
              @change="handleSettingChange" />
          </DbFormItem>
        </template>
      </TableColumn>
      <TableColumn
        col-key="replicas"
        :title="t('节点数')">
        <template #default="{ row, rowIndex }: { row: ComponentConfig; rowIndex: number }">
          <DbFormItem
            error-display-type="tooltips"
            :property="`details.qdrant.${rowIndex}.replicas`"
            required>
            <BkInput
              v-model="row.replicas"
              :disabled="disabled"
              :max="100"
              :min="3"
              type="number" />
          </DbFormItem>
        </template>
      </TableColumn>
    </PrimaryTable>
    <span class="input-desc">{{ t('计算+存储一体，最少 3 个节点，上限 100') }}</span>
  </BkFormItem>
</template>

<script lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getAddonSpecPlan } from '@services/source/kubernetesToolbox';

  import { ClusterTypes } from '@common/const';

  import CardCheckbox from '@views/db-manage/common/db-card-checkbox/CardCheckbox.vue';

  type ComponentSettings = Record<
    string,
    Record<string, ServiceReturnType<typeof getAddonSpecPlan>[number]['components'][number]>
  >;

  export interface ComponentConfig {
    component_name: string;
    replicas: number;
    request_cpu: number | string;
    request_memory: number | string;
    storage: number | string;
  }

  interface Props {
    addonType: ServiceParameters<typeof getAddonSpecPlan>['addonType'];
    addonVersion: string;
    applyMode?: string;
    bkBizId?: number | string;
  }

  export const getDefaultQdrantConfig = () => ({
    component_name: 'qdrant',
    replicas: '' as number | '',
    request_cpu: '' as number | '',
    request_memory: '' as number | '',
    storage: '' as number | '',
  });
</script>

<script setup lang="ts">
  const props = withDefaults(defineProps<Props>(), {
    applyMode: 'SharedMode',
    bkBizId: '',
  });

  const qdrant = defineModel<ReturnType<typeof getDefaultQdrantConfig>[]>('qdrant', {
    required: true,
  });

  const { t } = useI18n();

  let componentSettings = {} as ComponentSettings;

  const mode = ref('custom');

  const disabled = computed(() => !props.addonVersion);

  // 独占集群（isPublic=false）时按业务 ID 取该业务独占的套餐
  const isPublic = computed(() => props.applyMode !== 'ExclusiveMode');
  const bkBizId = computed(() => (props.bkBizId ? Number(props.bkBizId) : undefined));

  const { run: runGetAddonSpecPlan } = useRequest(getAddonSpecPlan, {
    manual: true,
    onSuccess(specPlan) {
      componentSettings = Object.fromEntries(
        specPlan
          .filter((item) => item.dbmClusterType === ClusterTypes.K8S_QDRANT_HA)
          .map((item) => [
            item.specLevel,
            Object.fromEntries(item.components.map((comItem) => [comItem.componentName, comItem])),
          ]),
      );

      // 部署类型/业务变化后已选套餐可能不在新列表中，回退到自定义配置
      if (mode.value !== 'custom' && !componentSettings[mode.value]) {
        mode.value = 'custom';
      }
    },
  });

  watch(
    [() => props.addonVersion, isPublic, bkBizId],
    () => {
      // 业务 ID 未就绪时不请求，避免回显过程中先按默认业务取一次造成结果竞态
      if (!props.addonVersion || !bkBizId.value) {
        return;
      }
      runGetAddonSpecPlan({
        addonType: props.addonType,
        addonVersion: props.addonVersion,
        bkBizId: bkBizId.value,
        isPublic: isPublic.value,
      });
    },
    { immediate: true },
  );

  watch(mode, () => {
    if (mode.value === 'custom') {
      return;
    }

    const settingItem = componentSettings[mode.value];
    const qdrantItem = settingItem?.['qdrant'];

    if (qdrantItem) {
      qdrant.value = [
        {
          component_name: 'qdrant',
          replicas: qdrant.value[0].replicas || 3,
          request_cpu: qdrantItem.cpuCores,
          request_memory: qdrantItem.memoryGb,
          storage: qdrantItem.diskSizeGb,
        },
      ];
    }
  });

  const handleSettingChange = () => {
    mode.value = 'custom';
  };
</script>
