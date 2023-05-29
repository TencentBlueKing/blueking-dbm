bk_biz_id: {{ .BkBizId }}
ip: {{ .IP }}
port: {{ .Port }}
bk_instance_id: {{ .BkInstanceId }}
immute_domain: {{ .ImmuteDomain }}
machine_type: {{ .MachineType }}
bk_cloud_id: {{ .BkCloudId }}
log:
  console: true
  log_file_dir: {{ .LogPath }}
  debug: true
  source: true
  json: false
api_url: http://127.0.0.1:9999
items_config_file: {{ .ItemsConfigPath }}
interact_timeout: 2s
default_schedule: '@every 1m'
