package common

// PredixConf TODO
var PredixConf = `Bind {{ip:port}}
WorkerThreads {{worker_threads}}
ClientTimeout {{client_timeout}}
Authority {
    Auth "{{predixy_password}}" {
        Mode write
    }
}
Log {{log_path}}
LogRotate 1d
ClusterServerPool {
    Password {{redis_password}}
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
