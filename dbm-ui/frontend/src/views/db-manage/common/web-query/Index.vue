<template>
  <div
    ref="pageRef"
    class="web-query-main-page">
    <BkAlert
      closable
      theme="info"
      :title="alertTip" />
    <BkForm
      ref="formRef"
      class="web-query-form"
      form-type="vertical"
      :model="formData"
      :rules="rules"
      @validate="handleFormValidate">
      <BkFormItem
        v-if="isMysql"
        :label="t('查询类型')"
        required>
        <BkRadioGroup
          v-model="formData.queryType"
          style="width: 300px"
          type="card">
          <BkRadioButton
            v-bk-tooltips="t('暂不支持，敬请期待')"
            disabled
            label="proxy">
            Proxy
          </BkRadioButton>
          <BkRadioButton label="master_slave">Master/Slave</BkRadioButton>
        </BkRadioGroup>
      </BkFormItem>
      <BkFormItem
        :label="t('实例')"
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
            type="textarea"
            @blur="handleInitInvalidValue"
            @input="handleInitInvalidValue" />
          <!-- <BkButton class="ml-8">
            <DbIcon
              style="margin-right: 6px; color: #979ba5"
              type="add" />
            {{ t('从拓扑添加') }}
          </BkButton> -->
          <div
            v-if="invalidInstanceList.length"
            class="error-info-main"
            @click="handleCopyInvalidInstances">
            <DbIcon
              v-bk-tooltips="t('复制无效实例')"
              type="copy" />
          </div>
        </div>
      </BkFormItem>
      <BkFormItem
        :label="t('查询 SQL')"
        required>
        <SQLQuery
          :db-type="dbType"
          :executable="isEditorExecutable"
          :instances="instanceList"
          :query-type="formData.queryType" />
      </BkFormItem>
    </BkForm>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { checkInstance } from '@services/source/dbbase';
  import { simpleCheckAllowed } from '@services/source/iam';

  import { DBTypes } from '@common/const';
  import { batchInputSplitRegex, ipPort } from '@common/regex';

  import { execCopy } from '@utils';

  import SQLQuery from './components/sql-query/Index.vue';

  interface Props {
    actionId: string;
    dbType?: DBTypes.MYSQL | DBTypes.TENDBCLUSTER | DBTypes.SQLSERVER;
  }

  const props = withDefaults(defineProps<Props>(), {
    dbType: DBTypes.MYSQL,
  });

  const { t } = useI18n();

  const pageRef = ref<HTMLElement>();
  const formRef = ref();
  const formData = ref({
    instance: '',
    queryType: 'master_slave',
  });
  const invalidInstanceList = ref<string[]>([]);
  const isEditorExecutable = ref(false);

  const isMysql = computed(() => props.dbType === DBTypes.MYSQL);
  const instanceList = computed(() =>
    formData.value.instance.split(batchInputSplitRegex).filter((item) => ipPort.test(item)),
  );
  const alertTip = computed(() =>
    isMysql.value ? t('执行常用管理命令，支持 Proxy 和 Backend 操作') : t('执行常用管理命令，支持spider、Backend'),
  );

  const autoSizeConf = {
    maxRows: 8,
    minRows: 5,
  };

  const rules = {
    instance: [
      {
        message: t('不能为空'),
        trigger: 'blur',
        validator: (value: string) => !!value,
      },
      {
        message: t('实例格式错误，请输入 IP:Port'),
        trigger: 'blur',
        validator: (value: string) => {
          const inputValue = value.trim();
          const instanceList = inputValue.split(batchInputSplitRegex);
          return instanceList.every((item) => ipPort.test(item));
        },
      },
      {
        message: t('存在无效实例'),
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
              invalidInstanceList.value = [];
              return true;
            }

            invalidInstanceList.value = [...invalidList, ...notMatchlist];
            return false;
          }

          const notMatchlist = instancesResult.reduce<string[]>((results, item) => {
            if (['master', 'orphan', 'repeater', 'slave'].includes(item.role)) {
              return results;
            }

            results.push(item.instance_address);
            return results;
          }, []);
          if (!notMatchlist.length && !invalidList.length) {
            invalidInstanceList.value = [];
            return true;
          }

          invalidInstanceList.value = [...invalidList, ...notMatchlist];
          return false;
        },
      },
    ],
  };

  const handleFormValidate = (_: unknown, isValid: boolean) => {
    isEditorExecutable.value = isValid;
  };

  const handleInitInvalidValue = () => {
    invalidInstanceList.value = [];
  };

  const handleCopyInvalidInstances = () => {
    execCopy(invalidInstanceList.value.join('\n'));
  };

  simpleCheckAllowed(
    {
      action_id: props.actionId,
      is_raise_exception: true,
    },
    {
      permission: 'page',
    },
  );
</script>
<style lang="less">
  .web-query-main-page {
    height: 100%;

    .web-query-form {
      margin-top: 16px;

      .bk-form-label {
        font-weight: 700;
      }

      .query-instance-main {
        position: relative;
        display: flex;
        width: 100%;

        .error-info-main {
          position: absolute;
          bottom: -26px;
          left: 76px;
          color: #3a84ff;
          cursor: pointer;
        }
      }
    }
  }
</style>
