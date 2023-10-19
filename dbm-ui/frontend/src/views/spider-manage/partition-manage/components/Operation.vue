<template>
  <div class="partition-operation-box">
    <BkAlert
      class="mb-16"
      theme="info">
      <div>{{ t('如果已经是分区表，会维护新分区，理论上不影响业务') }}</div>
      <div>{{ t('如果不是分区表，会转换成分区表，存在表数据迁移到新表，理论上不影响业务') }}</div>
      <div>{{ t('如果大于 500G 的表，无法执行分区') }}</div>
      <div>{{ t('建议在低峰期执行') }}</div>
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
            :name="item.cluster_name" />
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
        <BkSelect
          v-model="formData.partition_column_type"
          :disabled="isEditMode">
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
          :disabled="isEditMode"
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
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type PartitionModel from '@services/model/partition/partition';
  import {
    create as createParitition,
    edit as editPartition,
    verifyPartitionField,
  } from '@services/partitionManage';
  import { getList } from '@services/spider';

  import { dbSysExclude } from '@common/const';
  import { dbRegex } from '@common/regex';

  interface Props {
    data?: PartitionModel
  }
  interface Emits{
    (e: 'success', params: ServiceReturnType<typeof createParitition>): void
  }
  interface Expose {
    submit: () => Promise<any>
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const formRef = ref();
  const isEditMode = ref(false);
  const isTblikePopShow = ref(false);
  const formData = reactive({
    cluster_id: undefined as unknown as number,
    dblikes: [] as string[],
    tblikes: [] as string[],
    partition_column: '',
    partition_column_type: 'int',
    expire_time: 30,
    partition_time_interval: undefined as unknown as number,
  });

  const rules = {
    dblikes: [
      {
        required: true,
        validator: (value: string[]) => value.length > 0,
        message: t('目标 DB 不能为空'),
        trigger: 'blur',
      },
      {
        validator: (value: string[]) => !value.some(item => item === '*'),
        message: t('目标 DB 不能为*'),
        trigger: 'blur',
      },
      {
        validator: (value: string[]) => value.every(item => dbRegex.test(item)),
        message: t('只允许数字、大小写字母开头和结尾，或%结尾'),
        trigger: 'change',
      },
      {
        validator: (value: string[]) => value.every(item => !dbSysExclude.includes(item)),
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
        validator: (value: string[]) => value.every(item => !/[*%?]/.test(item)),
        message: t('不支持通配符 *, %, ?'),
        trigger: 'blur',
      },
    ],
    partition_column: [
      {
        validator: () => {
          if (!formData.cluster_id
            || formData.dblikes.length < 1
            || formData.tblikes.length < 1
            || !formData.partition_column_type) {
            return false;
          }
          return true;
        },
        message: t('请输入完整信息验证分区字段'),
        trigger: 'blur',
      },
      {
        validator: (value: string) => verifyPartitionField({
          cluster_id: formData.cluster_id,
          dblikes: formData.dblikes,
          tblikes: formData.tblikes,
          partition_column: value,
          partition_column_type: formData.partition_column_type,
        }),
        message: t('分区字段验证失败'),
        trigger: 'blur',
      },
    ],
    expire_time: [
      {
        required: true,
        validator: (value: number) =>  Boolean(value),
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
  };

  const {
    loading: isCluserListLoading,
    data: clusterList,
  } = useRequest(getList, {
    defaultParams: [{
      limit: -1,
    }],
  });

  watch(() => props.data, () => {
    if (props.data) {
      formData.cluster_id = props.data.cluster_id;
      formData.dblikes = [props.data.dblike];
      formData.tblikes = [props.data.tblike];
      formData.partition_column = props.data.partition_columns;
      formData.partition_column_type = props.data.partition_column_type;
      formData.expire_time = props.data.expire_time;
      formData.partition_time_interval = props.data.partition_time_interval;
    }
    isEditMode.value = Boolean(props.data && props.data.id);
  }, {
    immediate: true,
  });

  const handleTblikeFocus = () => {
    isTblikePopShow.value = true;
  };
  const handleTblikeBlur = () => {
    isTblikePopShow.value = false;
  };

  const handleClusterChange = (value: number) => {
    formData.cluster_id = value;
  };

  defineExpose<Expose>({
    submit() {
      return formRef.value.validate()
        .then(() => {
          if (props.data && props.data.id) {
            return editPartition({
              id: props.data.id,
              ...formData,
            }).then(data => emits('success', data));
          }

          return createParitition({
            ...formData,
          }).then(data => emits('success', data));
        });
    },
  });
</script>
<style lang="less">
  .partition-operation-box {
    padding: 20px 40px;
  }
</style>
