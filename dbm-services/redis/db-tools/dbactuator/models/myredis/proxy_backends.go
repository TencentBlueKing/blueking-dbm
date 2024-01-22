package myredis

import (
	"context"
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
)

// TwemproxyBackendItem twemproxy backend 项
type TwemproxyBackendItem struct {
	Addr     string `json:"addr"`
	App      string `json:"app"`
	SegStart int    `json:"segStart"`
	SegEnd   int    `json:"segEnd"`
	Weight   int    `json:"weight"`
}

// String 用于打印
func (backend *TwemproxyBackendItem) String() string {
	return fmt.Sprintf("%s %s %d-%d %d",
		backend.Addr, backend.App, backend.SegStart, backend.SegEnd, backend.Weight)
}

// StringWithoutApp 不带app信息
func (backend *TwemproxyBackendItem) StringWithoutApp() string {
	return fmt.Sprintf("%s %d-%d %d",
		backend.Addr, backend.SegStart, backend.SegEnd, backend.Weight)
}

// StringWithoutWeight 不带weight信息
func (backend *TwemproxyBackendItem) StringWithoutWeight() string {
	return fmt.Sprintf("%s %s %d-%d",
		backend.Addr, backend.App, backend.SegStart, backend.SegEnd)
}

// DecodeTwemproxyBackends 解析twmproxy backends,如:
// a.a.a.a:30006 myapp 0-2624 1
// a.a.a.a:30007 myapp 2625-5249 1
// b.b.b.b:30010 myapp 5250-7874 1
// c.c.c.c:30000 myapp 7875-10499 1
func DecodeTwemproxyBackends(backendsStr string) (
	backendList []TwemproxyBackendItem,
	backendAddrMap map[string]TwemproxyBackendItem,
	err error,
) {
	backendAddrMap = make(map[string]TwemproxyBackendItem)
	backendsStr = strings.TrimSpace(backendsStr)
	lines := strings.Split(backendsStr, "\n")
	for _, line01 := range lines {
		line01 = strings.TrimSpace(line01)
		list01 := strings.Fields(line01)
		if len(list01) != 4 {
			err = fmt.Errorf("twemproxy backend:%s format not correct", line01)
			mylog.Logger.Error(err.Error())
			return
		}
		backendItem := TwemproxyBackendItem{}
		backendItem.Addr = list01[0]
		backendItem.App = list01[1]
		segs := strings.Split(list01[2], "-")
		backendItem.SegStart, err = strconv.Atoi(segs[0])
		if err != nil {
			err = fmt.Errorf("twemproxy backend:%s not corret,segStart strconv.Atoi fail,err:%s", line01, err)
			mylog.Logger.Error(err.Error())
			return
		}
		backendItem.SegEnd, err = strconv.Atoi(segs[1])
		if err != nil {
			err = fmt.Errorf("twemproxy backend:%s not corret,segEnd strconv.Atoi fail,err:%s", line01, err)
			mylog.Logger.Error(err.Error())
			return
		}
		backendItem.Weight, _ = strconv.Atoi(list01[3])
		backendList = append(backendList, backendItem)
		backendAddrMap[backendItem.Addr] = backendItem
	}
	return
}

// GetTwemproxyBackendsRaw 获取twemproxy backends原始内容
func GetTwemproxyBackendsRaw(ip string, port int) (ret string, err error) {
	addr := fmt.Sprintf("%s:%d", ip, port+1000)
	cmd := "get nosqlproxy servers"
	ret, err = util.NetCatTcpClient(addr, cmd)
	if err != nil {
		err = fmt.Errorf("NetCatTcpClient fail,err:%v,addr:%s,command:%s", err, addr, cmd)
		mylog.Logger.Error(err.Error())
		return "", err
	}
	return
}

// GetTwemproxyBackendsDecoded 获取twemproxy backends解析后的内容
func GetTwemproxyBackendsDecoded(ip string, port int) (
	backendList []TwemproxyBackendItem,
	backendAddrMap map[string]TwemproxyBackendItem,
	err error,
) {
	backendsRaw, err := GetTwemproxyBackendsRaw(ip, port)
	if err != nil {
		return nil, nil, err
	}
	return DecodeTwemproxyBackends(backendsRaw)
}

// PredixyInfoServer predixy执行info server结果
type PredixyInfoServer struct {
	Server        string `json:"Server"`
	Role          string `json:"Role"`
	Group         string `json:"Group"`
	DC            string `json:"DC"`
	CurrentIsFail int    `json:"CurrentIsFail"`
	Connections   int    `json:"Connections"`
	Connect       int    `json:"Connect"`
	Requests      uint64 `json:"Requests"`
	Responses     uint64 `json:"Responses"`
	SendBytes     uint64 `json:"SendBytes"`
	RecvBytes     uint64 `json:"RecvBytes"`
}

// GetPredixyInfoServersRaw 获取predixy info server原始内容 s
func GetPredixyInfoServersRaw(ip string, port int, password string) (svrsinfo string, err error) {
	predixyAddr := fmt.Sprintf("%s:%d", ip, port)
	cli01, err := NewRedisClientWithTimeout(predixyAddr, password, 0,
		consts.TendisTypeRedisInstance, 5*time.Second)
	if err != nil {
		return
	}
	defer cli01.Close()

	svrsinfo, err = cli01.InstanceClient.Info(context.TODO(), "servers").Result()
	if err != nil {
		err = fmt.Errorf("PredixyInfoServers execute cmd:'info servers' fail,err:%v", err)
		mylog.Logger.Error(err.Error())
		return
	}
	return
}

// GetPredixyInfoServersDecoded 获取predixy info server结果(已解析)
func GetPredixyInfoServersDecoded(ip string, port int, password string) (rets []*PredixyInfoServer, err error) {
	svrsinfo, err := GetPredixyInfoServersRaw(ip, port, password)
	if err != nil {
		return
	}
	infoList := strings.Split(svrsinfo, "\n")
	item01 := &PredixyInfoServer{}
	for _, infoItem := range infoList {
		infoItem = strings.TrimSpace(infoItem)
		if strings.HasPrefix(infoItem, "#") {
			continue
		}
		if len(infoItem) == 0 {
			if item01.Server != "" {
				rets = append(rets, item01)
				item01 = &PredixyInfoServer{}
			}
			continue
		}
		list01 := strings.SplitN(infoItem, ":", 2)
		if len(list01) < 2 {
			continue
		}
		if strings.HasPrefix(list01[0], "Server") {
			item01.Server = list01[1]
		} else if strings.HasPrefix(list01[0], "Role") {
			item01.Role = list01[1]
		} else if strings.HasPrefix(list01[0], "Group") {
			item01.Group = list01[1]
		} else if strings.HasPrefix(list01[0], "DC") {
			item01.DC = list01[1]
		} else if strings.HasPrefix(list01[0], "CurrentIsFail") {
			item01.CurrentIsFail, _ = strconv.Atoi(list01[1])
		} else if strings.HasPrefix(list01[0], "Connections") {
			item01.Connections, _ = strconv.Atoi(list01[1])
		} else if strings.HasPrefix(list01[0], "Connect") {
			item01.Connect, _ = strconv.Atoi(list01[1])
		} else if strings.HasPrefix(list01[0], "Requests") {
			item01.Requests, _ = strconv.ParseUint(list01[1], 10, 64)
		} else if strings.HasPrefix(list01[0], "Responses") {
			item01.Responses, _ = strconv.ParseUint(list01[1], 10, 64)
		} else if strings.HasPrefix(list01[0], "SendBytes") {
			item01.SendBytes, _ = strconv.ParseUint(list01[1], 10, 64)
		} else if strings.HasPrefix(list01[0], "RecvBytes") {
			item01.RecvBytes, _ = strconv.ParseUint(list01[1], 10, 64)
		}
	}
	return rets, nil
}
