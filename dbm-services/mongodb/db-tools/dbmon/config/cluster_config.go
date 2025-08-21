package config

import (
	"os"
	"strings"
	"sync"
	"time"

	"github.com/pkg/errors"
	"gopkg.in/yaml.v3"
)

type ClusterConfigItem struct {
	ClusterId string `json:"cluster_id" yaml:"cluster_id"`
	Segment   string `json:"segment" yaml:"segment"`
	Key       string `json:"key" yaml:"key"`
	Value     string `json:"value" yaml:"value"`
	Mtime     int    `json:"mtime" yaml:"mtime"`
}

type SetConfigItem struct {
	SetId             string `json:"set_id" yaml:"set_id"`
	ClusterConfigItem `json:",inline" yaml:",inline"`
}

type InstanceConfigItem struct {
	Instance          string `json:"instance" yaml:"instance"`
	ClusterConfigItem `json:",inline" yaml:",inline"`
}

type ClusterConfigConf struct {
	ClusterConfig  []ClusterConfigItem  `json:"cluster_config" yaml:"cluster_config"`
	SetConfig      []SetConfigItem      `json:"set_config" yaml:"set_config"`
	InstanceConfig []InstanceConfigItem `json:"instance_config" yaml:"instance_config"`
	CreateTime     time.Time            `json:"create_time" yaml:"create_time"`
	LastTime       time.Time            `json:"-" yaml:"-"`
	LastSize       int64                `json:"-" yaml:"-"` // file size
}

// _loadClusterConfigFile load cluster config file.
// If preConf is not nil, it will check file info to avoid unnecessary read
func _loadClusterConfigFile(fileName string, preConf *ClusterConfigConf) (*ClusterConfigConf, error) {
	fileInfo, err := os.Stat(fileName)
	if err != nil {
		return nil, errors.Wrap(err, "failed to get file info")
	}

	if preConf != nil && preConf.LastTime.Equal(fileInfo.ModTime()) && preConf.LastSize == fileInfo.Size() {
		return preConf, nil
	}

	data, err := os.ReadFile(fileName)
	if err != nil {
		return nil, errors.Wrap(err, "failed to read config file: "+fileName)
	}
	var config ClusterConfigConf
	if err := yaml.Unmarshal(data, &config); err != nil {
		return nil, errors.Wrap(err, "failed to unmarshal config file")
	}
	config.LastTime, config.LastSize = fileInfo.ModTime(), fileInfo.Size()
	return &config, nil
}

var registeredConfig = RegisteredClusterConfig()

const ShieldEndTimeKey = "shield-end-time"
const ShieldEndTimeFormat = "2006-01-02 15:04:05"

const SegmentMonitor = "monitor"
const SegmentAlarm = "alarm"
const SegmentLog = "log"
const SegmentBackup = "backup"
const SegmentParseLog = "parselog"

const KeyLoginTimeout = "loginTimeout"
const KeyShield = "shield"

const KeyEnable = "enable"
const KeyZip = "zip"
const KeyFullTag = "full-tag"
const KeyFullFreq = "full-freq"
const KeyIncrEnable = "incr-enable"
const KeyIncrTag = "incr-tag"
const KeyIncrFreq = "incr-freq"
const KeyArchive = "archive"
const KeyMaxDiskUsage = "max-disk-usage"
const KeyMinDiskUsage = "min-disk-usage"
const KeyMaxRecordPerSecond = "max-record-per-second"
const KeyMaxTime = "maxtime"
const KeyMaxSizeG = "maxsizeg"
const ValueTrue = "true"
const ValueFalse = "false"
const KeyNumParallelCollections = "concurrent"

// GetAllClusterConfigRows 所有的集群配置项
func GetAllClusterConfigRows() []ClusterConfigItem {
	return []ClusterConfigItem{
		{Segment: SegmentBackup, Key: KeyEnable, Value: ValueTrue},            // 是否开启备份
		{Segment: SegmentBackup, Key: KeyZip, Value: ValueTrue},               // 是否开启压缩，默认开启
		{Segment: SegmentBackup, Key: KeyFullTag, Value: "MONGO_FULL_BACKUP"}, // full_tag
		{Segment: SegmentBackup, Key: KeyFullFreq, Value: "86400"},            // 全备时间间隔,默认是1天
		{Segment: SegmentBackup, Key: KeyIncrEnable, Value: "true"},           // 是否开启增量备份
		{Segment: SegmentBackup, Key: KeyIncrTag, Value: "MONGO_INCR_BACKUP"}, // incr_tag
		{Segment: SegmentBackup, Key: KeyIncrFreq, Value: "3600"},             // 增量备份时间间隔，单位秒
		{Segment: SegmentBackup, Key: KeyArchive, Value: ValueFalse},          // mongodump --archive 方式备份，默认为false
		{Segment: SegmentBackup, Key: KeyMaxDiskUsage, Value: "50"},           // 磁盘使用率超过此值为磁盘紧急状态, 默认50
		{Segment: SegmentBackup, Key: KeyMinDiskUsage, Value: "25"},           // 磁盘使用率低于此值为磁盘正常状态, 默认25
		{Segment: SegmentBackup, Key: KeyNumParallelCollections, Value: "0"},  // 备份时并行备份的集合数，默认0，表示用mongodump的默认值
		// monitor.loginTimeout: checkService 登录超时时间，单位秒。默认10秒，有效值为[5,360]
		{Segment: SegmentMonitor, Key: KeyLoginTimeout, Value: "10"},
		{Segment: SegmentAlarm, Key: KeyShield, Value: ValueFalse},             // 是否屏蔽事件产生
		{Segment: SegmentAlarm, Key: ShieldEndTimeKey, Value: ""},              // 屏蔽结束时间，为空为0都表示永久屏蔽
		{Segment: SegmentParseLog, Key: KeyEnable, Value: ValueTrue},           // 是否开启日志解析
		{Segment: SegmentParseLog, Key: KeyMaxRecordPerSecond, Value: "10000"}, // 每秒解析的最大日志数
		// mongo.log.* 文件最大时间，超过这个时间就删除 2592000 = 30天
		{Segment: SegmentLog, Key: KeyMaxTime, Value: "2592000"},
		// mongo.log.* 文件最大大小，超过这个大小就删除，从最旧的开始删除
		{Segment: SegmentLog, Key: KeyMaxSizeG, Value: "1"},
	}
}

// RegisteredClusterConfig  只有在这里注册的配置项才能被使用，Segment不能有.号
func RegisteredClusterConfig() *sync.Map {
	rows := GetAllClusterConfigRows()
	var m sync.Map
	for _, row := range rows {
		if strings.Contains(row.Segment, ".") {
			panic("segment cannot contain '.'")
		}
		if _, ok := m.Load(row.Segment + "." + row.Key); ok {
			panic("duplicate segment.key: " + row.Segment + "." + row.Key)
		}
		m.Store(row.Segment+"."+row.Key, row.Value)
	}
	return &m
}
