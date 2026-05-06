<template>
  <div class="batch-operation-main">
    <BkCheckbox
      v-model="isCheckAll"
      class="operation-checkbox"
      @change="handleChangeAll">
      {{ t('全选') }}
    </BkCheckbox>
    <div class="btn-operations">
      <BkPopConfirm
        v-if="status === 'RUNNING'"
        :confirm-config="{
          theme: 'danger',
        }"
        :confirm-text="t('批量失败')"
        :content="t('强制失败将立即终止这n个节点运行，统一标记为 “失败”', { n: data.length })"
        :popover-options="{
          disabled: isDisabled,
        }"
        :title="t('确认强制终止n个节点并置为失败？', { n: data.length })"
        trigger="click"
        width="280"
        @confirm="handleConfirmForceFail">
        <BkButton
          :disabled="isDisabled"
          :loading="isForceFailLoading"
          theme="danger">
          {{ t('批量失败') }}
        </BkButton>
      </BkPopConfirm>
      <template v-else-if="status === 'FAILED'">
        <template v-if="isSuperUserMode">
          <BkButton
            :disabled="isDisabled"
            :loading="forceRetryAndSkipLoading"
            theme="warning"
            @click="() => handleForceSkipOrRetry('forceRetry')">
            {{ t('强制重试') }}
          </BkButton>
          <BkButton
            :disabled="isDisabled"
            :loading="forceRetryAndSkipLoading"
            outline
            theme="warning"
            @click="() => handleForceSkipOrRetry('forceSkip')">
            {{ t('强制跳过') }}
          </BkButton>
        </template>
        <template v-else>
          <BkPopConfirm
            :confirm-text="t('批量重试')"
            :content="t('重试将重新执行这n个节点', { n: data.length })"
            :popover-options="{
              disabled: isDisabled,
            }"
            :title="t('确认重试n个失败节点？', { n: data.length })"
            trigger="click"
            width="280"
            @confirm="handleConfirmRetry">
            <BkButton
              :disabled="isDisabled"
              :loading="isRetryLoading"
              theme="primary">
              {{ t('批量重试') }}
            </BkButton>
          </BkPopConfirm>
          <BkPopConfirm
            :confirm-text="t('批量跳过')"
            :content="
              t('跳过将忽略这n个节点的失败状态，直接执行后续节点，当前节点将被标记为“执行成功（失败手动跳过）”', {
                n: data.length,
              })
            "
            :popover-options="{
              disabled: isDisabled,
            }"
            :title="t('确认跳过n个失败节点？', { n: data.length })"
            trigger="click"
            width="280"
            @confirm="handleConfirmSkip">
            <BkButton
              :disabled="isDisabled"
              :loading="isSkipLoading"
              outline
              theme="primary">
              {{ t('批量跳过') }}
            </BkButton>
          </BkPopConfirm>
        </template>
      </template>
      <template v-else>
        <BkPopConfirm
          :confirm-text="t('批量继续')"
          :content="t('继续后将立即完成这n个节点，并执行后续节点', { n: data.length })"
          :popover-options="{
            disabled: isDisabled,
          }"
          :title="t('确认继续执行n个待继续节点？', { n: data.length })"
          trigger="click"
          width="280"
          @confirm="handleConfirmTodo">
          <BkButton
            :disabled="isDisabled"
            :loading="isTodoLoading"
            theme="primary">
            {{ t('批量继续') }}
          </BkButton>
        </BkPopConfirm>
        <BkPopConfirm
          :confirm-config="{
            theme: 'danger',
          }"
          :confirm-text="t('批量失败')"
          :content="t('强制失败将立即终止这n个节点运行，统一标记为 “失败”', { n: data.length })"
          :popover-options="{
            disabled: isDisabled,
          }"
          :title="t('确认强制终止n个节点并置为失败？', { n: data.length })"
          trigger="click"
          width="280"
          @confirm="handleConfirmForceFail">
          <BkButton
            :disabled="isDisabled"
            :loading="isForceFailLoading"
            theme="danger">
            {{ t('批量失败') }}
          </BkButton>
        </BkPopConfirm>
      </template>
      <BkButton
        v-if="data.length"
        :disabled="isDisabled"
        @click="handleClickCancel">
        {{ t('取消') }}
      </BkButton>
    </div>
  </div>
</template>
<script setup lang="tsx">
  import BkAlert from 'bkui-vue/lib/alert';
  import BkForm, { BkFormItem } from 'bkui-vue/lib/form';
  import InfoBox from 'bkui-vue/lib/info-box';
  import BkInput from 'bkui-vue/lib/input';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { batchForceFailTaskflowNode, batchRetryNodes, batchSkipTaskflowNode } from '@services/source/taskflow';
  import { batchProcessTodo } from '@services/source/ticketFlow';

  import { messageSuccess } from '@utils';

  import { type TreeNode } from '../../flow-canvas/utils';

  interface Props {
    data: TreeNode[];
    rootId: string;
    status: string;
  }

  interface Emits {
    (e: 'cancel'): void;
    (e: 'checkAll', isCheck: boolean): void;
    (e: 'refresh'): void;
  }

  interface Exposes {
    setCheckAll(isCheck: boolean): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const isSuperUserMode = defineModel<boolean>('isSuperUserMode', { required: true });

  const { t } = useI18n();

  const formRef = ref<InstanceType<typeof BkForm>>();
  const isCheckAll = ref(false);
  const forceRetryAndSkipLoading = ref(false);

  const formData = reactive({
    remark: '',
  });

  const isDisabled = computed(() => !props.data.length);

  const handleSuccess = () => {
    isCheckAll.value = false;
    messageSuccess(t('操作成功'));
    emits('refresh');
  };

  const { loading: isTodoLoading, run: runBatchProcessTodo } = useRequest(batchProcessTodo, {
    manual: true,
    onSuccess() {
      handleSuccess();
    },
  });

  const { loading: isRetryLoading, run: runBatchRetryNodes } = useRequest(batchRetryNodes, {
    manual: true,
    onSuccess() {
      handleSuccess();
    },
  });

  const { loading: isSkipLoading, run: runBatchSkipTaskflowNode } = useRequest(batchSkipTaskflowNode, {
    manual: true,
    onSuccess() {
      handleSuccess();
    },
  });

  const { loading: isForceFailLoading, run: runBatchForceFailTaskflowNode } = useRequest(batchForceFailTaskflowNode, {
    manual: true,
    onSuccess() {
      handleSuccess();
    },
  });

  const handleConfirmForceFail = () => {
    runBatchForceFailTaskflowNode({
      nodes: props.data.map((item) => item.id),
      root_id: props.rootId,
    });
  };

  const handleConfirmTodo = () => {
    runBatchProcessTodo({
      action: 'APPROVE',
      operations: props.data.map((item) => ({
        params: {},
        todo_id: item.todoId,
      })),
    });
  };

  const handleConfirmSkip = () => {
    runBatchSkipTaskflowNode({
      nodes: props.data.map((item) => item.id),
      root_id: props.rootId,
    });
  };

  const handleConfirmRetry = () => {
    runBatchRetryNodes({
      nodes: props.data.map((item) => item.id),
      root_id: props.rootId,
    });
  };

  const handleForceSkipOrRetry = (type: 'forceSkip' | 'forceRetry') => {
    const length = props.data.length;

    const typeInfo = {
      forceRetry: {
        api: batchRetryNodes,
        confirmText: t('确认强制重试'),
        subtitle: t('强制重试将重新执行当前失败节点，执行成功后继续执行后续节点'),
        title: t('确认批量强制重试 n 个节点？', { n: length }),
      },
      forceSkip: {
        api: batchSkipTaskflowNode,
        confirmText: t('确认强制跳过'),
        subtitle: t('强制跳过将忽略当前节点的失败状态，直接执行后续节点。当前节点将标记为 失败手动跳过'),
        title: t('确认批量强制跳过 n 个节点？', { n: length }),
      },
    };

    InfoBox({
      cancelText: t('取消'),
      confirmButtonTheme: 'danger',
      confirmText: typeInfo[type].confirmText,
      content: () => (
        <div class='mission-search-tree-retry-and-skip-info'>
          <BkAlert
            theme='warning'
            title={t('此操作将绕过系统预设的流程控制，请确认已知晓风险')}
          />
          <div class='info-subtitle mt-12'>
            <div>{typeInfo[type].subtitle}</div>
          </div>
          <div class='list-box mt-16'>
            <div class='list-title'>{t('已选择以下 n 个节点', { n: length })}</div>
            <div class='list-content'>
              {props.data.map((item) => (
                <div
                  key={item.id}
                  class='list-item'>
                  {item.name}
                </div>
              ))}
            </div>
          </div>
          <BkForm
            ref={formRef}
            class='mt-20'
            form-type='vertical'
            model={formData}>
            <BkFormItem
              label={t('操作原因')}
              property='remark'
              required>
              <BkInput
                v-model={formData.remark}
                class='mt-6'
                placeholder={t('请输入操作原因')}
                type='textarea'
              />
            </BkFormItem>
          </BkForm>
        </div>
      ),
      infoType: 'warning',
      onConfirm: async function () {
        forceRetryAndSkipLoading.value = true;
        try {
          await formRef.value!.validate();
          typeInfo[type]
            .api({
              is_force: true,
              nodes: props.data.map((item) => item.id),
              remark: formData.remark,
              root_id: props.rootId,
            })
            .then(() => {
              Object.assign(formData, { remark: '' });
              // isSuperUserMode.value = false;
              handleSuccess();
              return true;
            });
        } finally {
          forceRetryAndSkipLoading.value = false;
        }
      },
      theme: 'danger',
      title: typeInfo[type].title,
    });
  };

  const handleChangeAll = (isCheck: boolean) => {
    emits('checkAll', isCheck);
  };

  const handleClickCancel = () => {
    emits('cancel');
    isCheckAll.value = false;
  };

  defineExpose<Exposes>({
    setCheckAll(isCheck: boolean) {
      isCheckAll.value = isCheck;
    },
  });
</script>
<style lang="less">
  .batch-operation-main {
    display: flex;
    width: calc(100% + 24px);
    height: 48px;
    min-height: 48px;
    padding: 0 12px;
    margin-top: 6px;
    margin-left: -12px;
    border: 1px solid #dcdee5;
    align-items: center;
    justify-content: space-between;

    .operation-checkbox {
      min-width: 48px;
    }

    .btn-operations {
      display: flex;
      gap: 8px;
    }
  }

  .mission-search-tree-retry-and-skip-info {
    text-align: left;

    .info-subtitle {
      padding: 12px 16px;
      line-height: 22px;
      background: #f5f6fa;
      border-radius: 2px;
    }

    .list-box {
      font-size: 12px;
      border: 1px solid #eaebf0;
      border-radius: 2px;

      .list-title {
        height: 32px;
        padding: 0 16px;
        line-height: 32px;
        color: #313238;
        background-color: #eaebf0;
      }

      .list-content {
        max-height: 200px;
        overflow: auto;

        .list-item {
          height: 32px;
          padding: 0 16px;
          line-height: 32px;

          &:nth-child(even) {
            background-color: #fafbfd;
          }
        }
      }
    }
  }
</style>
