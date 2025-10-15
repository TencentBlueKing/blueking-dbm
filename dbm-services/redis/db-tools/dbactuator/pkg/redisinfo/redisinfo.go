// Package redisinfo TODO
package redisinfo

/*
	original code from https://github.com/geoffreybauduin/redis-info
	built-in doesn't support the some self-developed redis version
	so we need to parse the info output by ourselves
*/
import (
	"fmt"
	"reflect"
	"sort"
	"strconv"
	"strings"
)

// Parse returns an Info struct from the provided content string
func Parse(content string) (Info, error) {
	info := &Info{}
	err := info.fromString(content)
	if err != nil {
		return Info{}, err
	}
	return *info, nil
}

// Info describes the INFO data returned by Redis
type Info struct {
	Server      Server      `json:"server"`
	Clients     Client      `json:"clients"`
	Memory      Memory      `json:"memory"`
	Persistence Persistence `json:"persistence"`
	Stats       Stats       `json:"stats"`
	Replication Replication `json:"replication"`
	CPU         CPU         `json:"cpu"`
	Cluster     Cluster     `json:"cluster"`
	Keyspace    []Keyspace  `json:"keyspace"`
}

type category interface {
	fromString(string) error
}

func (i *Info) fromString(content string) error {
	content = strings.Replace(content, "\r", "", -1) // remove all \r that are in the file
	lines := strings.Split(content, "\n")
	contentPerCategory := make(map[string][]string, 0)
	currentCategory := ""
	for _, line := range lines {
		if line == "" {
			continue
		} else if strings.HasPrefix(line, "# ") {
			currentCategory = strings.ToLower(line[2:])
			contentPerCategory[currentCategory] = make([]string, 0)
		} else {
			contentPerCategory[currentCategory] = append(contentPerCategory[currentCategory], line)
		}
	}
	val := reflect.ValueOf(i).Elem()
	for idx := 0; idx < val.NumField(); idx++ {
		field := val.Type().Field(idx)
		if categoryName := field.Tag.Get("json"); categoryName != "-" && categoryName != "" {
			if len(contentPerCategory[categoryName]) == 0 {
				continue
			}
			fieldVal := val.Field(idx)
			fieldValue := reflect.New(fieldVal.Type())
			if categoryValue, ok := fieldValue.Interface().(category); ok {
				if err := categoryValue.fromString(strings.Join(contentPerCategory[categoryName], "\n")); err != nil {
					return fmt.Errorf("cannot parse category %s: %w", categoryName, err)
				}
				valueToSet := reflect.Indirect(reflect.ValueOf(categoryValue))
				if !fieldVal.CanSet() {
					return fmt.Errorf("cannot set value for field %s", categoryName)
				}
				fieldVal.Set(valueToSet)
			} else if fieldVal.Kind() == reflect.Slice {
				parsed, err := sep(strings.Join(contentPerCategory[categoryName], "\n"), "\n", ":")
				if err != nil {
					return err
				}
				if err := parseSlice(parsed, fieldVal, "db"); err != nil {
					return err
				}
			} else {
				return fmt.Errorf("cannot parse kind %s for field %s", fieldVal.Kind(), categoryName)
			}
		}
	}
	return nil
}

// Server TODO
type Server struct {
	RedisVersion    string `json:"redis_version"`
	RedisGitSha1    string `json:"redis_git_sha1"`
	RedisGitDirty   bool   `json:"redis_git_dirty"`
	RedisBuildID    string `json:"redis_build_id"`
	RedisMode       string `json:"redis_mode"`
	OS              string `json:"os"`
	ArchBits        uint8  `json:"arch_bits"`
	MultiplexingAPI string `json:"multiplexing_api"`
	GCCVersion      string `json:"gcc_version"`
	ProcessID       uint64 `json:"process_id"`
	RunID           string `json:"run_id"`
	TCPPort         uint16 `json:"tcp_port"`
	UptimeInSeconds int64  `json:"uptime_in_seconds"`
	UptimeInDays    int64  `json:"uptime_in_days"`
	HZ              uint64 `json:"hz"`
	LRUClock        int64  `json:"lru_clock"`
	Executable      string `json:"executable"`
	ConfigFile      string `json:"config_file"`
}

func (s *Server) fromString(content string) error { return parseStruct(s, content) }

// Client TODO
/*
# Clients
connected_clients:5
cluster_connections:0
maxclients:180000
client_recent_max_input_buffer:20480
client_recent_max_output_buffer:0
blocked_clients:0
tracking_clients:0
clients_in_timeout_table:0
*/
type Client struct {
	ConnectedClients        int64 `json:"connected_clients"`
	ClientLongestOutputList int64 `json:"client_longest_output_list"`
	ClientBiggestInputBuf   int64 `json:"client_biggest_input_buf"`
	BlockedClients          int64 `json:"blocked_clients"`
}

func (s *Client) fromString(content string) error { return parseStruct(s, content) }

// Memory TODO
/*
最简单版本的info memory
	# Memory
	used_memory:55347544
	used_memory_human:52.78M
	used_memory_rss:49123328
	used_memory_peak:55939360
	used_memory_peak_human:53.35M
	used_memory_lua:33792
	mem_fragmentation_ratio:0.89
	mem_allocator:jemalloc-3.6.0
*/
type Memory struct {
	UsedMemory             int64   `json:"used_memory"`
	UsedMemoryHuman        string  `json:"used_memory_human"`
	UsedMemoryRss          int64   `json:"used_memory_rss"`
	UsedMemoryRssHuman     string  `json:"used_memory_rss_human"`
	UsedMemoryPeak         int64   `json:"used_memory_peak"`
	UsedMemoryPeakHuman    string  `json:"used_memory_peak_human"`
	TotalSystemMemory      int64   `json:"total_system_memory,omitempty"`
	TotalSystemMemoryHuman string  `json:"total_system_memory_human,omitempty"`
	UsedMemoryLua          int64   `json:"used_memory_lua"`
	UsedMemoryLuaHuman     string  `json:"used_memory_lua_human,omitempty"`
	Maxmemory              int64   `json:"maxmemory,omitempty"`
	MaxmemoryHuman         string  `json:"maxmemory_human,omitempty"`
	MaxmemoryPolicy        string  `json:"maxmemory_policy,omitempty"`
	MemFragmentationRatio  float64 `json:"mem_fragmentation_ratio,omitempty"`
	MemAllocator           string  `json:"mem_allocator,omitempty"`
}

func (s *Memory) fromString(content string) error { return parseStruct(s, content) }

// Persistence TODO
type Persistence struct {
	Loading                  bool   `json:"loading"`
	RdbChangesSinceLastSave  int64  `json:"rdb_changes_since_last_save"`
	RdbBgsaveInProgress      bool   `json:"rdb_bgsave_in_progress"`
	RdbLastSaveTime          int64  `json:"rdb_last_save_time"`
	RdbLastBgsaveStatus      string `json:"rdb_last_bgsave_status"`
	RdbLastBgsaveTimeSec     int64  `json:"rdb_last_bgsave_time_sec"`
	RdbCurrentBgsaveTimeSec  int64  `json:"rdb_current_bgsave_time_sec"`
	AofEnabled               bool   `json:"aof_enabled"`
	AofRewriteInProgress     bool   `json:"aof_rewrite_in_progress"`
	AofRewriteScheduled      bool   `json:"aof_rewrite_scheduled"`
	AofLastRewriteTimeSec    int64  `json:"aof_last_rewrite_time_sec"`
	AofCurrentRewriteTimeSec int64  `json:"aof_current_rewrite_time_sec"`
	AofLastBgrewriteStatus   string `json:"aof_last_bgrewrite_status"`
	AofLastWriteStatus       string `json:"aof_last_write_status"`
}

func (s *Persistence) fromString(content string) error { return parseStruct(s, content) }

// Stats TODO
type Stats struct {
	TotalConnectionsReceived int64   `json:"total_connections_received"`
	TotalCommandsProcessed   int64   `json:"total_commands_processed"`
	InstantaneousOpsPerSec   int64   `json:"instantaneous_ops_per_sec"`
	TotalNetInputBytes       int64   `json:"total_net_input_bytes,omitempty"`
	TotalNetOutputBytes      int64   `json:"total_net_output_bytes,omitempty"`
	InstantaneousInputKbps   float64 `json:"instantaneous_input_kbps,omitempty"`
	InstantaneousOutputKbps  float64 `json:"instantaneous_output_kbps,omitempty"`
	RejectedConnections      int64   `json:"rejected_connections"`
	SyncFull                 int64   `json:"sync_full"`
	SyncPartialOk            int64   `json:"sync_partial_ok"`
	SyncPartialErr           int64   `json:"sync_partial_err"`
	ExpiredKeys              int64   `json:"expired_keys"`
	EvictedKeys              int64   `json:"evicted_keys"`
	KeyspaceHits             int64   `json:"keyspace_hits"`
	KeyspaceMisses           int64   `json:"keyspace_misses"`
	PubsubChannels           int64   `json:"pubsub_channels"`
	PubsubPatterns           int64   `json:"pubsub_patterns"`
	LatestForkUsec           int64   `json:"latest_fork_usec"`
	MigrateCachedSockets     bool    `json:"migrate_cached_sockets"`
}

func (s *Stats) fromString(content string) error { return parseStruct(s, content) }

// Replication TODO
type Replication struct {
	Role                       string             `json:"role"`
	ConnectedSlaves            uint64             `json:"connected_slaves"`
	MasterHost                 string             `json:"master_host,omitempty"`
	MasterPort                 int64              `json:"master_port,omitempty"`
	MasterLinkUp               string             `json:"master_link_status,omitempty"`
	SlaveReplOffset            int64              `json:"slave_repl_offset,omitempty"`
	Slaves                     []ReplicationSlave `json:"slave"`
	MasterReplOffset           int64              `json:"master_repl_offset"`
	ReplBacklogActive          bool               `json:"repl_backlog_active"`
	ReplBacklogSize            uint64             `json:"repl_backlog_size"`
	ReplBacklogFirstByteOffset uint64             `json:"repl_backlog_first_byte_offset"`
	ReplBacklogHistLen         uint64             `json:"repl_backlog_histlen"`
	SlavePriority              uint64             `json:"slave_priority"`
}

// ReplicationSlave TODO
type ReplicationSlave struct {
	ID     int64  `json:"id,omitempty" index:"true"`
	IP     string `json:"ip"`
	Port   uint16 `json:"port"`
	State  string `json:"state"`
	Offset int64  `json:"offset"`
	Lag    int64  `json:"lag"`
}

func (rs *ReplicationSlave) fromString(content string) error { return parseStruct(rs, content) }

func (s *Replication) fromString(content string) error { return parseStruct(s, content) }

// CPU TODO
type CPU struct {
	UsedCPUSys          float64 `json:"used_cpu_sys"`
	UsedCPUUser         float64 `json:"used_cpu_user"`
	UsedCPUSysChildren  float64 `json:"used_cpu_sys_children"`
	UsedCPUUserChildren float64 `json:"used_cpu_user_children"`
}

func (s *CPU) fromString(content string) error { return parseStruct(s, content) }

// Cluster TODO
type Cluster struct {
	ClusterEnabled bool `json:"cluster_enabled"`
}

func (s *Cluster) fromString(content string) error { return parseStruct(s, content) }

// Keyspace TODO
type Keyspace struct {
	DB      int64  `json:"db,omitempty" index:"true"`
	Keys    uint64 `json:"keys"`
	Expires uint64 `json:"expires"`
	AvgTTL  uint64 `json:"avg_ttl"`
}

func (s *Keyspace) fromString(content string) error { return parseStruct(s, content) }

func sep(content string, lineSep string, keySep string) (map[string]string, error) {
	parsed := map[string]string{}
	lines := strings.Split(content, lineSep)
	for nbr, line := range lines {
		lineContent := strings.SplitN(line, keySep, 2)
		if len(lineContent) != 2 {
			return nil, fmt.Errorf("invalid line %d: '%s'", nbr, line)
		}
		parsed[lineContent[0]] = lineContent[1]
	}
	return parsed, nil
}

// parseStruct 解析struct类型的字段
func parseStruct(c category, content string) error {
	parsed, err := sep(content, "\n", ":")
	if err != nil {
		return err
	}
	val := reflect.ValueOf(c).Elem()
	for idx := 0; idx < val.NumField(); idx++ {
		field := val.Type().Field(idx)
		if jsonTag := field.Tag.Get("json"); jsonTag != "-" && jsonTag != "" {
			splitJSONTag := strings.Split(jsonTag, ",")
			fieldName := splitJSONTag[0]
			stringVal, e := parsed[fieldName]
			if !e {
				continue
			}
			// fmt.Printf("tag:%s, v:%s splitJSONTag %+v", splitJSONTag, stringVal, splitJSONTag)
			if len(splitJSONTag) == 2 && splitJSONTag[1] == "omitempty" && stringVal == "" {
				continue
			}
			fieldVal := val.Field(idx)
			switch field.Type.Kind() {
			case reflect.String:
				fieldVal.Set(reflect.ValueOf(stringVal))
			case reflect.Bool:
				fieldVal.Set(reflect.ValueOf(stringVal == "1"))
			case reflect.Uint8:
				val, err := strconv.ParseUint(stringVal, 10, 8)
				if err != nil {
					return fmt.Errorf("cannot parse uint8 for %s: %w", fieldName, err)
				}
				fieldVal.Set(reflect.ValueOf(uint8(val)))
			case reflect.Uint16:
				val, err := strconv.ParseUint(stringVal, 10, 16)
				if err != nil {
					return fmt.Errorf("cannot parse uint16 for %s: %w", fieldName, err)
				}
				fieldVal.Set(reflect.ValueOf(uint16(val)))
			case reflect.Uint64:
				val, err := strconv.ParseUint(stringVal, 10, 64)
				if err != nil {
					return fmt.Errorf("cannot parse uint64 for %s: %w", fieldName, err)
				}
				fieldVal.Set(reflect.ValueOf(uint64(val)))
			case reflect.Int64:
				val, err := strconv.ParseInt(stringVal, 10, 64)
				if err != nil {
					return fmt.Errorf("cannot parse int64 for %s: %w map:%+v", fieldName, err, parsed)
				}
				fieldVal.Set(reflect.ValueOf(int64(val)))
			case reflect.Float64:
				val, err := strconv.ParseFloat(stringVal, 64)
				if err != nil {
					return fmt.Errorf("cannot parse float64 for %s: %w", fieldName, err)
				}
				fieldVal.Set(reflect.ValueOf(val))
			case reflect.Slice:
				if err := parseSlice(parsed, fieldVal, fieldName); err != nil {
					return err
				}
			default:
				return fmt.Errorf("unhandled type %s for %s", field.Type.Kind(), fieldName)
			}
		}
	}
	return nil
}

// parseSlice 解析slice类型的字段
func parseSlice(dict map[string]string, fieldVal reflect.Value, prefix string) error {
	toUse := make([]int64, 0)
	for fieldName := range dict {
		if strings.HasPrefix(fieldName, prefix) {
			index, err := strconv.ParseInt(fieldName[len(prefix):], 10, 64)
			if err != nil {
				// return fmt.Errorf("cannot parse index from field name %s: %w", fieldName, err)
				continue
			}
			toUse = append(toUse, index)
		}
	}
	sort.SliceStable(toUse, func(i, j int) bool { return toUse[i] < toUse[j] })
	slice := reflect.MakeSlice(fieldVal.Type(), 0, 0)
	for _, fieldIndex := range toUse {
		fieldName := fmt.Sprintf("%s%d", prefix, fieldIndex)
		parsed, err := sep(dict[fieldName], ",", "=")
		if err != nil {
			return err
		}
		content := make([]string, 0)
		for key, value := range parsed {
			content = append(content, fmt.Sprintf("%s:%s", key, value))
		}
		v := reflect.New(fieldVal.Type().Elem())
		if err := v.Interface().(category).fromString(strings.Join(content, "\n")); err != nil {
			return err
		}
		for idx := 0; idx < v.Elem().NumField(); idx++ {
			field := v.Elem().Type().Field(idx)
			if field.Tag.Get("index") == "true" {
				v.Elem().Field(idx).SetInt(fieldIndex)
			}
		}
		slice = reflect.Append(slice, reflect.Indirect(v))
	}
	fieldVal.Set(slice)
	return nil
}
