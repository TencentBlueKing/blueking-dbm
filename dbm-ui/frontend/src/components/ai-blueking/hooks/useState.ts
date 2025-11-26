import { useSystemEnviron } from '@stores';

export const enum AiBluekingModeEnum {
  COMMON = 'common',
  LOG_ANALYSIS = 'logAnalysis',
}

// 全局单实例
const aiBluekingRef = ref();
const aiBluekingMode = ref<AiBluekingModeEnum>(AiBluekingModeEnum['COMMON']);

export const useState = () => {
  const systemEnvironStore = useSystemEnviron();

  const hideNimbus = ref(false);
  const showNewChatIcon = ref(true);
  const showHistoryIcon = ref(true);
  const showMoreIcon = ref(true);

  const isLogAnalysisMode = computed(() => aiBluekingMode.value === AiBluekingModeEnum['LOG_ANALYSIS']);
  const apiUrl = computed(() => (isLogAnalysisMode ? logAnalysisUrl : aidevUrl));

  const { BK_AIDEV_LOG_ANALYSIS_URL: logAnalysisUrl, BK_AIDEV_URL: aidevUrl } = systemEnvironStore.urls;

  watch(
    isLogAnalysisMode,
    () => {
      if (isLogAnalysisMode.value) {
        showNewChatIcon.value = false;
        showHistoryIcon.value = false;
        showMoreIcon.value = false;
        hideNimbus.value = true;
      } else {
        showNewChatIcon.value = true;
        showHistoryIcon.value = true;
        showMoreIcon.value = true;
        hideNimbus.value = false;
      }
    },
    {
      immediate: true,
    },
  );

  const show = async () => {
    await aiBluekingRef.value?.handleShow();
  };

  const hide = async () => {
    await aiBluekingRef.value?.handleClose();
  };

  const sendMessage = async (message: string) => {
    await aiBluekingRef.value?.handleSendMessage(message);
  };

  const changeMode = (mode: AiBluekingModeEnum) => {
    aiBluekingMode.value = mode;
  };

  return {
    aiBluekingMode,
    aiBluekingRef,
    apiUrl,
    changeMode,
    hide,
    hideNimbus,
    sendMessage,
    show,
    showHistoryIcon,
    showMoreIcon,
    showNewChatIcon,
  };
};
