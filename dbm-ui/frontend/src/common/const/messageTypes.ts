/**
 * 消息通知类型
 */

import { t } from '@locales/index';

export enum MessageTypes {
  MAIL = 'mail',
  RTX = 'rtx',
  SMS = 'sms',
  VOICE = 'voice',
  WECOM_ROBOT = 'wecom_robot',
  WEIXIN = 'weixin',
}

export const InputMessageTypes = [MessageTypes.WECOM_ROBOT] as string[];

export const MessageTipMap: Record<string, string> = {
  [MessageTypes.WECOM_ROBOT]: [
    t('获取会话ID方法:'),
    t('1. 群聊添加群机器人: 蓝鲸审批助手'),
    t('2. 手动蓝鲸审批助手，获取会话ID'),
    t('3. 将获取到的会话ID粘贴到输入框，多个会话ID使用逗号分隔'),
  ].join('\n'),
};
