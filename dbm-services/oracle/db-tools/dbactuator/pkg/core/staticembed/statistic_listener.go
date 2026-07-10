package staticembed

import "embed"

// StatisticListenerFileName TODO
var StatisticListenerFileName = "statistic_listener.ora"

// StatisticListener TODO
//
//go:embed statistic_listener.ora
var StatisticListener embed.FS
