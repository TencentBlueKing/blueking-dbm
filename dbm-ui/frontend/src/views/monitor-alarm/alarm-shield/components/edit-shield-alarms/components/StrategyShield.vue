<template>
  <BkFormItem
    :label="t('屏蔽的策略')"
    property="range"
    required>
    <div class="strategy-shield-main">
      <BkSelect
        v-model="dbValue"
        class="db-select"
        :clearable="false"
        :disabled="disabled"
        :filterable="false"
        @change="handleDbTypeChange">
        <BkOption
          v-for="item in dbList"
          :key="item.value"
          :label="item.label"
          :value="item.value" />
      </BkSelect>
      <BkSelect
        v-model="strategyValue"
        class="strategy-select"
        collapse-tags
        :disabled="disabled"
        filterable
        multiple
        multiple-mode="tag"
        :remote-method="remoteMethod"
        :scroll-loading="scrollLoading"
        @scroll-end="handleScrollEnd">
        <BkOption
          v-for="item in strategyList"
          :key="item.id"
          :label="item.name"
          :value="item.id" />
      </BkSelect>
    </div>
  </BkFormItem>
  <DimensionShield
    ref="dimensionShieldRef"
    :data="data"
    :disabled="disabled" />
  <BkFormItem
    class="mt-24"
    :label="t('屏蔽的告警等级')"
    property="level"
    required>
    <BkCheckboxGroup v-model="level">
      <BkCheckbox
        v-for="(item, index) in alarmLevelList"
        :key="index"
        :label="item.value">
        <span
          class="sign-bar"
          :class="[`sign-bar-${item.theme}`]"></span>
        <span>{{ item.label }}</span>
      </BkCheckbox>
    </BkCheckboxGroup>
  </BkFormItem>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import AlarmShieldModel from '@services/model/monitor/alarm-shield';
  import { getPolicyList } from '@services/source/monitor';

  import { DBTypeInfos, DBTypes } from '@common/const';

  import DimensionShield from './dimension-shield/Index.vue';

  interface Props {
    data?: AlarmShieldModel['dimension_config'];
    disabled?: boolean;
  }

  interface Exposes {
    getValue: () =>
      | {
          dimension_config: {
            id: number[];
          };
        }
      | false;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    disabled: false,
  });

  const { t } = useI18n();

  const dimensionShieldRef = ref<InstanceType<typeof DimensionShield>>();
  const dbValue = ref('');
  const level = ref<number[]>([]);
  const strategyValue = ref<number[]>([]);
  const scrollLoading = ref(false);
  const requestParams = ref({
    bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    db_type: '',
    limit: 10,
    name: '',
    offset: 0,
  });

  const strategyList = shallowRef<
    {
      id: number;
      name: string;
    }[]
  >([]);

  const dbList = Object.keys(DBTypeInfos).map((key) => ({
    label: DBTypeInfos[key as DBTypes].name,
    value: key,
  }));

  const alarmLevelList = [
    {
      label: t('提醒'),
      theme: 'info',
      value: 3,
    },
    {
      label: t('告警'),
      theme: 'warning',
      value: 2,
    },
    {
      label: t('致命'),
      theme: 'critical',
      value: 1,
    },
  ];

  let isAppend = false;

  const { run: fetchPolicyList } = useRequest(getPolicyList, {
    manual: true,
    onSuccess(data) {
      scrollLoading.value = false;
      if (isAppend) {
        strategyList.value.push(...data.results);
        isAppend = false;
        return;
      }

      strategyList.value = data.results;
    },
  });

  const { run: fetchExistPolicyList } = useRequest(getPolicyList, {
    manual: true,
    onSuccess(data) {
      dbValue.value = data.results[0].db_type;
      strategyList.value.unshift(...data.results);
    },
  });

  watch(
    requestParams,
    () => {
      fetchPolicyList(requestParams.value);
    },
    {
      deep: true,
      immediate: true,
    },
  );

  watch(
    () => props.data,
    () => {
      if (props.data) {
        if (props.data.strategy_id?.length) {
          strategyValue.value = props.data.strategy_id;
          fetchExistPolicyList({
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            monitor_policy_ids: props.data.strategy_id.join(','),
          });
        }

        level.value = props.data.level;
      }
    },
    { immediate: true },
  );

  const handleDbTypeChange = (value: string) => {
    strategyValue.value = [];
    requestParams.value.db_type = value;
    requestParams.value.offset = 0;
  };

  const remoteMethod = (value: string) => {
    isAppend = false;
    requestParams.value.name = value;
    requestParams.value.offset = 0;
  };

  const handleScrollEnd = () => {
    scrollLoading.value = true;
    isAppend = true;
    requestParams.value.offset += requestParams.value.limit;
  };

  defineExpose<Exposes>({
    getValue(type = 'strategy') {
      if (type === 'strategy') {
        if (!dbValue.value || !strategyValue.value.length) {
          return false;
        }
      }
      const dimensionInfo = dimensionShieldRef.value!.getValue();
      return {
        dimension_config: {
          id: strategyValue.value,
          level: level.value,
          ...dimensionInfo.dimension_config,
        },
      };
    },
  });
</script>
<style lang="less" scoped>
  .strategy-shield-main {
    display: flex;

    .db-select {
      width: 90px;

      :deep(.bk-input) {
        // border-right: transparent;
        border-top-right-radius: 0;
        border-bottom-right-radius: 0;
      }
    }

    .strategy-select {
      flex: 1;

      :deep(.bk-select-tag) {
        border-bottom-left-radius: 0;
        border-top-left-radius: 0;
      }
    }
  }
</style>
