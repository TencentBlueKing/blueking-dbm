import urlJoin from 'url-join';

interface ShortCutInfo {
  agent_code: string;
  agent_id: number;
  agent_name: string;
  components: {
    default: string;
    fill_back: boolean;
    fill_regx: string;
    key: string;
    max: null;
    min: null;
    name: string;
    options: any[];
    placeholder: string;
    required: boolean;
    rows: number;
    type: string;
  }[];
  content: string;
  icon: string;
  id: string;
  name: string;
  status: string;
}

export const enum AiBluekingModeEnum {
  COMMON = 'common',
  LOG_ANALYSIS = 'logAnalysis',
}

// 全局单实例
const aiBluekingRef = ref();
const aiBluekingMode = ref<AiBluekingModeEnum>(AiBluekingModeEnum['COMMON']);

let currentIsLogAnalysisMode = false;
let aiLogAnalysisShortCut: ShortCutInfo | null = null;

export const useState = () => {
  const apiUrl = urlJoin(window.BK_AJAX_URL, '/apis/ai/agent');

  const hideNimbus = ref(false);
  const showNewChatIcon = ref(true);
  const showHistoryIcon = ref(true);
  const showMoreIcon = ref(true);

  const isLogAnalysisMode = computed(() => aiBluekingMode.value === AiBluekingModeEnum['LOG_ANALYSIS']);

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

  watch(isLogAnalysisMode, async () => {
    if (isLogAnalysisMode.value === currentIsLogAnalysisMode) {
      return;
    }
    currentIsLogAnalysisMode = isLogAnalysisMode.value;
    if (isLogAnalysisMode.value) {
      // 读取智能体info接口
      const infoUrl = `${apiUrl}/agent/info/`;
      const response = await fetch(infoUrl, {
        credentials: 'include',
        method: 'GET',
      });
      const infoData = (await response.json()) as { data: { conversation_settings: { commands: ShortCutInfo[] } } };
      aiLogAnalysisShortCut =
        infoData.data.conversation_settings.commands.find((item) => item.id === 'LogAnalysis') ?? null;
    }
  });

  const show = async () => {
    await aiBluekingRef.value?.handleShow();
  };

  const hide = async () => {
    await aiBluekingRef.value?.handleClose();
  };

  const sendMessage = async (ticketTypeDisplay: string, message: string) => {
    if (aiLogAnalysisShortCut) {
      aiLogAnalysisShortCut.components[0].default = ticketTypeDisplay;
      aiLogAnalysisShortCut.components[1].default = message;
      await aiBluekingRef.value?.handleShortcutClick({
        shortcut: aiLogAnalysisShortCut,
        source: 'popup',
      });
    }
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
