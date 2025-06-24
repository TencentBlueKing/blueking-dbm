package agent

import (
	"fmt"
	"net"
	"strconv"
	"sync"
	"time"

	"dbm-services/common/dbha/ha-module/log"
)

// GMConnection TODO
type GMConnection struct {
	Ip            string
	Port          int
	NetConnection net.Conn
	IsConnected   bool
	LastFetchTime time.Time
	IsClose       bool
	Mutex         sync.Mutex
}

// HEADER TODO
const HEADER string = "HEADER"

// Init gm connection
func (gm *GMConnection) Init() error {
	return gm.connect()
}

// init gm connection
func (gm *GMConnection) connect() error {
	if gm.NetConnection != nil {
		gm.NetConnection.Close()
		gm.NetConnection = nil
	}

	address := net.JoinHostPort(gm.Ip, strconv.Itoa(gm.Port))
	dialer := &net.Dialer{
		Timeout:   60 * time.Second,
		KeepAlive: 30 * time.Second,
	}

	conn, err := dialer.Dial("tcp", address)
	if err != nil {
		log.Logger.Errorf("GM connection init failed. address:%s, err:%s", address, err.Error())
		gm.IsConnected = false
		gm.IsClose = true
		return err
	}

	gm.NetConnection = conn
	gm.IsConnected = true
	gm.IsClose = false
	return nil
}

// closeConnection close connection
func (gm *GMConnection) closeConnection() {
	if gm.NetConnection != nil {
		gm.NetConnection.Close()
		gm.NetConnection = nil
	}
	gm.IsConnected = false
	gm.IsClose = true
}

func (gm *GMConnection) SendHeartbeat() error {
	var writeBuf string
	writeBuf += HEADER
	writeBuf += "\r\n"
	writeBuf += "HEARTBEAT"
	writeBuf += "\r\n"
	writeBuf += strconv.Itoa(len("NONE"))
	writeBuf += "\r\n"
	writeBuf += "NONE"
	log.Logger.Debugf("send heartbeat to gm. address:%s", gm.Ip)
	return gm.sendData(writeBuf)
}

func (gm *GMConnection) sendData(writeBuf string) error {
	defer func() {
		_ = gm.NetConnection.SetDeadline(time.Time{})
	}()

	_ = gm.NetConnection.SetDeadline(time.Now().Add(10 * time.Second))
	n, err := gm.NetConnection.Write([]byte(writeBuf))
	if err != nil {
		log.Logger.Error("agent send gm failed. gm ip:", gm.Ip, " port:", gm.Port, " err:", err.Error())
		return err
	}
	if n != len(writeBuf) {
		err = fmt.Errorf("send gm size[%d] not equal buf size[%d]", n, len(writeBuf))
		log.Logger.Errorf(err.Error())
		return err
	}
	readBuf := make([]byte, 2)
	n, err = gm.NetConnection.Read(readBuf)
	if err != nil {
		log.Logger.Error("agent read response failed. gm ip:", gm.Ip, " port:", gm.Port, " err:", err.Error())
		return err
	}
	if n != 2 || string(readBuf) != "OK" {
		err = fmt.Errorf("gm response failed, return:%s, expect: OK", string(readBuf))
		log.Logger.Errorf(err.Error())
		return err
	}
	return nil
}

// ReportInstance agent report instance detect info to gm
func (gm *GMConnection) ReportInstance(detectType string, jsonInfo []byte) error {
	var writeBuf string
	writeBuf += HEADER
	writeBuf += "\r\n"
	writeBuf += detectType
	writeBuf += "\r\n"
	writeBuf += strconv.Itoa(len(jsonInfo))
	writeBuf += "\r\n"
	writeBuf += string(jsonInfo)
	if err := gm.sendData(writeBuf); err != nil {
		gm.closeConnection()
		log.Logger.Warnf("send data failed, try to reconnect")
		err = gm.connect()
		if err != nil {
			log.Logger.Warnf("reconnect failed:%s", err.Error())
			return err
		}
		log.Logger.Infof("reconnect to gm success")
	}

	return gm.sendData(writeBuf)
}
