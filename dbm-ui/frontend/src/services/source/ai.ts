import http from '../http';

const path = '/apis/ai';

export function getAgentInfo() {
  return http.get(`${path}/agent/agent/info/`);
}

export function getAgentPing() {
  return http.get(`${path}/agent/agent/ping/`);
}

export function chatCompletion(params: {
  messages: {
    content: string;
    role: string;
  }[];
  model: string;
}) {
  return http.post(`${path}/agent/chat_completion/`, params);
}

export function chatGroup(params: { name: string }) {
  return http.post(`${path}/agent/chat_group/`, params);
}

export function getSession() {
  return http.get<
    {
      create_at: string;
      create_by: string;
      model: string;
      role_info: {
        generate_type: string;
        role_content: {
          content: string;
          extra: string;
          id: string;
          role: string;
        }[];
        role_id: number;
        role_name: string;
        role_variable: string[];
        status: string;
      };
      session_code: string;
      session_name: string;
      session_property: {
        is_auto_clac_prompt: boolean;
        is_auto_clear: boolean;
        test_code: string | null;
      };
      updated_at: string;
      updated_by: string;
    }[]
  >(`${path}/agent/session/`);
}

export function createSession(params: {
  is_temporary: boolean;
  session_code: string;
  session_name: string;
  session_property: Record<string, any>;
}) {
  return http.post<{
    session_code: string;
  }>(`${path}/agent/session/`, params);
}
export function batchDeleteSession(params: { session_codes: string[] }) {
  return http.post(`${path}/agent/session/batch_delete/`, params);
}
export function getSessionDetail(params: { session_id: string }) {
  return http.get(`${path}/agent/session/${params.session_id}/`);
}
export function updateSession(params: { session_id: string }) {
  return http.post(`${path}/agent/session/${params.session_id}/`, params);
}
export function deleteSession(params: { session_code: string }) {
  return http.delete(`${path}/agent/session/${params.session_code}/`);
}
export function renameSession(params: { session_code: string; session_name: string }) {
  return http.post(`${path}/agent/session/${params.session_code}/ai_rename/`, params);
}
export function sessionContent(params: { session_id: string }) {
  return http.post(`${path}/agent/session_content/`, params);
}
// 更新会话信息
export function updateSessionInfo(params: { session_code: string; session_name: string }) {
  return http.put(`${path}/agent/session/${params.session_code}/`, params);
}

export function getFlowLogAnnlysis(params: { flow_id: string; ticket_id: number }) {
  return http.post(`${path}/agent/log/get_flow_log_analysis/`, params);
}
