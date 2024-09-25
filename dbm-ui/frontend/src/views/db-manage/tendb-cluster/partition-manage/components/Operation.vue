<template>
  <BkSideslider
    v-model:is-show="isShow"
    render-directive="if"
    :title="data ? (data.id ? t('编辑分区策略') : t('克隆分区策略')) : t('新建分区策略')"
    :width="1000">
    <div class="partition-operation-box">
      <BkAlert
        class="mb-16"
        theme="info">
        <div>{{ t('表中包含数据，建议在低峰期执行分区；') }}</div>
        <div>{{ t('表中行数大于1千万或者表数据量大于300GB，不允许执行分区；') }}</div>
      </BkAlert>
      <DbForm
        ref="formRef"
        form-type="vertical"
        :model="formData"
        :rules="rules">
        <DbFormItem
          :label="t('目标集群')"
          property="cluster_id"
          required>
          <BkSelect
            :loading="isCluserListLoading"
            :model-value="formData.cluster_id || undefined"
            @change="handleClusterChange">
            <BkOption
              v-for="item in clusterList?.results"
              :id="item.id"
              :key="item.id"
              :name="item.master_domain" />
          </BkSelect>
        </DbFormItem>
        <DbFormItem
          :label="t('目标 DB')"
          property="dblikes"
          required>
          <BkTagInput
            v-model="formData.dblikes"
            allow-create
            :disabled="isEditMode"
            :placeholder="t('请输入目标 DB')" />
        </DbFormItem>
        <DbFormItem
          :label="t('目标表')"
          property="tblikes"
          required>
          <BkPopover
            :is-show="isTblikePopShow"
            placement="top"
            theme="light"
            trigger="manual">
            <BkTagInput
              v-model="formData.tblikes"
              allow-create
              :disabled="isEditMode"
              :placeholder="t('支持多张表')"
              @blur="handleTblikeBlur"
              @focus="handleTblikeFocus" />
            <template #content>
              <p>{{ t('注：不支持通配符 *, %, ?') }}</p>
              <p>{{ t('Enter 完成内容输入') }}</p>
            </template>
          </BkPopover>
        </DbFormItem>
        <DbFormItem
          :label="t('字段类型')"
          property="partition_column_type"
          required>
          <BkSelect v-model="formData.partition_column_type">
            <BkOption
              id="int"
              name="整型(int)" />
            <BkOption
              id="datetime"
              name="日期类型(date)" />
            <BkOption
              id="timestamp"
              name="时间戳类型(timestamp)" />
          </BkSelect>
        </DbFormItem>
        <DbFormItem
          :label="t('分区字段')"
          property="partition_column"
          required>
          <BkInput
            v-model="formData.partition_column"
            :placeholder="t('须为时间类型的字段，如2022-12-12 或 2022.12.12')" />
        </DbFormItem>
        <DbFormItem
          :description="t('多少天为一个分区，例如 7 天为一个分区')"
          :label="t('分区间隔')"
          property="partition_time_interval"
          required>
          <BkInput
            v-model="formData.partition_time_interval"
            :min="1"
            :suffix="t('天')"
            type="number" />
        </DbFormItem>
        <DbFormItem
          :description="t('当到达天数后过去的数据会被定期删除，且必须是分区区间的整数倍')"
          :label="t('数据过期时间')"
          property="expire_time"
          required>
          <BkInput
            v-model="formData.expire_time"
            :min="1"
            :suffix="t('天')"
            type="number" />
        </DbFormItem>
      </DbForm>
    </div>
    <template #footer>
      <BkPopConfirm
        :content="verifyWarnTip"
        :is-show="warnConfirming"
        :title="data && data.id ? t('确定提交？') : t('确定保存并执行？')"
        trigger="manual"
        width="350"
        @cancel="handleVerifyCancel"
        @confirm="handleVerifyConfirm">
        <BkButton
          :loading="warnConfirming"
          style="width: 100px"
          theme="primary"
          @click="handleSubmit">
          {{ data && data.id ? t('提交') : t('保存并执行') }}
        </BkButton>
      </BkPopConfirm>
      <BkButton
        class="ml-8"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type PartitionModel from '@services/model/partition/partition';
  import {
    create as createParitition,
    edit as editPartition,
    verifyPartitionField,
  } from '@services/source/partitionManage';
  import { getTendbClusterList } from '@services/source/tendbcluster';

  import { dbSysExclude } from '@common/const';
  import { dbRegex } from '@common/regex';

  interface Props {
    data?: PartitionModel;
  }

  interface Emits {
    (e: 'editSuccess'): void;
    (e: 'createSuccess', params: ServiceReturnType<typeof createParitition>, clusterId: number): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const initFormData = () => ({
    cluster_id: undefined as unknown as number,
    dblikes: [] as string[],
    tblikes: [] as string[],
    partition_column: '',
    partition_column_type: 'int',
    expire_time: 30,
    partition_time_interval: undefined as unknown as number,
  });

  let showPopConfirm = false;

  const { t } = useI18n();

  const formRef = ref();
  const isEditMode = ref(false);
  const isTblikePopShow = ref(false);
  const warnConfirming = ref(false);
  const verifyWarnTip = ref('');

  const formData = reactive(initFormData());

  const rules = computed(() => ({
    dblikes: [
      {
        required: true,
        validator: (value: string[]) => value.length > 0,
        message: t('目标 DB 不能为空'),
        trigger: 'blur',
      },
      {
        validator: (value: string[]) => !value.some((item) => item === '*'),
        message: t('目标 DB 不能为*'),
        trigger: 'blur',
      },
      {
        validator: (value: string[]) => value.every((item) => dbRegex.test(item)),
        message: t('只允许数字、大小写字母开头和结尾，或%结尾'),
        trigger: 'change',
      },
      {
        validator: (value: string[]) => value.every((item) => !dbSysExclude.includes(item)),
        message: t('不能是系统库'),
        trigger: 'change',
      },
    ],
    tblikes: [
      {
        required: true,
        validator: (value: string[]) => value.length > 0,
        message: t('目标表不能为空'),
        trigger: 'blur',
      },
      {
        validator: (value: string[]) => value.every((item) => !/[*%?]/.test(item)),
        message: t('不支持通配符 *, %, ?'),
        trigger: 'blur',
      },
    ],
    partition_column: [
      {
        validator: () => {
          if (
            !formData.cluster_id ||
            formData.dblikes.length < 1 ||
            formData.tblikes.length < 1 ||
            !formData.partition_column_type
          ) {
            return false;
          }
          return true;
        },
        message: t('请输入完整信息验证分区字段'),
        trigger: 'blur',
      },
      {
        validator: (value: string) =>
          verifyPartitionField({
            cluster_id: formData.cluster_id,
            dblikes: formData.dblikes,
            tblikes: formData.tblikes,
            partition_column: value,
            partition_column_type: formData.partition_column_type,
          }).then((result) => {
            if (result) {
              showPopConfirm = true;
              verifyWarnTip.value = result;
            } else {
              showPopConfirm = false;
              verifyWarnTip.value = '';
            }
            return true;
          }),
        message: t('分区字段验证失败'),
        trigger: 'blur',
      },
    ],
    expire_time: [
      {
        required: true,
        validator: (value: number) => Boolean(value),
        message: t('数据过期时间不能为空'),
        trigger: 'blur',
      },
      {
        validator: (value: number) => value >= formData.partition_time_interval,
        message: t('数据过期时间必须不小于分区间隔'),
        trigger: 'change',
      },
      {
        validator: (value: number) => value % formData.partition_time_interval === 0,
        message: t('数据过期时间是分区间隔的整数倍'),
        trigger: 'change',
      },
    ],
  }));

  const { loading: isCluserListLoading, data: clusterList } = useRequest(getTendbClusterList, {
    defaultParams: [
      {
        limit: -1,
      },
    ],
  });

  watch(
    () => props.data,
    () => {
      if (props.data) {
        formData.cluster_id = props.data.cluster_id;
        formData.dblikes = [props.data.dblike];
        formData.tblikes = [props.data.tblike];
        formData.partition_column = props.data.partition_columns;
        formData.partition_column_type = props.data.partition_column_type;
        formData.expire_time = props.data.expire_time;
        formData.partition_time_interval = props.data.partition_time_interval;
      } else {
        // 从编辑态进入创建态，初始化表单
        Object.assign(formData, initFormData());
      }
      isEditMode.value = Boolean(props.data && props.data.id);
    },
    {
      immediate: true,
    },
  );

  const handleCancel = () => {
    isShow.value = false;
  };

  const handleTblikeFocus = () => {
    isTblikePopShow.value = true;
  };
  const handleTblikeBlur = () => {
    isTblikePopShow.value = false;
  };

  const handleClusterChange = (value: number) => {
    formData.cluster_id = value;
  };

  const handleVerifyCancel = () => {
    warnConfirming.value = false;
  };

  const submitPartition = () => {
    if (props.data && props.data.id) {
      editPartition({
        id: props.data.id,
        ...formData,
      }).then(() => {
        emits('editSuccess');
        handleCancel();
      });
      return;
    }

    createParitition({
      ...formData,
    }).then((data) => {
      emits('createSuccess', data, formData.cluster_id);
      handleCancel();
    });
  };

  const handleVerifyConfirm = () => {
    showPopConfirm = false;
    warnConfirming.value = false;
    submitPartition();
  };

  const handleSubmit = () => {
    formRef.value.validate().then(() => {
      if (showPopConfirm) {
        warnConfirming.value = true;
        return;
      }
      submitPartition();
    });
  };
</script>
<style lang="less">
  .partition-operation-box {
    padding: 20px 40px;
  }
</style>
