ip: {{ .IP }}
port: {{ .Port }}
immute_domain: {{ .ImmuteDomain }}
machine_type: {{ .MachineType }}
role: {{ .Role }}
bk_cloud_id: {{ .BkCloudId }}
log:
  console: true
  log_file_dir: {{ .LogPath }}
  debug: true
  source: true
  json: false
api_url: http://127.0.0.1:9999
items_config_file: {{ .ItemsConfigPath }}
auth:
  user: {{ .User }}
  password: {{ .Password }}
dba_sys_dbs: {{ .DbaSysDbs }}
interact_timeout: 2s
default_schedule: '@every 1m'