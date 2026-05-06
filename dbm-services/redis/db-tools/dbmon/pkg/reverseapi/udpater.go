package reverseapi

import (
	"bufio"
	reversecommonapi "dbm-services/common/reverseapi/apis/common"
	"dbm-services/common/reverseapi/pkg/core"
	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"fmt"
	"io"
	"math/rand"
	"os"
	"sync"
	"time"
)

var globReverseJobOnce *ReverseJob
var ReverseJobOnce sync.Once

type ReverseJob struct {
	Conf *config.Configuration `json:"conf"`
}

// GetReverseJob 反响接口调用的配置定期更新
func GetReverseJob(conf *config.Configuration) *ReverseJob {
	ReverseJobOnce.Do(func() {
		globReverseJobOnce = &ReverseJob{
			Conf: conf,
		}
	})
	return globReverseJobOnce
}

func (job *ReverseJob) Run() {
	rand.Seed(time.Now().UnixNano()) // 初始化随机数种子
	r := rand.Intn(10)               // 生成0-9的随机整数
	sleepDuration := time.Duration(r) * time.Second
	time.Sleep(sleepDuration)
	reverseConfig := common.GetResrveAPIConfig()

	f, err := os.OpenFile(reverseConfig, os.O_CREATE|os.O_RDWR,
		0777,
	)
	if err != nil {
		mylog.Logger.Error(fmt.Sprintf("open reverse config file failed %s:%+v", reverseConfig, err))
		return
	}
	defer f.Close()

	var addrs []string
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		addrs = append(addrs, scanner.Text()) // 每行作为字符串存入切片
	}
	if len(addrs) == 0 {
		return
	}
	mylog.Logger.Debug(fmt.Sprintf("begin update reverse nginx addrs with old:%+v", addrs))

	apiCore, err := core.NewCoreWithAddr(0, addrs, core.DefaultRetryOpts...)
	if err != nil {
		mylog.Logger.Error(fmt.Sprintf("create reverse core:%+v", err))
		return
	}
	Newaddrs, err := reversecommonapi.ListNginxAddrs(apiCore)
	if err != nil {
		mylog.Logger.Error(fmt.Sprintf("list nginx addrs failed %d:%+v", 0, err))
		return
	}
	mylog.Logger.Debug(fmt.Sprintf("list nginx addrs %d:%+v", 0, Newaddrs))
	defer mylog.Logger.Info("done update reverse nginx addrs write addr file")

	// 后置， 防止拉取最新的失败，数据丢失
	if err := f.Truncate(0); err != nil {
		mylog.Logger.Error(fmt.Sprintf("truncate reverse file failed %s:%+v", reverseConfig, err))
		return
	}
	if _, err := f.Seek(0, io.SeekStart); err != nil {
		mylog.Logger.Error(fmt.Sprintf("seek reverse file failed %s:%+v", reverseConfig, err))
		return
	} // 移动到文件开头;err

	for _, addr := range Newaddrs {
		if _, err := f.WriteString(addr + "\n"); err != nil {
			mylog.Logger.Error(fmt.Sprintf("writing %s 2 reverse file %s failed:%+v", addr, reverseConfig, err))
		}
	}
}

func (job *ReverseJob) precheck() {
}
