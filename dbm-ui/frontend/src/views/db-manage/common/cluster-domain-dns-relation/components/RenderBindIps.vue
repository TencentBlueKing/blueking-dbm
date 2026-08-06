<template>
  <div
    v-if="!activeInput"
    class="entry-config-display">
    <p
      v-for="(row, index) in localIps"
      :key="row"
      class="entry-config-display-item">
      {{ row }}
      <AuthButton
        v-if="index === 0"
        :action-id="manageActionId"
        :permission="clusterData.permission[manageActionId]"
        :resource="clusterData.id"
        text
        theme="primary"
        @click="handleActiveInput">
        <DbIcon type="edit" />
      </AuthButton>
    </p>
  </div>
  <div
    v-else
    class="entry-config-multi"
    :class="{ 'is-error': isError }">
    <BkInput
      ref="inputRef"
      v-model="localValue"
      placeholder=" "
      :rows="localIps.length"
      style="resize: none"
      type="textarea"
      @blur="handleBlur"
      @input="handleInput" />
    <div
      v-show="isError"
      class="error-box">
      <div
        v-for="(item, index) in errorList"
        :key="index"
        class="tip-box">
        <DbIcon
          v-if="!item.isChecked"
          v-bk-tooltips="item.tip"
          class="error-icon"
          type="exclamation-fill" />
      </div>
    </div>
  </div>
</template>
<script lang="ts">
  import type { ClusterEntryInfo } from '../Index.vue';

  interface Props {
    clusterData: {
      db_type: string;
      id: number;
      permission: Record<string, boolean>;
    };
    data: ClusterEntryInfo;
  }

  type Emits = (e: 'success') => void;

  interface ErrorItem {
    isChecked: boolean;
    tip: string;
  }
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { updateClusterEntryConfig } from '@services/source/clusterEntry';

  import { DBTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import { messageSuccess } from '@utils';

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  /** 数据库类型对应的运维管理权限 actionId（废弃 access_entry_edit，整合进 dbType_manage） */
  const dnsManageActionIdMap: Record<DBTypes, string> = {
    [DBTypes.DORIS]: 'doris_manage',
    [DBTypes.ES]: 'es_manage',
    [DBTypes.HDFS]: 'hdfs_manage',
    [DBTypes.INFLUXDB]: 'influxdb_manage',
    [DBTypes.KAFKA]: 'kafka_manage',
    [DBTypes.MONGODB]: 'mongodb_manage',
    [DBTypes.MYSQL]: 'mysql_manage',
    [DBTypes.ORACLE]: 'oracle_manage',
    [DBTypes.PULSAR]: 'pulsar_manage',
    [DBTypes.REDIS]: 'redis_manage',
    [DBTypes.RIAK]: 'riak_manage',
    [DBTypes.SQLSERVER]: 'sqlserver_manage',
    [DBTypes.TENDBCLUSTER]: 'tendbcluster_manage',
  };

  /** DNS 手动配置编辑的运维管理权限 actionId */
  const manageActionId = computed(() => dnsManageActionIdMap[props.clusterData.db_type as DBTypes]);

  const inputRef = ref();
  const activeInput = ref(false);
  const isError = ref(false);
  const errorList = ref<ErrorItem[]>([]);
  const localValue = ref('');
  const localIps = ref<string[]>([]);

  const { run: runUpdateClusterEntryConfig } = useRequest(updateClusterEntryConfig, {
    manual: true,
    onError: () => {
      localValue.value = props.data.ips;
      localIps.value = props.data.ips.split('\n');
    },
    onSuccess: () => {
      messageSuccess(t('修改成功'));
      emits('success');
    },
  });

  watch(
    () => props.data,
    () => {
      localValue.value = props.data.ips;
      localIps.value = props.data.ips.split('\n');
    },
    {
      immediate: true,
    },
  );

  const handleActiveInput = () => {
    activeInput.value = true;
    nextTick(() => {
      inputRef.value.focus();
    });
  };

  const executeUpdate = () => {
    const params = {
      cluster_entry_details: [
        {
          cluster_entry_type: props.data.cluster_entry_type,
          domain_name: props.data.entry,
          target_instances: localValue.value.split('\n').map((row) => `${row}#${props.data.port}`),
        },
      ],
      cluster_id: props.clusterData.id,
    };
    runUpdateClusterEntryConfig(params);
  };

  const handleBlur = () => {
    if (localValue.value === props.data.ips) {
      activeInput.value = false;
      return;
    }
    const inputArr = localValue.value.split('\n');
    const resultArr: ErrorItem[] = [];
    inputArr.forEach((item) => {
      const isChecked = ipv4.test(item);
      if (!isChecked) {
        isError.value = true;
      }
      resultArr.push({
        isChecked,
        tip: !isChecked && item === '' ? t('IP 不能为空') : t('IP 输入有误'),
      });
    });
    errorList.value = resultArr;
    if (!isError.value) {
      activeInput.value = false;
      executeUpdate();
    }
  };

  const handleInput = () => {
    isError.value = false;
  };
</script>
<style lang="less" scoped>
  .entry-config-display {
    padding: 13px 19px;

    .entry-config-display-item {
      line-height: 18px;
    }

    .db-icon-edit {
      cursor: pointer;
    }
  }

  .entry-config-multi {
    position: relative;

    .bk-textarea {
      border-color: transparent;
      border-radius: 0;
    }

    .is-focused {
      border-color: #3a84ff;
    }

    :deep(textarea) {
      min-height: 42px !important;
      padding: 12px 18px;
      border-radius: 0;
    }

    .error-box {
      position: absolute;
      top: 0;
      right: 0;
      width: 25px;
      height: 100%;
      padding-top: 12px;

      .tip-box {
        display: flex;
        height: 18px;
        padding-top: 3.5px;
        justify-content: center;

        .error-icon {
          font-size: 14px;
          color: #ea3636;
        }
      }
    }
  }

  .is-error {
    :deep(textarea) {
      background-color: #fff0f1;
    }
  }
</style>
