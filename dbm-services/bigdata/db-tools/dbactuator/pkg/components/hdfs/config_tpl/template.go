package config_tpl

import "embed"

// Log4jPropertiesFileName TODO
var Log4jPropertiesFileName = "log4j.properties"

// Log4jPropertiesFile TODO
//
//go:embed log4j.properties
var Log4jPropertiesFile embed.FS

// RackAwareFileName TODO
var RackAwareFileName = "rack-aware.sh"

// RackAwareFile TODO
//
//go:embed rack-aware.sh
var RackAwareFile embed.FS

// HadoopEnvFileName TODO
var HadoopEnvFileName = "hadoop-env.sh"

// HadoopEnvFile TODO
//
//go:embed hadoop-env.sh
var HadoopEnvFile embed.FS

// HaproxyCfgFileName TODO
var HaproxyCfgFileName = "haproxy.cfg"

// HaproxyCfgFile TODO
//
//go:embed haproxy.cfg
var HaproxyCfgFile embed.FS

// HadoopDaemonWrapperFileName TODO
var HadoopDaemonWrapperFileName = "hadoop-daemon-wrapper.sh"

// HadoopDaemonWrapper TODO
//
//go:embed hadoop-daemon-wrapper.sh
var HadoopDaemonWrapper embed.FS

// ExternalCheckFileName TODO
var ExternalCheckFileName = "check_nn_active"

// ExternalCheckFile TODO
//
//go:embed check_nn_active
var ExternalCheckFile embed.FS
