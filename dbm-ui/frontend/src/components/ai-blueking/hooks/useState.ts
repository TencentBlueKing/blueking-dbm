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

  const apiUrl = computed(() =>
    aiBluekingMode.value === AiBluekingModeEnum['LOG_ANALYSIS'] ? logAnalysisUrl : aidevUrl,
  );

  const { BK_AIDEV_LOG_ANALYSIS_URL: logAnalysisUrl, BK_AIDEV_URL: aidevUrl } = systemEnvironStore.urls;

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
    sendMessage,
    show,
  };
};
