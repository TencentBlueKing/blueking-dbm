/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package harvest

import (
	"encoding/json"
	"reflect"
	"strings"

	"dbm-services/common/dbha-v2/pkg/converter"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// redisInfo redis info key-value pair
type redisInfo struct {
	Key   string
	Value string
}

// convertToRedisStatus convert the redis info to status
func convertToRedisStatus(info []redisInfo) *haprobe.RedisClusterStatus {
	infoMap := map[string]string{}
	for _, i := range info {
		infoMap[strings.ToLower(i.Key)] = i.Value
	}

	status := haprobe.RedisClusterStatus{}
	t := reflect.TypeOf(status)
	v := reflect.ValueOf(&status).Elem()
	setFieldByReflection(v, t, infoMap)

	return &status
}

// parseInfoToTwemproxyStatus parses Twemproxy stats JSON output to TwemproxyStatus
func parseInfoToTwemproxyStatus(info []byte, status *haprobe.RedisTwemproxyStatus) {
	if info == nil {
		return
	}

	var rawStats map[string]json.RawMessage
	if err := json.Unmarshal(info, &rawStats); err != nil {
		logger.Warn("failed to parse twemproxy stats json, errmsg: %s", err)
		return
	}

	statsMap := make(map[string]string)
	for key, value := range rawStats {
		var strVal string
		if err := json.Unmarshal(value, &strVal); err != nil {
			var numVal int64
			if err := json.Unmarshal(value, &numVal); err == nil {
				strVal, _ = converter.ToJsonLine(numVal)
			} else {
				continue
			}
		}
		statsMap[strings.ToLower(key)] = strVal
	}

	t := reflect.TypeOf(*status)
	v := reflect.ValueOf(status).Elem()
	setFieldByReflection(v, t, statsMap)

	for _, poolData := range rawStats {
		var poolStats map[string]json.RawMessage
		if err := json.Unmarshal(poolData, &poolStats); err != nil {
			continue
		}

		for serverAddr, serverData := range poolStats {
			var backend haprobe.RedisTwemproxyBackend
			if err := json.Unmarshal(serverData, &backend); err != nil {
				continue
			}
			backend.Server = serverAddr
			status.Backends = append(status.Backends, backend)
		}
	}
}

// parseInfoToPredixyStatus parses Predixy INFO output to PredixyStatus
func parseInfoToPredixyStatus(info string, status *haprobe.RedisPredixyStatus) {
	if info == "" {
		return
	}
	infoMap := parseRedisInfoToMap(info)
	t := reflect.TypeOf(*status)
	v := reflect.ValueOf(status).Elem()
	setFieldByReflection(v, t, infoMap)
}

func parsePredixyServersInfo(info string, status *haprobe.RedisPredixyStatus) {
	if info == "" {
		return
	}

	lines := strings.Split(info, "\n")
	var currentBackend *haprobe.RedisPredixyBackend

	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		lineLower := strings.ToLower(line)
		if strings.HasPrefix(lineLower, "server:") {
			if currentBackend != nil {
				status.Backends = append(status.Backends, *currentBackend)
			}
			currentBackend = &haprobe.RedisPredixyBackend{
				Server: line[len("server:"):],
			}
			continue
		}

		if currentBackend != nil {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) != 2 {
				continue
			}
			key := strings.ToLower(strings.TrimSpace(parts[0]))
			value := strings.TrimSpace(parts[1])

			switch key {
			case "role":
				currentBackend.Role = value
			case "group":
				currentBackend.Group = value
			case "dc":
				currentBackend.DC = value
			case "connections":
				if v, err := converter.ToInt64(value); err == nil {
					currentBackend.Connections = v
				} else {
					logger.Warn("failed to convert connections value: %s to int64, errmsg: %s", value, err)
				}
			case "requests":
				if v, err := converter.ToInt64(value); err == nil {
					currentBackend.Requests = v
				} else {
					logger.Warn("failed to convert requests value: %s to int64, errmsg: %s", value, err)
				}
			case "responses":
				if v, err := converter.ToInt64(value); err == nil {
					currentBackend.Responses = v
				} else {
					logger.Warn("failed to convert responses value: %s to int64, errmsg: %s", value, err)
				}
			case "sendbytes":
				if v, err := converter.ToInt64(value); err == nil {
					currentBackend.SendBytes = v
				} else {
					logger.Warn("failed to convert sendbytes value: %s to int64, errmsg: %s", value, err)
				}
			case "recvbytes":
				if v, err := converter.ToInt64(value); err == nil {
					currentBackend.RecvBytes = v
				} else {
					logger.Warn("failed to convert recvbytes value: %s to int64, errmsg: %s", value, err)
				}
			}
		}
	}

	if currentBackend != nil {
		status.Backends = append(status.Backends, *currentBackend)
	}
}

// parseInfoToTendisCacheStatus parses Redis INFO output to TendisCacheStatus
func parseInfoToTendisCacheStatus(info string, status *haprobe.RedisTendisCacheStatus) {
	if info == "" {
		return
	}
	infoMap := parseRedisInfoToMap(info)
	t := reflect.TypeOf(*status)
	v := reflect.ValueOf(status).Elem()
	setFieldByReflection(v, t, infoMap)

	status.Keyspace = parseKeyspace(infoMap)
}

// parseInfoToTendisSSDStatus parses Redis INFO output to TendisSSDStatus
func parseInfoToTendisSSDStatus(info string, status *haprobe.RedisTendisSSDStatus) {
	if info == "" {
		return
	}
	infoMap := parseRedisInfoToMap(info)
	t := reflect.TypeOf(*status)
	v := reflect.ValueOf(status).Elem()
	setFieldByReflection(v, t, infoMap)

	status.SlaveStates = parseSlaveStates(infoMap)
}

// parseInfoToTendisPlusStatus parses Redis INFO output to TendisPlusStatus
func parseInfoToTendisPlusStatus(info string, status *haprobe.RedisTendisPlusStatus) {
	if info == "" {
		return
	}
	infoMap := parseRedisInfoToMap(info)
	t := reflect.TypeOf(*status)
	v := reflect.ValueOf(status).Elem()
	setFieldByReflection(v, t, infoMap)

	status.SlaveStates = parseSlaveStates(infoMap)

	status.RocksDBSlaveStates = parseRocksDBSlaveStates(infoMap)

	status.Keyspace = parseKeyspace(infoMap)
}

// parseInfoToRedisClusterStatus parses Redis INFO output to RedisClusterStatus
func parseInfoToRedisClusterStatus(info string, status *haprobe.RedisClusterStatus) {
	if info == "" {
		return
	}
	infoMap := parseRedisInfoToMap(info)
	t := reflect.TypeOf(*status)
	v := reflect.ValueOf(status).Elem()
	setFieldByReflection(v, t, infoMap)

	status.SlaveStates = parseClusterSlaveStates(infoMap)

	status.Keyspace = parseKeyspace(infoMap)
}

func parseRedisInfoToMap(info string) map[string]string {
	result := make(map[string]string)
	lines := strings.Split(info, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.SplitN(line, ":", 2)
		if len(parts) == 2 {
			result[strings.ToLower(strings.TrimSpace(parts[0]))] = strings.TrimSpace(parts[1])
		}
	}
	return result
}

func setFieldByReflection(v reflect.Value, t reflect.Type, infoMap map[string]string) {
	for i := 0; i < t.NumField(); i++ {
		field := t.Field(i)
		fieldValue := v.Field(i)

		if field.Type.Kind() == reflect.Struct {
			setFieldByReflection(fieldValue, field.Type, infoMap)
			continue
		}

		jTag := field.Tag.Get("json")
		if jTag == "" {
			logger.Debug("the field: %s has no tag", field.Name)
			continue
		}

		jTagName := strings.Split(jTag, ",")[0]

		statusValue, exists := infoMap[strings.ToLower(jTagName)]
		if !exists {
			logger.Debug("missed the key: %s in the info", jTagName)
			continue
		}

		if !fieldValue.CanSet() {
			logger.Debug("can not set the key: %s", jTagName)
			continue
		}

		switch field.Type.Kind() {
		case reflect.String:
			fieldValue.SetString(statusValue)

		case reflect.Int, reflect.Int64:
			sVal, err := converter.ToInt64(statusValue)
			if err != nil {
				logger.Warn("can not convert the value: %s to int64, errmsg: %s", statusValue, err)
				continue
			}
			fieldValue.SetInt(sVal)

		case reflect.Uint, reflect.Uint64:
			sVal, err := converter.ToUint64(statusValue)
			if err != nil {
				logger.Warn("can not convert the value: %s to uint64, errmsg: %s", statusValue, err)
				continue
			}
			fieldValue.SetUint(sVal)

		case reflect.Float32, reflect.Float64:
			sVal, err := converter.ToFloat64(statusValue)
			if err != nil {
				logger.Warn("can not convert the value: %s to float64, errmsg: %s", statusValue, err)
				continue
			}
			fieldValue.SetFloat(sVal)

		default:
			logger.Warn("unsupported the type: %s, field: %s", field.Type.Kind(), field.Name)
		}
	}
}

// parseKeyspace parses db0, db1, ... keys from INFO output
func parseKeyspace(infoMap map[string]string) []haprobe.RedisDBKeyspace {
	var keyspaces []haprobe.RedisDBKeyspace

	for key, value := range infoMap {
		if !strings.HasPrefix(key, "db") {
			continue
		}

		dbNumStr := strings.TrimPrefix(key, "db")
		dbNum, err := converter.ToInt(dbNumStr)
		if err != nil {
			continue
		}

		ks := haprobe.RedisDBKeyspace{DB: dbNum}

		parts := strings.Split(value, ",")
		for _, part := range parts {
			kv := strings.SplitN(part, "=", 2)
			if len(kv) != 2 {
				logger.Warn("invalid keyspace format, expected key=value but got: %s", part)
				continue
			}
			k := strings.ToLower(strings.TrimSpace(kv[0]))
			v := strings.TrimSpace(kv[1])

			switch k {
			case "keys":
				if n, err := converter.ToInt64(v); err == nil {
					ks.Keys = n
				} else {
					logger.Warn("failed to convert keyspace keys value: %s to int64, errmsg: %s", v, err)
				}
			case "expires":
				if n, err := converter.ToInt64(v); err == nil {
					ks.Expires = n
				} else {
					logger.Warn("failed to convert keyspace expires value: %s to int64, errmsg: %s", v, err)
				}
			case "avg_ttl":
				if n, err := converter.ToInt64(v); err == nil {
					ks.AvgTTL = n
				} else {
					logger.Warn("failed to convert keyspace avg_ttl value: %s to int64, errmsg: %s", v, err)
				}
			}
		}

		keyspaces = append(keyspaces, ks)
	}

	return keyspaces
}

// parseSlaveStates parses slave0, slave1, ... keys from INFO output (simple format)
func parseSlaveStates(infoMap map[string]string) []haprobe.RedisSlaveState {
	var slaves []haprobe.RedisSlaveState

	for key, value := range infoMap {
		if !strings.HasPrefix(key, "slave") {
			continue
		}

		idStr := strings.TrimPrefix(key, "slave")
		id, err := converter.ToInt(idStr)
		if err != nil {
			continue
		}

		slave := haprobe.RedisSlaveState{ID: id}

		parts := strings.Split(value, ",")
		for _, part := range parts {
			kv := strings.SplitN(part, "=", 2)
			if len(kv) != 2 {
				logger.Warn("invalid slave state format, expected key=value but got: %s", part)
				continue
			}
			k := strings.ToLower(strings.TrimSpace(kv[0]))
			v := strings.TrimSpace(kv[1])

			if k == "state" {
				slave.State = v
			}
		}

		slaves = append(slaves, slave)
	}

	return slaves
}

// parseClusterSlaveStates parses slave0, slave1, ... keys from INFO output (full format)
func parseClusterSlaveStates(infoMap map[string]string) []haprobe.RedisClusterSlaveState {
	var slaves []haprobe.RedisClusterSlaveState

	for key, value := range infoMap {
		if !strings.HasPrefix(key, "slave") {
			continue
		}

		idStr := strings.TrimPrefix(key, "slave")
		id, err := converter.ToInt(idStr)
		if err != nil {
			continue
		}

		slave := haprobe.RedisClusterSlaveState{ID: id}

		parts := strings.Split(value, ",")
		for _, part := range parts {
			kv := strings.SplitN(part, "=", 2)
			if len(kv) != 2 {
				logger.Warn("invalid cluster slave state format, expected key=value but got: %s", part)
				continue
			}
			k := strings.ToLower(strings.TrimSpace(kv[0]))
			v := strings.TrimSpace(kv[1])

			switch k {
			case "ip":
				slave.IP = v
			case "port":
				if n, err := converter.ToInt(v); err == nil {
					slave.Port = n
				} else {
					logger.Warn("failed to convert slave port value: %s to int, errmsg: %s", v, err)
				}
			case "state":
				slave.State = v
			case "offset":
				if n, err := converter.ToInt64(v); err == nil {
					slave.Offset = n
				} else {
					logger.Warn("failed to convert slave offset value: %s to int64, errmsg: %s", v, err)
				}
			case "lag":
				if n, err := converter.ToInt64(v); err == nil {
					slave.Lag = n
				} else {
					logger.Warn("failed to convert slave lag value: %s to int64, errmsg: %s", v, err)
				}
			}
		}

		slaves = append(slaves, slave)
	}

	return slaves
}

// parseRocksDBSlaveStates parses RocksDB slave states for TendisPlus
func parseRocksDBSlaveStates(infoMap map[string]string) []haprobe.RedisTendisPlusRocksDBSlaveState {
	var states []haprobe.RedisTendisPlusRocksDBSlaveState

	for key, value := range infoMap {
		if !strings.HasPrefix(key, "rocksdb") || !strings.Contains(key, "_slave") {
			continue
		}

		parts := strings.Split(key, "_slave")
		if len(parts) != 2 {
			continue
		}

		rocksDBIDStr := strings.TrimPrefix(parts[0], "rocksdb")
		rocksDBID, err := converter.ToInt(rocksDBIDStr)
		if err != nil {
			continue
		}

		slaveID, err := converter.ToInt(parts[1])
		if err != nil {
			continue
		}

		state := haprobe.RedisTendisPlusRocksDBSlaveState{
			RocksDBID: rocksDBID,
			SlaveID:   slaveID,
		}

		valueParts := strings.Split(value, ",")
		for _, part := range valueParts {
			kv := strings.SplitN(part, "=", 2)
			if len(kv) != 2 {
				logger.Warn("invalid rocksdb slave state format, expected key=value but got: %s", part)
				continue
			}
			if strings.EqualFold(strings.TrimSpace(kv[0]), "state") {
				state.State = strings.TrimSpace(kv[1])
			}
		}

		states = append(states, state)
	}

	return states
}
