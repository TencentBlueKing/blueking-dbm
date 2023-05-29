ip: {{ cmdb_instance.host.bk_host_innerip }}
port: 9999
bk_cloud_id: {{ cmdb_instance.host.bk_cloud_id }}
bk_monitor_beat:
  custom_event:
    bk_data_id: 542898
    access_token: xxxx
    report_type: agent
    message_kind: event
  custom_metrics:
    bk_data_id: 543957
    access_token: xxxx
    report_type: agent
    message_kind: timeseries
  beat_path: {{ plugin_path.setup_path }}/plugins/bin/bkmonitorbeat
  agent_address: {{ plugin_path.endpoint }}
log:
    console: true
    log_file_dir: {{ plugin_path.log_path }}
    debug: false
    source: true
    json: true
pid_path: {{ plugin_path.pid_path }}
jobs_user: mysql
jobs_config: {{ plugin_path.setup_path }}/plugins/etc/jobs-config.yaml


