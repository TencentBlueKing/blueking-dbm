<template>
  <div class="inspection-search-box">
    <BkForm form-type="vertical">
      <BkFormItem :label="t('日期')">
        <BkDatePicker v-model="formData.create_at" />
      </BkFormItem>
      <BkFormItem :label="t('集群')">
        <BkSelect
          v-model="formData.cluster"
          filterable>
          <BkOption
            v-for="clusterItem in clusterList"
            :key="clusterItem.id"
            :label="`[${clusterItem.id}] ${clusterItem.immute_domain}`"
            :value="clusterItem.immute_domain" />
        </BkSelect>
      </BkFormItem>
      <BkFormItem :label="t('状态')">
        <BkSelect v-model="formData.status">
          <BkOption
            :label="t('正常')"
            :value="1" />
          <BkOption
            :label="t('异常')"
            :value="0" />
          <BkOption
            :label="t('未知')"
            :value="-1" />
        </BkSelect>
      </BkFormItem>
    </BkForm>
    <div style="padding: 0 12px;">
      <BkButton
        theme="primary"
        @click="handleSubmit">
        {{ t('查询') }}
      </BkButton>
      <BkButton
        class="ml-8"
        @click="handleReset">
        {{ t('清空') }}
      </BkButton>
    </div>
  </div>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { reactive } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { queryAllTypeCluster } from '@services/dbbase';

  interface Emits{
    (e: 'change', value: Record<string, any>): void
  }

  const emits = defineEmits<Emits>();

  const genDefaultData = () => ({
    create_at: '',
    cluster: '',
    status: '',
  });

  const filterInvalidValue = (params: Record<string, any>) => Object.keys(params).reduce((result, item) => {
    if (params[item]) {
      return Object.assign(result, {
        [item]: params[item],
      });
    }
    return result;
  }, {});

  const { t } = useI18n();

  const formData = reactive(genDefaultData());

  const {
    data: clusterList,
  } = useRequest(queryAllTypeCluster, {
    defaultParams: [
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      },
    ],
  });


  const handleSubmit = () => {
    emits('change', filterInvalidValue({
      ...formData,
      create_at: formData.create_at ? dayjs(formData.create_at).format('YYYY-MM-DD') : '',
    }));
  };

  const handleReset = () => {
    Object.assign(formData, genDefaultData());
  };
</script>
<style lang="less">
  .inspection-search-box {
    padding: 16px 12px 36px;
    background: #fff;

    .bk-form{
      display: flex;

      .bk-form-item{
        flex: 1;
        padding: 0 12px;
      }
    }

    .bk-date-picker{
      width: 100%;
    }
  }
</style>
