package common

// PredixConf predixy ClusterServerPool 配置文件模板
var PredixConf = `Bind {{ip:port}}
WorkerThreads {{worker_threads}}
ClientTimeout {{client_timeout}}
SlowlogLogSlowerThan {{slowlog_Log_slower_than}}
SlowlogMaxLen {{slowlog_max_len}}
Authority {
	Auth "{{predixy_password}}" {
        Mode write
    }
	Auth "{{predixy_admin_password}}" {
        Mode admin
    }
}
Log {{log_path}}
LogRotate 1d
ClusterServerPool {
    Password "{{redis_password}}"
    RefreshInterval {{refresh_interval}}
    ServerFailureLimit {{server_failure_limit}} 
    ServerRetryTimeout {{server_retry_timeout}}
    ServerTimeout {{server_timeout}}
    KeepAlive {{keep_alive}}
    Servers {
        {{server:port}}
    }
}
LatencyMonitor all {
        Commands {
                + all
        }
        TimeSpan {
                + 100
                + 500
                + 1000
                + 5000
                + 10000
        }
}
`

// PredixyStandaloneConf predixy StandaloneServerPool 配置文件模板 (用于PredixyTendisplusInstance集群类型)
var PredixyStandaloneConf = `Bind {{ip:port}}
WorkerThreads {{worker_threads}}
ClientTimeout {{client_timeout}}
SlowlogLogSlowerThan {{slowlog_Log_slower_than}}
SlowlogMaxLen {{slowlog_max_len}}
Authority {
	Auth "{{predixy_password}}" {
        Mode write
    }
	Auth "{{predixy_admin_password}}" {
        Mode admin
    }
}
Log {{log_path}}
LogRotate 1d
StandaloneServerPool {
    Password "{{redis_password}}"
    Databases {{databases}}
    Hash fnv1a_64
    HashTag "{{hash_tag}}"
    Distribution modula
    RefreshMethod manual
    RefreshInterval {{refresh_interval}}
    ServerFailureLimit {{server_failure_limit}} 
    ServerRetryTimeout {{server_retry_timeout}}
    ServerTimeout {{server_timeout}}
    ServerConnections {{server_connections}}
    KeepAlive {{keep_alive}}
    Masters {
        {{server:port seg}}
    }
}

LatencyMonitor all {
        Commands {
                + all
        }
        TimeSpan {
                + 100
                + 500
                + 1000
                + 5000
                + 10000
        }
}
`
