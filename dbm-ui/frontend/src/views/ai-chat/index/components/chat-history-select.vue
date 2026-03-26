<template>
  <BkDropdown
    class="ml-8"
    :popover-options="{
      clickContentAutoHide: true,
    }"
    trigger="click"
    @hide="handleHide"
    @show="handleShow">
    <BkButton :loading="isLoading">
      <DbIcon
        class="mr-4"
        type="history" />
      {{ t('会话历史') }}
      <DbIcon
        class="chat-history-arrow"
        :class="{ 'is-flip': isDropdownShow }"
        type="up-big" />
    </BkButton>
    <template #content>
      <BkDropdownMenu class="chat-history-dropdown-menu">
        <ScrollFaker class="chat-history-scroll-area">
          <template v-if="sessionList.length > 0">
            <BkDropdownItem
              v-for="item in sessionList"
              :key="item.sessionCode"
              class="chat-history-item"
              :class="{ 'is-active': item.sessionCode === activeSessionCode }"
              @click="handleSelect(item.sessionCode)">
              <span class="chat-history-item-name">{{ item.sessionName }}</span>
              <span class="chat-history-item-time">{{ formatDateTime(item.updatedAt) }}</span>
            </BkDropdownItem>
          </template>
          <div
            v-else
            class="chat-history-empty">
            {{ t('暂无会话记录') }}
          </div>
        </ScrollFaker>
      </BkDropdownMenu>
    </template>
  </BkDropdown>
</template>

<script setup lang="ts">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  interface Props {
    activeSessionCode?: string;
    isLoading?: boolean;
    sessionList?: { sessionCode: string; sessionName: string; updatedAt: string }[];
  }

  type Emits = (e: 'select', sessionCode: string) => void;

  withDefaults(defineProps<Props>(), {
    activeSessionCode: '',
    isLoading: false,
    sessionList: () => [],
  });

  const emit = defineEmits<Emits>();

  const { t } = useI18n();

  const formatDateTime = (dateTime: string) => {
    if (dayjs(dateTime).isAfter(dayjs().subtract(1, 'hour'))) {
      return dayjs(dateTime).fromNow();
    }
    if (dayjs(dateTime).isAfter(dayjs().subtract(1, 'day'))) {
      return `${t('今天')} ${dayjs(dateTime).format('HH:mm:ss')}`;
    }
    return dayjs(dateTime).format('YYYY年MM月DD日 HH:mm:ss');
  };

  const isDropdownShow = ref(false);

  const handleHide = () => {
    isDropdownShow.value = false;
  };

  const handleShow = () => {
    isDropdownShow.value = true;
  };

  const handleSelect = (sessionCode: string) => {
    emit('select', sessionCode);
  };
</script>

<style lang="postcss">
  .chat-history-arrow {
    margin-left: 4px;
    font-size: 12px;
    transform: rotateZ(180deg);
    transition: transform 0.2s;

    &.is-flip {
      transform: rotateZ(0);
    }
  }

  .chat-history-dropdown-menu {
    width: 350px;
    max-height: 50vh;

    .chat-history-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;

      &.is-active {
        color: #3a84ff;
        background-color: #e1ecff;
      }
    }

    .chat-history-item-name {
      overflow: hidden;
      flex: 1;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .chat-history-item-time {
      flex-shrink: 0;
      font-size: 12px;
      color: #979ba5;
    }
  }

  .chat-history-scroll-area {
    max-height: 50vh;
  }

  .chat-history-empty {
    padding: 24px 16px;
    font-size: 12px;
    color: #979ba5;
    text-align: center;
  }
</style>
