package mongologparser

import (
	"bytes"
	"encoding/json"
	"strconv"
	"strings"
	"time"

	log "github.com/sirupsen/logrus"

	"go.mongodb.org/mongo-driver/bson/primitive"
)

// ParseV3Mongolog parses a log line and returns a MongoLogMsg for mongodb version 4.4 - 6.0
func ParseV3Mongolog(data []byte) (*MongoLogMsg, []byte, error) {
	var row MongoLogMsg
	d := json.NewDecoder(bytes.NewReader(data))
	d.UseNumber()
	err := d.Decode(&row)
	// err := json.Unmarshal(data, &row)
	if err != nil {
		row.Msg = string(data)
		return &row, nil, err
	}
	row.ParseOk = 1
	if row.T != nil {
		row.DateTime = row.T.DateTime
		row.T = nil
	}

	if row.Attr == nil {
		return &row, nil, err
	}

	var attrStr []byte
	attrStr, _ = json.Marshal(row.Attr)

	switch row.Attr.(type) {
	case map[string]interface{}:
		if row.Id == LogTypeSlowlog {
			attr := row.Attr.(map[string]interface{})
			// 将不确定的字段转换为string: command
			// durationMillis 保持原值，兼容 attr.durationMillis 查询
			for k, v := range attr {
				if k == "durationMillis" {
					continue
				}
				switch v.(type) {
				case string, float64, bool, int:
					continue
				default:
					datav, _ := json.Marshal(v)
					attr[k] = string(datav)
				}
			}

			row.Attr = attr
		} else {
			attr := row.Attr.(map[string]interface{})
			// 将不确定的字段转换为string: command
			for k, v := range attr {
				if k == "durationMillis" {
					continue
				}
				switch v.(type) {
				case string, float64, bool, int:
					continue
				default:
					datav, _ := json.Marshal(v)
					attr[k] = string(datav)
				}
			}
			row.Attr = attr
		}
		row.copyDurationMillisFromAttr()

	default:
		log.Warnf("unmarshal Attr failed: unknown type %T", row.Attr)
	}

	return &row, attrStr, err
}

func (m *MongoLogMsg) copyDurationMillisFromAttr() {
	if m == nil || m.Attr == nil {
		return
	}
	switch attr := m.Attr.(type) {
	case map[string]interface{}:
		v, ok := attr["durationMillis"]
		if !ok || v == nil {
			return
		}
		n, ok := parseDurationMillis(v)
		if ok {
			m.DurationMillis = n
		}
	case *SlowlogAttr:
		if attr != nil && attr.DurationMillis != 0 {
			m.DurationMillis = attr.DurationMillis
		}
	case SlowlogAttr:
		if attr.DurationMillis != 0 {
			m.DurationMillis = attr.DurationMillis
		}
	}
}

func parseDurationMillis(v interface{}) (int64, bool) {
	switch n := v.(type) {
	case int:
		return int64(n), true
	case int32:
		return int64(n), true
	case int64:
		return n, true
	case float64:
		return int64(n), true
	case json.Number:
		i, err := n.Int64()
		if err != nil {
			return 0, false
		}
		return i, true
	case string:
		n = strings.TrimSpace(strings.TrimSuffix(n, "ms"))
		if n == "" {
			return 0, false
		}
		i, err := strconv.ParseInt(n, 10, 64)
		if err != nil {
			return 0, false
		}
		return i, true
	default:
		return 0, false
	}
}

// MongoLogMsg is a struct to hold the parsed log message
// mongo 4.4+ 时间格式 "t":{"$date":"2024-03-28T09:35:42.647+08:00"}

type MongoLogMsg struct {
	OriginLine []byte `json:"-"`
	T          *struct {
		DateTime primitive.DateTime `json:"$date"`
	} `json:"t,omitempty"` // timestamp
	DateTime       primitive.DateTime `json:"dt"`
	S              string             `json:"s"` // severity
	C              string             `json:"c"` // component
	Id             int64              `json:"id"`
	Ctx            string             `json:"ctx"`
	Msg            string             `json:"msg"`
	Attr           interface{}        `json:"attr,omitempty"`
	DurationMillis int64              `json:"durationMillis,omitempty"`
	Line           struct {
		Num      int       `json:"num"`
		OffSet   int64     `json:"offset"`
		TimeDiff int64     `json:"timeDiff"` // ms Line.Time - dt (ms)
		Time     time.Time `json:"t"`
	} `json:"line,omitempty"`
	ParseOk int `json:"ok"`
}

// SlowlogAttr slowlog attr
type SlowlogAttr struct {
	Type            string      `json:"type"`
	Ns              string      `json:"ns"`
	AppName         *string     `json:"appName,omitempty"`
	Command         interface{} `json:"command,omitempty"`
	NShards         *int        `json:"nShards,omitempty"`
	CursorExhausted *bool       `json:"cursorExhausted,omitempty"`
	KeysExamined    *int        `json:"keysExamined,omitempty"`
	DocsExamined    *int        `json:"docsExamined,omitempty"`
	WriteConflicts  *int        `json:"writeConflicts,omitempty"`
	Cursorid        *string     `json:"cursorid,omitempty"`
	KeyUpdates      *int        `json:"keyUpdates,omitempty"`
	NDeleted        *int        `json:"ndeleted,omitempty"`
	PlanSummary     *string     `json:"planSummary,omitempty"`
	NumYields       *int        `json:"numYields,omitempty"`
	Nreturned       *int        `json:"nreturned,omitempty"`
	Reslen          int         `json:"reslen"`
	Protocol        string      `json:"protocol,omitempty"`
	Locks           string      `json:"locks,omitempty"`
	Storage         *string     `json:"storage,omitempty"`
	DurationMillis  int64       `json:"durationMillis"`
}

// Component
/*
CONTROL:
NETWORK:
ACCESS:
COMMAND, QUERY, WRITE,
*/

const LogTypeSlowlog = 51803
const LogTypeEndId = 22944

// SetProp set prop
func (attr *SlowlogAttr) SetProp(key string, value string) (bool, error) {
	var err error
	var v int

	switch key {
	case "ms", "durationMillis":
		value = strings.TrimSuffix(value, "ms")
		attr.DurationMillis, err = strconv.ParseInt(value, 10, 64)
	case "numYields":
		v, err = strconv.Atoi(value)
		attr.NumYields = &v
	case "reslen":
		attr.Reslen, err = strconv.Atoi(value)
	case "nShards":
		v, err = strconv.Atoi(value)
		attr.NShards = &v
	case "cursorExhausted":
		var b = value == "true"
		attr.CursorExhausted = &b
	case "nreturned":
		v, err = strconv.Atoi(value)
		attr.Nreturned = &v
	case "keysExamined":
		v, err = strconv.Atoi(value)
		attr.KeysExamined = &v
	case "docsExamined":
		v, err = strconv.Atoi(value)
		attr.DocsExamined = &v
	case "writeConflicts":
		v, err = strconv.Atoi(value)
		attr.WriteConflicts = &v
	case "keyUpdates":
		v, err = strconv.Atoi(value)
		attr.KeyUpdates = &v
	case "ndeleted":
		v, err = strconv.Atoi(value)
		attr.NDeleted = &v
	case "cursorid":
		s := value
		attr.Cursorid = &s
	case "ns":
		attr.Ns = value
	case "type":
		attr.Type = value
	case "appName":
		var s = value
		attr.AppName = &s
	case "command":
		attr.Command = strings.TrimSpace(value)
	case "protocol":
		attr.Protocol = value
	case "planSummary":
		var s = strings.TrimSpace(value)
		attr.PlanSummary = &s
	case "locks":
		attr.Locks = value
	case "storage":
		var s = value
		attr.Storage = &s
	default:
		return false, nil
	}

	if err != nil {
		return false, err
	}
	return true, nil

}

// getField
func getField(line []byte, pos [2]int) string {
	return string(line[pos[0]:pos[1]])
}

const timeStr = "2006-01-02T15:04:05.000-0700"
const timeStrV24 = "Mon Jan 2 15:04:05.000"
