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

package redis

import (
	"reflect"
	"strconv"
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

func parseInfoToTwemproxyStatus(info string, status *haprobe.RedisTwemproxyStatus) {
	// TODO
}

func parseInfoToPredixyStatus(info string, status *haprobe.RedisPredixyStatus) {
	// TODO
}

func parsePredixyServersInfo(info string, status *haprobe.RedisPredixyStatus) {
	// TODO
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

func parseInfoToTendisSSDStatus(info string, status *haprobe.RedisTendisSSDStatus) {
	// TODO
}

func parseInfoToTendisPlusStatus(info string, status *haprobe.RedisTendisPlusStatus) {
	// TODO
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

// parseClusterSlaveStates parses slave0, slave1, ... keys from INFO output (full format)
func parseClusterSlaveStates(infoMap map[string]string) []haprobe.RedisClusterSlaveState {
	var slaves []haprobe.RedisClusterSlaveState

	for key, value := range infoMap {
		if !strings.HasPrefix(key, "slave") {
			continue
		}

		idStr := strings.TrimPrefix(key, "slave")
		id, err := strconv.Atoi(idStr)
		if err != nil {
			continue
		}

		slave := haprobe.RedisClusterSlaveState{ID: id}

		parts := strings.Split(value, ",")
		for _, part := range parts {
			kv := strings.SplitN(part, "=", 2)
			if len(kv) != 2 {
				continue
			}
			k := strings.TrimSpace(kv[0])
			v := strings.TrimSpace(kv[1])

			switch k {
			case "ip":
				slave.IP = v
			case "port":
				if n, err := strconv.Atoi(v); err == nil {
					slave.Port = n
				}
			case "state":
				slave.State = v
			case "offset":
				if n, err := strconv.ParseInt(v, 10, 64); err == nil {
					slave.Offset = n
				}
			case "lag":
				if n, err := strconv.ParseInt(v, 10, 64); err == nil {
					slave.Lag = n
				}
			}
		}

		slaves = append(slaves, slave)
	}

	return slaves
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
		dbNum, err := strconv.Atoi(dbNumStr)
		if err != nil {
			continue
		}

		ks := haprobe.RedisDBKeyspace{DB: dbNum}

		parts := strings.Split(value, ",")
		for _, part := range parts {
			kv := strings.SplitN(part, "=", 2)
			if len(kv) != 2 {
				continue
			}
			k := strings.TrimSpace(kv[0])
			v := strings.TrimSpace(kv[1])

			switch k {
			case "keys":
				if n, err := strconv.ParseInt(v, 10, 64); err == nil {
					ks.Keys = n
				}
			case "expires":
				if n, err := strconv.ParseInt(v, 10, 64); err == nil {
					ks.Expires = n
				}
			case "avg_ttl":
				if n, err := strconv.ParseInt(v, 10, 64); err == nil {
					ks.AvgTTL = n
				}
			}
		}

		keyspaces = append(keyspaces, ks)
	}

	return keyspaces
}
