<template>
  <BkForm
    class="search-box"
    form-type="vertical">
    <BkFormItem
      :label="t('DB类型')"
      required>
      <Db
        v-model:model-value="modelValue"
        @change="handleChangeDbType" />
    </BkFormItem>
    <BkFormItem :label="t('专业业务')">
      <Biz
        ref="bizRef"
        @change="handleChange" />
    </BkFormItem>
    <BkFormItem :label="t('地域 - 园区')">
      <Region
        ref="regionRef"
        @change="handleChange" />
    </BkFormItem>
    <BkFormItem :label="t('规格')">
      <Spec
        ref="specRef"
        :db-type="modelValue"
        @change="handleChange" />
    </BkFormItem>
  </BkForm>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes, DBTypes, MachineTypes } from '@common/const';

  import Biz from './components/Biz.vue';
  import Db from './components/Db.vue';
  import Region from './components/Region.vue';
  import Spec from './components/Spec.vue';

  interface Emits {
    (e: 'search'): void;
    (e: 'change', dbType: DBTypes): void;
  }

  interface Exposes {
    getValue: () => Promise<{
      for_biz?: number;
      city?: string;
      sub_zones?: string[];
      spec_param: {
        db_type: DBTypes;
        machine_type?: MachineTypes;
        cluster_type?: ClusterTypes;
        spec_id_list?: number[];
      };
    }>;
  }

  const emits = defineEmits<Emits>();
  const modelValue = defineModel<DBTypes>({
    default: DBTypes.MYSQL,
  });

  const { t } = useI18n();

  const bizRef = ref<InstanceType<typeof Biz>>();
  const regionRef = ref<InstanceType<typeof Region>>();
  const specRef = ref<InstanceType<typeof Spec>>();

  const handleChangeDbType = (dbType: DBTypes) => {
    specRef.value!.reset();
    nextTick(() => {
      emits('change', dbType);
    });
  };

  const handleChange = () => {
    emits('search');
  };

  const filterEmptyValues = (obj: any): any =>
    _.pickBy(obj, (value) => value !== '' && value !== 0 && (!_.isArray(value) || !_.isEmpty(value)));

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([bizRef.value!.getValue(), regionRef.value!.getValue(), specRef.value!.getValue()]).then(
        ([biz, region, spec]) =>
          filterEmptyValues({
            ...biz,
            ...region,
            spec_param: filterEmptyValues(spec.spec_param),
          }),
      );
    },
  });
</script>

<style lang="less" scoped>
  .search-box {
    display: flex;

    :deep(.bk-form-item) {
      margin-bottom: 0;

      .bk-form-label {
        font-weight: initial;
      }

      & ~ .bk-form-item {
        margin-left: 16px;
      }

      &:nth-child(-n + 2) {
        flex: 1;
      }

      &:nth-last-child(2) {
        flex: 1.5;
      }

      &:nth-last-child(1) {
        flex: 2;
      }
    }
  }
</style>
