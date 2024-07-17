<template>
  <BkPopover
    v-model:is-show="stateShow"
    :boundary="body"
    ext-cls="redis-host-batch-edit"
    theme="light"
    trigger="manual"
    :width="320">
    <DbIcon
      class="redis-host-batch-edit-trigger"
      type="bulk-edit"
      @click="() => (stateShow = true)" />
    <template #content>
      <div class="batch-edit-content">
        <p class="batch-edit-header">
          {{ t('批量录入待部署主库主机') }}
        </p>
        <div
          class="batch-edit-domain"
          :style="{ '--offset': `${stateOffsetWidth}px` }">
          <BkInput
            v-model="stateValue"
            class="batch-edit-domain-input"
            :class="[validateErrorText ? '' : 'batch-edit-domain-input-bottom']"
            :placeholder="t('批量录入，多个对象换行分隔')"
            :rows="textareaRows"
            type="textarea" />
          <p
            v-if="validateErrorText"
            class="batch-edit-domain-error">
            {{ validateErrorText }}
          </p>
        </div>
        <div class="batch-edit-footer">
          <BkButton
            class="mr-8"
            size="small"
            theme="primary"
            @click="handleConfirm">
            {{ t('确定') }}
          </BkButton>
          <BkButton
            size="small"
            @click="handleCancel">
            {{ t('取消') }}
          </BkButton>
        </div>
      </div>
    </template>
  </BkPopover>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getRedisMachineList } from '@services/source/redis';

  import { ClusterTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  interface Props {
    cloudId: string | number;
    cityName: string;
  }

  interface Emits {
    (e: 'change', value: string[]): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const stateShow = ref(false);
  const stateValue = ref('');
  const stateOffsetWidth = ref(0);
  const validateErrorText = ref('');

  const { body } = document;

  const textareaRows = computed(() => {
    const rows = stateValue.value.split('\n').length;
    if (rows <= 5) {
      return 5;
    }
    return rows > 10 ? 10 : rows;
  });

  watch(stateShow, (show) => {
    if (!show) {
      stateValue.value = '';
    }
  });

  watch(stateValue, (value) => {
    if (value) {
      handleValidate();
    } else {
      validateErrorText.value = '';
    }
  });

  /**
   * validate batch edit value
   */
  const handleValidate = async () => {
    const inputHostList = stateValue.value.split('\n');
    // 格式
    if (!inputHostList.every((key) => ipv4.test(key))) {
      validateErrorText.value = t('主机格式不正确');
      return;
    }
    // 校验名称是否重复
    // if (inputHostList.length !== _.uniq(inputHostList).length) {
    //   validateErrorText.value = t('输入主机重复');
    //   return;
    // }
    // 存在性
    const data = await getRedisMachineList({
      ip: inputHostList.join(','),
      instance_role: 'redis_master',
      bk_cloud_id: props.cloudId as number,
      region: props.cityName,
      cluster_type: ClusterTypes.REDIS_INSTANCE,
    });
    const inputHostMap = inputHostList.reduce(
      (prevMap, hostItem) => ({
        ...prevMap,
        [hostItem]: false,
      }),
      {} as Record<string, boolean>,
    );
    data.results.forEach((machineItem) => {
      if (machineItem.ip in inputHostMap) {
        inputHostMap[machineItem.ip] = true;
      }
    });
    const errorHostList = Object.entries(inputHostMap).reduce((prevList, [key, value]) => {
      if (value) {
        return prevList;
      }
      return [...prevList, key];
    }, [] as string[]);
    if (errorHostList.length) {
      validateErrorText.value = t('目标从库主机 n 不存在', { n: errorHostList.join('，') });
      return;
    }

    validateErrorText.value = '';
  };

  /**
   * confirm batch edit
   */
  const handleConfirm = () => {
    if (validateErrorText.value) {
      return;
    }

    const inputHostList = stateValue.value.split('\n');
    emits('change', inputHostList);
    handleCancel();
  };

  /**
   * close popover
   */
  const handleCancel = () => {
    stateShow.value = false;
  };
</script>

<style lang="less" scoped>
  .redis-host-batch-edit {
    .batch-edit-content {
      padding: 9px 2px;
    }

    .batch-edit-header {
      font-size: @font-size-large;
      color: @title-color;

      span {
        font-size: @font-size-mini;
        color: @default-color;
      }
    }

    .batch-edit-domain {
      position: relative;
      color: @default-color;

      .batch-edit-domain-name {
        word-wrap: break-word;
      }

      .batch-edit-domain-underline {
        position: relative;
        display: inline-block;
        width: 54px;
        height: 1px;
        margin: 0 2px;
        color: @default-color;
        background-color: #c4c6cc;

        &::after {
          position: absolute;
          top: -4px;
          left: 50%;
          z-index: 1;
          width: 6px;
          height: 6px;
          background-color: white;
          border: 1px solid transparent;
          border-bottom-color: #c4c6cc;
          border-left-color: #c4c6cc;
          content: '';
          transform: translateX(-50%) rotate(-45deg);
        }
      }

      .batch-edit-domain-input {
        position: relative;
        margin: 12px 0 4px;
        transition: none;

        &::before {
          position: absolute;
          top: -4px;
          left: var(--offset);
          width: 6px;
          height: 6px;
          background-color: @white-color;
          border: 1px solid transparent;
          border-top-color: @border-light-gray;
          border-left-color: @border-light-gray;
          content: '';
          transform: rotateZ(45deg);
        }

        .batch-edit.is-focused {
          &::before {
            border-top-color: @border-primary;
            border-left-color: @border-primary;
          }
        }
      }

      .batch-edit-domain-input-bottom {
        margin-bottom: 16px;
      }

      .batch-edit-domain-error {
        // position: absolute;
        // bottom: -4px;
        // left: 0;
        font-size: @font-size-mini;
        color: @danger-color;
        margin-bottom: 16px;
      }
    }

    .batch-edit-footer {
      text-align: right;

      .bk-button {
        min-width: 60px;
        font-size: 12px;
      }
    }
  }
</style>

<style lang="less">
  .redis-host-batch-edit-trigger {
    margin-left: 4px;
    color: @primary-color;
    cursor: pointer;
  }
</style>
