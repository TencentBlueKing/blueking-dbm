// Package keylifecycle TODO
package keylifecycle

import (
	"fmt"
	"strconv"
	"strings"

	"dbm-services/redis/db-tools/dbmon/models/myredis"
	"dbm-services/redis/db-tools/dbmon/mylog"
)

// Instance TODO
type Instance struct {
	IP       string `json:"ip"`
	Port     int    `json:"port"`
	Addr     string `json:"addr"`
	Password string `json:"passwords"`
	App      string `json:"app"`
	Domain   string `json:"domain"`
	Role     string `json:"role"`
	Version  string `json:"version"`

	Cli *myredis.RedisClient `json:"-"`
}

func getStatToolParams(keys int64) (int64, int, int, int, int) {
	step, slptime, sample, confidence, adjfactor := 1, 50, 3000, 400, 100

	if keys >= 100000000 {
		step, slptime, sample, confidence, adjfactor = 50, 10, 12000, 8000, 3000
	} else if keys >= 50000000 {
		step, slptime, sample, confidence, adjfactor = 50, 10, 10000, 5000, 2200
	} else if keys >= 10000000 {
		step, slptime, sample, confidence, adjfactor = 50, 10, 10000, 5000, 2000
	} else if keys >= 100000 {
		step, slptime, sample, confidence, adjfactor = 50, 0, 10000, 4000, 1200
	} else if keys >= 10000 {
		step, slptime, sample, confidence, adjfactor = 50, 0, 10000, 3000, 1000
	}
	mylog.Logger.Info(fmt.Sprintf("get tools params for %d:%d,%d,%d,%d,%d",
		keys, step, slptime, sample, confidence, adjfactor))
	return int64(step), slptime, sample, confidence, adjfactor
}

const (
	// DEFATUL_VERSION_FACTOR TODO
	DEFATUL_VERSION_FACTOR = 1000000
	// DEFAULT_VERSION_NUM TODO
	DEFAULT_VERSION_NUM = 9999999
	// VERSION_TENDIS_SSD_TAG TODO
	VERSION_TENDIS_SSD_TAG = "TRedis"
	// VERSION_TENDIS_DELIMITER TODO
	VERSION_TENDIS_DELIMITER = "-"
)

// tendisSSDVersion2Int 转化ssd版本成数字
func tendisSSDVersion2Int(v string) (int, int) {
	if strings.Contains(v, VERSION_TENDIS_SSD_TAG) {
		vps := strings.Split(v, VERSION_TENDIS_DELIMITER)
		if len(vps) == 3 {
			return dotString2Int(vps[0]), dotString2Int(vps[2])
		}
	}
	return DEFAULT_VERSION_NUM, DEFAULT_VERSION_NUM
}

func dotString2Int(dt string) int {
	dt = strings.TrimSpace(dt)
	var vnum, step, factor int
	if strings.HasPrefix(dt, "v") {
		dt = dt[1:]
	}
	factor = DEFATUL_VERSION_FACTOR
	step = 100
	parts := strings.Split(dt, ".")
	for _, v := range parts {
		vint, err := strconv.Atoi(v)
		if err != nil {
			return DEFAULT_VERSION_NUM
		}
		vnum += vint * factor
		factor = factor / step
	}
	return vnum
}

// KafkaMsg old msg struct.
// type KafkaMsg struct {
// 	Name   string `json:"name"`
// 	From   string `json:"form"`
// 	XMLRow struct {
// 		XMLField map[string]interface{} `json:"xml_field"`
// 	} `json:"xml_row"`
// }

// func (t *Task) sendFileToKafka(file string, dict map[string]interface{}) error {
// 	fh, err := os.Open(file)
// 	if err != nil {
// 		return err
// 	}

// 	dict["content"], err = ioutil.ReadAll(fh)
// 	if err != nil {
// 		return err
// 	}

// 	kafkaMsg := KafkaMsg{Name: t.conf.KafaTopic, From: "K8S",
// 		XMLRow: struct {
// 			XMLField map[string]interface{} "json:\"xml_field\""
// 		}{},
// 	}
// 	kafkaMsg.XMLRow.XMLField = dict
// 	msgJSON, _ := json.Marshal(kafkaMsg)

// 	fileName := "/tmp/kafka.txt"
// 	if err = ioutil.WriteFile(fileName, msgJSON, os.FileMode(0660)); err != nil {
// 		return err
// 	}

// 	return kafka.KafkaClient(t.kafkaConf.KafkaHosts, t.conf.KafaTopic,
// 		t.kafkaConf.KafkaUser, t.kafkaConf.KafaPass, fileName)
// }
