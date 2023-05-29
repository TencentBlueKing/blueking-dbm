package agent

import (
	"dbm-services/common/dbha/ha-module/log"
	"fmt"
	"net"
	"strconv"
	"sync"
	"time"
)

// GMConnection TODO
type GMConnection struct {
	Ip            string
	Port          int
	NetConnection net.Conn
	IsConnection  bool
	LastFetchTime time.Time
	IsClose       bool
	Mutex         sync.Mutex
}

// HEADER TODO
const HEADER string = "HEADER"

// Init init gm connect
func (gm *GMConnection) Init() error {
	address := gm.Ip + ":" + strconv.Itoa(gm.Port)
	conn, err := net.Dial("tcp", address)
	if err != nil {
		log.Logger.Errorf("gm connection init failed. address:%s, err:%s", address, err.Error())
		return err
	}
	gm.NetConnection = conn
	gm.IsConnection = true
	return nil
}

// ReportInstance report instance detect info
func (gm *GMConnection) ReportInstance(dbType string, jsonInfo []byte) error {
	var writeBuf string
	writeBuf += HEADER
	writeBuf += "\r\n"
	writeBuf += dbType
	writeBuf += "\r\n"
	writeBuf += strconv.Itoa(len(jsonInfo))
	writeBuf += "\r\n"
	writeBuf += string(jsonInfo)
	n, err := gm.NetConnection.Write([]byte(writeBuf))
	if err != nil {
		log.Logger.Error("GMConf write failed. gm ip:", gm.Ip, " port:", gm.Port, " err:", err.Error())
		return err
	}
	if n != len(writeBuf) {
		err = fmt.Errorf("repoter GMConf length not equal, buf size:%d,real send buf size:%d", len(writeBuf), n)
		log.Logger.Errorf(err.Error())
		return err
	}
	readBuf := make([]byte, 2)
	n, err = gm.NetConnection.Read(readBuf)
	if err != nil {
		log.Logger.Error("GMConf read failed. gm ip:", gm.Ip, " port:", gm.Port, " err:", err.Error())
		return err
	}
	if n != 2 || string(readBuf) != "OK" {
		err = fmt.Errorf("GMConf read failed, return:%s, expect: OK", string(readBuf))
		log.Logger.Errorf(err.Error())
		return err
	}
	return nil
}
