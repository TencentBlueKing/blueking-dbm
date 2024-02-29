<template>
  <div class="inspection-search-box">
    <BkForm form-type="vertical">
      <BkFormItem :label="t('日期')">
        <BkDatePicker
          clearable
          :model-value="[formData.create_at__gte, formData.create_at__lte]"
          type="datetimerange"
          @change="handleDateChange" />
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
    <div style="padding: 0 12px">
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

<<<<<<< HEAD
  import { useUrlSearch } from '@hooks';

=======
>>>>>>> c3acfbeaf (style(frontend): 使用prettier代码格式化 #3408)
  interface Emits {
    (e: 'change', value: Record<string, any>): void;
  }

  const emits = defineEmits<Emits>();

  const genDefaultData = () => ({
    create_at__gte: '',
    create_at__lte: '',
    cluster: '',
    status: '',
  });

  const filterInvalidValue = (params: Record<string, any>) =>
    Object.keys(params).reduce((result, item) => {
      if (params[item]) {
        return Object.assign(result, {
          [item]: params[item],
        });
      }
      return result;
    }, {});

  const { t } = useI18n();
  const { getSearchParams } = useUrlSearch();

  const formData = reactive(genDefaultData());

<<<<<<< HEAD
  const serachParams = getSearchParams();
  Object.keys(formData).forEach((key) => {
    formData[key as keyof typeof formData] = serachParams[key];
  });

=======
>>>>>>> c3acfbeaf (style(frontend): 使用prettier代码格式化 #3408)
  const { data: clusterList } = useRequest(queryAllTypeCluster, {
    defaultParams: [
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      },
    ],
  });

<<<<<<< HEAD
  const handleDateChange = (value: [string, string]) => {
    [formData.create_at__gte, formData.create_at__lte] = value;
  };

=======
>>>>>>> c3acfbeaf (style(frontend): 使用prettier代码格式化 #3408)
  const handleSubmit = () => {
    emits(
      'change',
      filterInvalidValue({
        ...formData,
<<<<<<< HEAD
        create_at__gte: formData.create_at__gte ? dayjs(formData.create_at__gte).format('YYYY-MM-DD HH:mm:ss') : '',
        create_at__lte: formData.create_at__lte ? dayjs(formData.create_at__lte).format('YYYY-MM-DD HH:mm:ss') : '',
=======
        create_at: formData.create_at ? dayjs(formData.create_at).format('YYYY-MM-DD') : '',
>>>>>>> c3acfbeaf (style(frontend): 使用prettier代码格式化 #3408)
      }),
    );
  };

  const handleReset = () => {
    Object.assign(formData, genDefaultData());
  };
</script>
<style lang="less">
  .inspection-search-box {
    padding: 16px 12px 36px;
    background: #fff;

    .bk-form {
      display: flex;

      .bk-form-item {
        flex: 1;
        padding: 0 12px;
      }
    }

    .bk-date-picker {
      width: 100%;
    }
  }
</style>
