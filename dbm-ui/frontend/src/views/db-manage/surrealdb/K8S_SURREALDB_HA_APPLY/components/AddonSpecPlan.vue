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
    label="Surreal"
    required>
    <PrimaryTable
      bordered
      :data="surreal"
      row-key="component_name">
      <TableColumn
        col-key="request_cpu"
        :title="t('CPU (核)')">
        <template #default="{ row, rowIndex }: { row: ComponentConfig; rowIndex: number }">
          <DbFormItem
            error-display-type="tooltips"
            :property="`details.surreal.${rowIndex}.request_cpu`"
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
            :property="`details.surreal.${rowIndex}.request_memory`"
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
        col-key="replicas"
        :title="t('节点数')">
        <template #default="{ row, rowIndex }: { row: ComponentConfig; rowIndex: number }">
          <DbFormItem
            error-display-type="tooltips"
            :property="`details.surreal.${rowIndex}.replicas`"
            required>
            <BkInput
              v-model="row.replicas"
              :disabled="disabled"
              :max="100"
              :min="2"
              type="number" />
          </DbFormItem>
        </template>
      </TableColumn>
    </PrimaryTable>
    <span class="input-desc">{{ t('计算节点，无需存储，最少 2 个节点，上限 100') }}</span>
  </BkFormItem>
  <BkFormItem
    label="TiKV"
    required>
    <PrimaryTable
      bordered
      :data="tikv"
      row-key="component_name">
      <TableColumn
        col-key="request_cpu"
        :title="t('CPU (核)')">
        <template #default="{ row, rowIndex }: { row: ComponentConfig; rowIndex: number }">
          <DbFormItem
            error-display-type="tooltips"
            :property="`details.tikv.${rowIndex}.request_cpu`"
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
            :property="`details.tikv.${rowIndex}.request_memory`"
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
            :property="`details.tikv.${rowIndex}.storage`"
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
            :property="`details.tikv.${rowIndex}.replicas`"
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
    <span class="input-desc">{{ t('存储节点，最少 3 个节点，上限 100') }}</span>
  </BkFormItem>
  <BkFormItem
    label="PD"
    required>
    <PrimaryTable
      bordered
      :data="pd"
      row-key="component_name">
      <TableColumn
        col-key="request_cpu"
        :title="t('CPU (核)')">
        <template #default="{ row, rowIndex }: { row: ComponentConfig; rowIndex: number }">
          <DbFormItem
            error-display-type="tooltips"
            :property="`details.pd.${rowIndex}.request_cpu`"
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
            :property="`details.pd.${rowIndex}.request_memory`"
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
            :property="`details.pd.${rowIndex}.storage`"
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
            :property="`details.pd.${rowIndex}.replicas`"
            required>
            <BkInput
              v-model="row.replicas"
              :disabled="disabled"
              :min="3"
              type="number" />
          </DbFormItem>
        </template>
      </TableColumn>
    </PrimaryTable>
    <span class="input-desc">{{ t('调度节点，最少 3 个节点') }}</span>
  </BkFormItem>
</template>

<script lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getAddonSpecPlan } from '@services/source/kubernetesToolbox';

  import { ClusterTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  type ComponentSettings = Record<
    string,
    Record<string, ServiceReturnType<typeof getAddonSpecPlan>[number]['components'][number]>
  >;

  interface ComponentConfig {
    component_name: string;
    replicas: number;
    request_cpu: string;
    request_memory: string;
    storage: string;
  }

  interface Props {
    addonType: ServiceParameters<typeof getAddonSpecPlan>['addonType'];
    addonVersion: string;
  }

  export const getDefaultSurrealConfig = () => ({
    component_name: 'surreal',
    replicas: '' as number | '',
    request_cpu: '' as number | '',
    request_memory: '' as number | '',
  });

  export const getDefaultPdConfig = () => ({
    component_name: 'pd',
    replicas: '' as number | '',
    request_cpu: '' as number | '',
    request_memory: '' as number | '',
    storage: '' as number | '',
  });

  export const getDefaultTikvConfig = () => ({
    component_name: 'tikv',
    replicas: '' as number | '',
    request_cpu: '' as number | '',
    request_memory: '' as number | '',
    storage: '' as number | '',
  });
</script>

<script setup lang="ts">
  const props = defineProps<Props>();

  const surreal = defineModel<ReturnType<typeof getDefaultSurrealConfig>[]>('surreal', {
    required: true,
  });
  const pd = defineModel<ReturnType<typeof getDefaultPdConfig>[]>('pd', {
    required: true,
  });
  const tikv = defineModel<ReturnType<typeof getDefaultTikvConfig>[]>('tikv', {
    required: true,
  });

  const { t } = useI18n();

  let componentSettings = {} as ComponentSettings;

  const mode = ref('custom');

  const disabled = computed(() => !props.addonVersion);

  const { run: runGetAddonSpecPlan } = useRequest(getAddonSpecPlan, {
    manual: true,
    onSuccess(specPlan) {
      componentSettings = Object.fromEntries(
        specPlan
          .filter((item) => item.dbmClusterType === ClusterTypes.K8S_SURREALDB_HA)
          .map((item) => [
            item.specLevel,
            Object.fromEntries(item.components.map((comItem) => [comItem.componentName, comItem])),
          ]),
      );
    },
  });

  watch(
    () => props.addonVersion,
    () => {
      if (props.addonVersion) {
        // surreal.value = [getDefaultSurrealConfig()];
        // pd.value = [getDefaultPdConfig()];
        // tikv.value = [getDefaultTikvConfig()];

        runGetAddonSpecPlan({
          addonType: props.addonType,
          addonVersion: props.addonVersion,
        });
      }
    },
  );

  watch(mode, () => {
    if (mode.value === 'custom') {
      return;
    }

    const settingItem = componentSettings[mode.value];
    const surrealItem = settingItem['surreal'];
    const pdItem = settingItem['pd'];
    const tikvItem = settingItem['tikv'];

    surreal.value = [
      {
        component_name: 'surreal',
        replicas: surreal.value[0].replicas || 2,
        request_cpu: surrealItem.cpuCores,
        request_memory: surrealItem.memoryGb,
      },
    ];
    pd.value = [
      {
        component_name: 'pd',
        replicas: pd.value[0].replicas || 3,
        request_cpu: pdItem.cpuCores,
        request_memory: pdItem.memoryGb,
        storage: pdItem.diskSizeGb,
      },
    ];
    tikv.value = [
      {
        component_name: 'tikv',
        replicas: tikv.value[0].replicas || 3,
        request_cpu: tikvItem.cpuCores,
        request_memory: tikvItem.memoryGb,
        storage: tikvItem.diskSizeGb,
      },
    ];
  });

  const handleSettingChange = () => {
    mode.value = 'custom';
  };
</script>
