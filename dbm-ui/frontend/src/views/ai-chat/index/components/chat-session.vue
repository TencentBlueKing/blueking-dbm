<template>
  <div
    v-bk-loading="{ loading: isDeleting }"
    class="chat-session-box"
    :class="{
      'is-active': modelValue === data.session_code,
    }">
    <div
      v-if="isEditing"
      class="session-rename-box">
      <input
        ref="renameInput"
        v-model="newSessionName"
        :readonly="isRenameSubmiting"
        :spellcheck="false"
        @blur="handleRenameSubmit"
        @keydown.enter="handleRenameSubmit" />
      <div
        v-if="isRenameSubmiting"
        class="rename-loading rotate-loading">
        <DbIcon
          svg
          type="loading" />
      </div>
    </div>
    <template v-else>
      <div
        class="session-info"
        @click="handleActive(data.session_code)">
        <div class="session-name">{{ data.session_name }}</div>
        <div class="session-content">{{ formatDateTime(data.updated_at) }}</div>
      </div>
      <div
        class="session-action-box"
        :class="{ 'is-active': isDeletePopconfirmShow }">
        <div
          class="session-action-item"
          @click="handleRename">
          <DbIcon type="edit" />
        </div>
        <DbPopconfirm
          :confirm-handler="() => handleDelete(data.session_code)"
          :content="t('删除对话将删除该会话的所有聊天记录，请谨慎操作。')"
          :title="t('确认删除对话？')"
          @toggle-show="handleToggleDeletePopconfirm">
          <div class="session-action-item">
            <DbIcon type="delete" />
          </div>
        </DbPopconfirm>
        <div
          class="session-select-checkbox ml-4"
          :class="{
            'is-selected': selected,
          }">
          <BkCheckbox
            :false-label="false"
            :model-value="selected"
            :true-label="trueLabel"
            @change="handleSelect" />
        </div>
      </div>
    </template>
  </div>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { deleteSession, getSession, updateSessionInfo } from '@services/source/ai';

  import { messageSuccess } from '@utils';

  interface Props {
    data: ServiceReturnType<typeof getSession>[number];
    selected: boolean;
  }

  interface Emits {
    (e: 'success'): void;
    (e: 'select', value: boolean): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>('modelValue');

  const formatDateTime = (dateTime: string) => {
    if (dayjs(dateTime).isAfter(dayjs().subtract(1, 'hour'))) {
      return dayjs(dateTime).fromNow();
    }
    if (dayjs(dateTime).isAfter(dayjs().subtract(1, 'day'))) {
      return `${t('今天')} ${dayjs(dateTime).format('HH:mm:ss')}`;
    }
    return dayjs(dateTime).format('YYYY年MM月DD日 HH:mm:ss');
  };

  const trueLabel = true;
  const { t } = useI18n();

  const renameInputRef = useTemplateRef<HTMLInputElement>('renameInput');
  const isEditing = ref(false);
  const newSessionName = ref<string>('');
  const isDeletePopconfirmShow = ref(false);

  const { loading: isDeleting, runAsync: runDeleteSession } = useRequest(deleteSession, {
    manual: true,
    onSuccess: () => {
      emits('success');
      messageSuccess(t('删除成功'));
    },
  });

  const { loading: isRenameSubmiting, runAsync: runUpdateSessionInfo } = useRequest(updateSessionInfo, {
    manual: true,
    onSuccess: () => {
      emits('success');
      isEditing.value = false;
      messageSuccess(t('更新成功'));
    },
  });
  const handleActive = (sessionCode: string) => {
    modelValue.value = sessionCode;
  };

  const handleToggleDeletePopconfirm = (value: boolean) => {
    isDeletePopconfirmShow.value = value;
  };

  const handleDelete = (sessionCode: string) => {
    return runDeleteSession({
      session_code: sessionCode,
    });
  };
  const handleRename = () => {
    isEditing.value = true;
    newSessionName.value = props.data.session_name;
    nextTick(() => {
      renameInputRef.value?.focus();
    });
  };

  const handleRenameSubmit = _.debounce(() => {
    if (
      !newSessionName.value ||
      newSessionName.value === props.data.session_name ||
      isRenameSubmiting.value ||
      !isEditing.value
    ) {
      isEditing.value = false;
      return;
    }
    return runUpdateSessionInfo({
      session_code: props.data.session_code,
      session_name: newSessionName.value,
    });
  }, 200);

  const handleSelect = (value: boolean) => {
    emits('select', value);
  };
</script>
<style lang="postcss">
  .chat-session-box {
    position: relative;
    display: flex;
    height: 48px;
    padding: 9px 16px 5px;
    font-size: 12px;
    background-color: #fff;
    border-radius: 2px;
    transition: all 0.3s ease;
    align-items: center;

    & ~ .chat-session-box {
      margin-top: 8px;
    }

    &.is-active {
      background: #e1ecff;

      .session-info {
        .session-name {
          color: #3a84ff;
        }
      }
    }

    &:hover {
      .session-action-box {
        .session-action-item,
        .session-select-checkbox {
          display: flex !important;
        }
      }
    }

    .session-info {
      overflow: hidden;
      flex: 1;
      cursor: pointer;

      .session-name,
      .session-content {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .session-name {
        font-weight: bold;
        color: #4d4f56;
      }

      .session-content {
        margin-top: 2px;
        line-height: 20px;
        color: #979ba5;
      }
    }

    .session-action-box {
      display: flex;
      align-items: center;
      justify-content: flex-end;

      &.is-active {
        .session-action-item,
        .session-select-checkbox {
          display: flex !important;
        }
      }

      .session-action-item {
        display: flex;
        display: none;
        padding: 0 4px;
        font-size: 14px;
        cursor: pointer;
        align-items: center;
        justify-content: center;

        &:hover {
          color: #3a84ff;
        }
      }

      .session-select-checkbox {
        display: none;

        &.is-selected {
          display: flex;
        }
      }
    }

    .session-rename-box {
      position: absolute;
      inset: 0;

      input {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        padding: 0 16px;
        background: #fff;
        border: 1px solid #3a84ff;
        border-radius: 2px;
        outline: none;
      }

      .rename-loading {
        position: absolute;
        top: 8px;
        right: 1px;
        display: flex;
        width: 32px;
        height: 32px;
        font-size: 16px;
        align-items: center;
        justify-content: center;
      }
    }
  }
</style>
