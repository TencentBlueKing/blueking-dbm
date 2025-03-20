<template>
  <div class="web-query-main-page">
    <BkAlert
      closable
      theme="info"
      :title="t('用于户跨业务多实例查询')" />
    <BkForm
      ref="formRef"
      class="web-query-form"
      form-type="vertical"
      :model="formData"
      :rules="rules">
      <BkFormItem
        v-if="isMysql"
        :label="t('查询类型')"
        required>
        <BkRadioGroup
          v-model="formData.queryType"
          style="width: 300px"
          type="card">
          <BkRadioButton label="proxy">Proxy</BkRadioButton>
          <BkRadioButton label="master_slave">Master/Slave</BkRadioButton>
        </BkRadioGroup>
      </BkFormItem>
      <BkFormItem
        :label="t('查询实例')"
        property="instance"
        required>
        <div class="query-instance-main">
          <BkInput
            v-model="formData.instance"
            :autosize="autoSizeConf"
            clearable
            :placeholder="t('请输入查询实例或从拓扑选择，多个逗号或换行分隔')"
            :resize="false"
            style="width: 750px; height: 115px"
            type="textarea" />
          <!-- <BkButton class="ml-8">
            <DbIcon
              style="margin-right: 6px; color: #979ba5"
              type="add" />
            {{ t('从拓扑添加') }}
          </BkButton> -->
        </div>
      </BkFormItem>
      <BkFormItem
        :label="t('查询 SQL')"
        required>
        <SQLQuery
          :db-type="dbType"
          :instances="instanceList"
          :query-type="formData.queryType"
          @execute="handleExecute" />
      </BkFormItem>
    </BkForm>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { checkInstance } from '@services/source/dbbase';

  import { DBTypes } from '@common/const';
  import { batchInputSplitRegex, ipPort } from '@common/regex';

  import SQLQuery from './components/sql-query/Index.vue';

  interface Props {
    dbType?: DBTypes.MYSQL | DBTypes.TENDBCLUSTER | DBTypes.SQLSERVER;
  }

  const props = withDefaults(defineProps<Props>(), {
    dbType: DBTypes.MYSQL,
  });

  const { t } = useI18n();

  const formRef = ref();
  const formData = ref({
    instance: '',
    queryType: 'proxy',
  });

  const isMysql = computed(() => props.dbType === DBTypes.MYSQL);
  const instanceList = computed(() =>
    formData.value.instance.split(batchInputSplitRegex).filter((item) => ipPort.test(item)),
  );

  const autoSizeConf = {
    maxRows: 8,
    minRows: 5,
  };

  let message = '';

  const rules = {
    instance: [
      {
        message: () => message,
        trigger: 'blur',
        validator: async (value: string) => {
          if (!isMysql.value) {
            return true;
          }

          const instanceList = value.split(batchInputSplitRegex).filter((item) => ipPort.test(item));
          const instancesResult = await checkInstance({ instance_addresses: instanceList });
          const resultList = instancesResult.map((item) => item.instance_address);
          const invalidList = _.difference(instanceList, resultList);
          if (formData.value.queryType === 'proxy') {
            const notMatchlist = instancesResult.reduce<string[]>((results, item) => {
              if (item.role === 'proxy') {
                return results;
              }

              results.push(item.instance_address);
              return results;
            }, []);
            if (!notMatchlist.length && !invalidList.length) {
              return true;
            }

            const finalList = [...invalidList, ...notMatchlist];
            message = t('n不是proxy实例', { n: finalList.join(' , ') });
            return false;
          }

          const notMatchlist = instancesResult.reduce<string[]>((results, item) => {
            if (item.role === 'master' || item.role === 'slave') {
              return results;
            }

            results.push(item.instance_address);
            return results;
          }, []);
          if (!notMatchlist.length && !invalidList.length) {
            return true;
          }

          const finalList = [...invalidList, ...notMatchlist];
          message = t('{n}不是master/slave实例', { n: finalList.join(' , ') });
          return false;
        },
      },
    ],
  };

  const handleExecute = () => {
    formRef.value.validate('instance');
  };
</script>
<style lang="less">
  .web-query-main-page {
    height: 100%;
    overflow-y: auto;

    .web-query-form {
      margin-top: 16px;

      .bk-form-label {
        font-weight: 700;
      }

      .query-instance-main {
        display: flex;
        width: 100%;
      }
    }
  }
</style>
