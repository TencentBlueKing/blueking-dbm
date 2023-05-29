ip: {{ .IP }}
port: 9999
bk_cloud_id: {{ .BkCloudId }}
bk_monitor_beat:
  custom_event:
    bk_data_id: {{ .EventDataId }}
    access_token: {{ .EventDataToken }}
    report_type: agent
    message_kind: event
  custom_metrics:
    bk_data_id: {{ .MetricsDataId }}
    access_token: {{ .MetricsDataToken }}
    report_type: agent
    message_kind: timeseries
  beat_path: {{ .BeatPath }}
  agent_address: {{ .AgentAddress }}
log:
    console: false
    log_file_dir: {{ .LogPath }}
    debug: false
    source: true
    json: true
pid_path: {{ .PidPath }}
jobs_user: mysql
jobs_config: {{ .InstallPath }}/jobs-config.yaml


