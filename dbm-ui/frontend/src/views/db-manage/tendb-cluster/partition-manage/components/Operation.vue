<template>
  <BkSideslider
    v-model:is-show="isShow"
    render-directive="if"
    :title="data ? (data.id ? t('编辑分区策略') : t('克隆分区策略')) : t('新建分区策略')"
    :width="1000">
    <div class="partition-operation-box">
      <BkAlert
        class="mb-16"
        closable
        theme="info">
        <div>{{ t('表中包含数据，建议在低峰期执行分区；') }}</div>
        <div>{{ t('表中行数大于1千万或者表数据量大于300GB，不允许执行分区；') }}</div>
        <div>{{ t('int或bigint类型，格式要求为：20060102') }}</div>
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
            :disabled="isEditMode"
            filterable
            :loading="isCluserListLoading"
            :model-value="formData.cluster_id || undefined"
            @change="handleClusterChange">
            <BkOption
              v-for="item in clusterList"
              :id="item.id"
              :key="item.id"
              :name="item.immute_domain" />
          </BkSelect>
        </DbFormItem>
        <DbFormItem
          :label="t('目标 DB')"
          property="dblikes"
          required>
          <DbTagInput
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
            <DbTagInput
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
          :label="t('分区字段')"
          property="partition_column"
          required>
          <BkInput
            v-model="formData.partition_column"
            :placeholder="
              t('请输入分区字段，分区字段的字段类型必须是 int、bigint、date、datetime、timestamp 其中一个')
            " />
        </DbFormItem>
        <DbFormItem
          :label="t('字段类型')"
          property="partition_column_type"
          required>
          <BkSelect
            v-model="formData.partition_column_type"
            :disabled="partitionColumnTypeDisabled">
            <BkOption
              v-for="item in columnTypeSelectList"
              :id="item.id"
              :key="item.id"
              :name="item.name" />
          </BkSelect>
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
      <BkAlert
        v-if="isEditMode"
        class="mt-24"
        theme="warning">
        <div style="font-weight: 600">{{ t('操作说明：') }}</div>
        <div class="mt-20">
          <div style="font-weight: 600">
            {{ t('保存并执行')
            }}<BkTag
              class="ml-8"
              theme="success">
              {{ t('推荐') }}
            </BkTag>
          </div>
          <ul>
            <li>{{ t('- 适用：调整分区间隔，过期时间') }}</li>
            <li>{{ t('- 影响：仅对新分区生效，历史分区不变') }}</li>
            <li>{{ t('- 风险：低，无业务影响') }}</li>
          </ul>
        </div>
        <div class="mt-20 mb-8">
          <div style="font-weight: 600">
            {{ t('保存并重新初始化')
            }}<BkTag
              class="ml-8"
              theme="danger">
              {{ t('谨慎') }}
            </BkTag>
          </div>
          <ul>
            <li>{{ t('- 适用：修改分区字段或需历史分区立即应用新的分区策略') }}</li>
            <li>{{ t('- 影响：重构表结构，历史分区同步调整') }}</li>
            <li>{{ t('- 风险：高，可能影响查询性能，建议联系DBA评估') }}</li>
          </ul>
        </div>
      </BkAlert>
    </div>
    <template #footer>
      <template v-if="isEditMode">
        <BkPopConfirm
          :is-show="warnConfirming"
          :title="t('确定保存并执行？')"
          trigger="manual"
          width="350"
          @cancel="handleVerifyCancel"
          @confirm="handleVerifyConfirm">
          <BkButton
            :loading="confirmLoading"
            style="width: 100px"
            theme="primary"
            @click="handleSubmit">
            {{ t('保存并执行') }}
          </BkButton>
        </BkPopConfirm>
        <BkPopConfirm
          :confirm-config="{ theme: 'danger' }"
          :confirm-text="t('确认初始化')"
          :content="t('重新初始化会立刻对当前表结构进行变更，请谨慎操作')"
          :is-show="warnResetConfirming"
          :title="t('确认重新初始化？')"
          trigger="manual"
          width="350"
          @cancel="handleResetCancel"
          @confirm="handleResetConfirm">
          <BkButton
            class="ml-8"
            :disabled="isDisabledResetButton"
            :loading="resetLoading"
            @click="handleResetSubmit">
            {{ t('保存并重新初始化') }}
          </BkButton>
        </BkPopConfirm>
      </template>
      <template v-else>
        <BkPopConfirm
          :is-show="warnConfirming"
          :title="t('确定提交？')"
          trigger="manual"
          width="350"
          @cancel="handleVerifyCancel"
          @confirm="handleVerifyConfirm">
          <BkButton
            :loading="confirmLoading"
            theme="primary"
            @click="handleSubmit">
            {{ t('提交') }}
          </BkButton>
        </BkPopConfirm>
      </template>
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
  import { queryAllTypeCluster } from '@services/source/dbbase';
  import { create as createPartition, queryFieldType, saveAndExecute } from '@services/source/partitionManage';

  import { useTicketMessage } from '@hooks';

  import { ClusterTypes, dbSysExclude } from '@common/const';
  import { dbRegex } from '@common/regex';

  interface Props {
    data?: PartitionModel;
  }

  interface Emits {
    (e: 'editSuccess'): void;
    (e: 'createSuccess'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const initFormData = () => ({
    cluster_id: undefined as unknown as number,
    dblikes: [] as string[],
    expire_time: 30,
    partition_column: '',
    partition_column_type: '',
    partition_time_interval: undefined as unknown as number,
    tblikes: [] as string[],
  });

  let showPopConfirm = false;
  let partionColumnVerifyErrorText = '';
  let motifyBefore = {
    partition_column: '',
    partition_time_interval: 0,
  };

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const formRef = ref();
  const isEditMode = ref(false);
  const isTblikePopShow = ref(false);
  const confirmLoading = ref(false);
  const warnConfirming = ref(false);
  const warnResetConfirming = ref(false);
  const resetLoading = ref(false);
  const partitionColumnTypeDisabled = ref(true);

  const formData = reactive(initFormData());

  const rules = computed(() => ({
    dblikes: [
      {
        message: t('目标 DB 不能为空'),
        required: true,
        trigger: 'blur',
        validator: (value: string[]) => value.length > 0,
      },
      {
        message: t('目标 DB 不能为*'),
        trigger: 'blur',
        validator: (value: string[]) => !value.some((item) => item === '*'),
      },
      {
        message: t('只允许数字、大小写字母开头和结尾，或%结尾'),
        trigger: 'change',
        validator: (value: string[]) => value.every((item) => dbRegex.test(item)),
      },
      {
        message: t('不能是系统库'),
        trigger: 'change',
        validator: (value: string[]) => value.every((item) => !dbSysExclude.includes(item)),
      },
    ],
    expire_time: [
      {
        message: t('数据过期时间不能为空'),
        required: true,
        trigger: 'blur',
        validator: (value: number) => Boolean(value),
      },
      {
        message: t('数据过期时间必须不小于分区间隔'),
        trigger: 'change',
        validator: (value: number) => value >= formData.partition_time_interval,
      },
      {
        message: t('数据过期时间是分区间隔的整数倍'),
        trigger: 'change',
        validator: (value: number) => value % formData.partition_time_interval === 0,
      },
    ],
    partition_column: [
      {
        message: t('请输入完整信息验证分区字段'),
        trigger: 'blur',
        validator: () => {
          if (!formData.cluster_id || formData.dblikes.length < 1 || formData.tblikes.length < 1) {
            return false;
          }
          return true;
        },
      },
      {
        message: () => partionColumnVerifyErrorText,
        trigger: 'blur',
        validator: (value: string) =>
          queryFieldType({
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            cluster_id: formData.cluster_id,
            dblikes: formData.dblikes,
            partition_column: value,
            tblikes: formData.tblikes,
          })
            .then((result) => {
              if (result) {
                showPopConfirm = true;
                partitionColumnTypeDisabled.value = true;
                formData.partition_column_type = result;
              } else {
                showPopConfirm = false;
                partitionColumnTypeDisabled.value = false;
                formData.partition_column_type = '';
              }
              return true;
            })
            .catch((err) => {
              partionColumnVerifyErrorText = err.message;
              return false;
            }),
      },
    ],
    tblikes: [
      {
        message: t('目标表不能为空'),
        required: true,
        trigger: 'blur',
        validator: (value: string[]) => value.length > 0,
      },
      {
        message: t('不支持通配符 *, %, ?'),
        trigger: 'blur',
        validator: (value: string[]) => value.every((item) => !/[*%?]/.test(item)),
      },
    ],
  }));

  const isDisabledResetButton = computed(() => {
    return (
      formData.partition_column === motifyBefore.partition_column &&
      formData.partition_time_interval === motifyBefore.partition_time_interval
    );
  });

  const columnTypeSelectList = [
    {
      id: 'int',
      name: t('整型(int)'),
    },
    {
      id: 'bigint',
      name: t('整型(bigint)'),
    },
    {
      id: 'date',
      name: t('日期类型(date)'),
    },
    {
      id: 'datetime',
      name: t('日期时间类型(datetime)'),
    },
    {
      id: 'timestamp',
      name: t('时间戳类型(timestamp)'),
    },
  ];

  const { data: clusterList, loading: isCluserListLoading } = useRequest(queryAllTypeCluster, {
    defaultParams: [
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        cluster_types: ClusterTypes.TENDBCLUSTER,
        limit: -1,
        offset: 0,
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
        formData.partition_column = props.data.partition_column;
        formData.partition_column_type = props.data.partition_column_type;
        formData.expire_time = props.data.expire_time;
        formData.partition_time_interval = props.data.partition_time_interval;
        motifyBefore = {
          partition_column: props.data.partition_column,
          partition_time_interval: props.data.partition_time_interval,
        };
      } else {
        // 从编辑态进入创建态，初始化表单
        Object.assign(formData, initFormData());
      }
      isEditMode.value = Boolean(props.data?.id);
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

  const submitPartition = async () => {
    confirmLoading.value = true;

    const apiFn = isEditMode.value ? saveAndExecute : createPartition;

    try {
      const data = await apiFn({ ...formData });

      ticketMessage(data[0].id);
      handleCancel();

      if (isEditMode.value) {
        emits('editSuccess');
      } else {
        emits('createSuccess');
      }
    } finally {
      confirmLoading.value = false;
    }
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

  const handleResetConfirm = () => {
    warnResetConfirming.value = false;
    resetLoading.value = true;
    saveAndExecute({
      ...formData,
      force: true,
    })
      .then((data) => {
        ticketMessage(data[0].id);
        handleCancel();
        emits('editSuccess');
      })
      .finally(() => {
        resetLoading.value = false;
      });
  };

  const handleResetCancel = () => {
    warnResetConfirming.value = false;
  };

  const handleResetSubmit = () => {
    formRef.value.validate().then(() => {
      warnResetConfirming.value = true;
    });
  };
</script>
<style lang="less">
  .partition-operation-box {
    padding: 20px 24px;
  }
</style>
