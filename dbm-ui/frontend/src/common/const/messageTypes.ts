/**
 * 消息通知类型
 */

export enum MessageTypes {
  SMS = 'sms',
  WEIXIN = 'weixin',
  MAIL = 'mail',
  VOICE = 'voice',
  RTX = 'rtx',
  WECOM_ROBOT = 'wecom_robot',
}

export const InputMessageTypes = [MessageTypes.WECOM_ROBOT] as string[];
