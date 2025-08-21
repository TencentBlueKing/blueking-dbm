// Package util here mybe something
package util

import (
	"bufio"
	"crypto/md5"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"math/rand"
	"net"
	"sort"
	"strconv"
	"strings"
	"time"
)

// NCInstance NCInstance
var NCInstance *NetCat

// NetCat use tcp for nc
type NetCat struct {
	AdminAddr   string
	ReadTimeOut time.Duration
	Nc          net.Conn
}

func init() {
	NCInstance = &NetCat{}
	rand.Seed(time.Now().UnixNano())
}

// GetTwemProxyBackendsMd5Sum 获取MD5 sum
func GetTwemProxyBackendsMd5Sum(addr string) (string, error) {
	pinfo := strings.Split(addr, ":")
	port, _ := strconv.Atoi(pinfo[1])
	segsMap, err := GetTwemproxyBackends(pinfo[0], port)
	if err != nil {
		return "errFailed", err
	}
	segList := []string{}
	for addr, seg := range segsMap {
		segList = append(segList, fmt.Sprintf("%s|%s", addr, seg))
	}
	sort.Slice(segList, func(i, j int) bool {
		return segList[i] > segList[j]
	})

	data, _ := json.Marshal(segList)
	md5er := md5.New()
	md5er.Write(data)
	hash2 := md5er.Sum(nil)
	return fmt.Sprintf("%s||%x", addr, hex.EncodeToString(hash2)), nil
}

// DoSwitchTwemproxyBackends "change nosqlproxy $mt:$mp $st:$sp"
func DoSwitchTwemproxyBackends(ip string, port int, from, to string) (rst string, err error) {
	addr := fmt.Sprintf("%s:%d", ip, port+1000)
	for range 10 {
		var nc net.Conn
		nc, err = net.DialTimeout("tcp", addr, time.Second*10)
		if err != nil {
			fmt.Printf("dail with proxy:%s:%d failed:+%v\n", ip, port, err)
			continue
		}
		//server xxxxx:30000 xxxx:30000 already exits in server pool nosqlproxy
		//cannot find svr xxxx:30000 in server pool nosqlproxy
		//change 1 banckends from ' xxxx:30000 ' to  ' xxxx:30000 ' success.
		_, err = nc.Write([]byte(fmt.Sprintf("change nosqlproxy %s %s", from, to)))
		if err != nil {
			fmt.Printf("write changeInfo 2 proxy:%s:%d failed:+%v\n", ip, port, err)
			continue
		}
		rst, err = bufio.NewReader(nc).ReadString('\n')
		if strings.Contains(rst, "success") || strings.Contains(rst, "in server pool nosqlproxy") {
			fmt.Printf("do switch twemproxy with result [%s:%d]:%s:%+v\n", ip, port, rst, err)
			break
		}
	}
	return
}

// GetTwemproxyBackends get nosqlproxy servers
func GetTwemproxyBackends(ip string, port int) (segs map[string]string, err error) {
	addr := fmt.Sprintf("%s:%d", ip, port+1000)
	nc, err := net.DialTimeout("tcp", addr, time.Second*10)
	if err != nil {
		return nil, err
	}
	if segs, err = GetSegDetails(nc); err != nil {
		return nil, err
	}
	return segs, nil
}

// GetSegDetails echo stats |nc twempip port
func GetSegDetails(nc net.Conn) (map[string]string, error) {
	_, err := nc.Write([]byte("get nosqlproxy servers"))
	if err != nil {
		return nil, err
	}
	reader := bufio.NewReader(nc)
	segs := make(map[string]string)
	for {
		// rep, _, err := reader.ReadLine()
		line, _, err := reader.ReadLine()
		if err != nil {
			if err == io.EOF {
				break
			}
			return nil, err
		}
		strws := strings.Split(string(line), " ")
		if len(strws) == 4 {
			segs[strws[2]] = strws[0]
		}
	}
	return segs, nil
}
