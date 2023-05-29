package gm

import (
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/dbmodule"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/types"
	"fmt"
	"net"
	"strconv"
	"strings"
	"time"
)

type parseStatus int

const (
	// Idle TODO
	Idle parseStatus = 0
	// ParseHeader TODO
	ParseHeader parseStatus = 1
	// ParseHeaderLF TODO
	ParseHeaderLF parseStatus = 2
	// ParseType TODO
	ParseType parseStatus = 3
	// ParseTypeLF TODO
	ParseTypeLF parseStatus = 4
	// ParseLength TODO
	ParseLength parseStatus = 5
	// ParseLengthLF TODO
	ParseLengthLF parseStatus = 6
	// ParseBody TODO
	ParseBody parseStatus = 7
)

// HEADER TODO
const HEADER string = "HEADER"

// MaxDBTypeLength TODO
const MaxDBTypeLength int = 64

// MaxBodyLength TODO
const MaxBodyLength int = 128 * 1024

// Package TODO
type Package struct {
	Header     string
	DBType     string
	BodyLength int
	Body       []byte
}

// AgentConnection TODO
type AgentConnection struct {
	Ip            string
	Port          int
	NetConnection net.Conn
	Buffer        []byte
	status        parseStatus
	netPackage    Package
	GDMChan       chan DoubleCheckInstanceInfo
	Conf          *config.Config
}

// Init TODO
func (conn *AgentConnection) Init() {
	addr := strings.Split(conn.NetConnection.RemoteAddr().String(), ":")
	conn.Ip = addr[0]
	conn.Port, _ = strconv.Atoi(addr[1])
	conn.status = Idle
}

// Read 用于常见IO
func (conn *AgentConnection) Read() error {
	defer conn.NetConnection.Close()
	for {
		conn.Buffer = make([]byte, 1024)
		n, err := conn.NetConnection.Read(conn.Buffer)
		if err != nil {
			log.Logger.Warnf("client exit.ip:%s port:%d err: %s", conn.Ip, conn.Port, err.Error())
			return err
		}
		err = conn.parse(n)
		if err != nil {
			log.Logger.Errorf("parse net package failed.buf:\n%s\n err:%s", conn.Buffer, err.Error())
			return err
		}
	}
}

// parse 拆包的过程
func (conn *AgentConnection) parse(readLen int) error {
	var err error
	var i int
	for i = 0; i < readLen; i++ {
		switch conn.status {
		case Idle:
			if conn.Buffer[i] != HEADER[0] {
				err = fmt.Errorf("parse failed, status Idle, index %d", i)
				log.Logger.Errorf(err.Error())
				break
			}
			conn.resetPackage()
			conn.netPackage.Header += string(conn.Buffer[i])
			conn.status = ParseHeader
		case ParseHeader:
			if (conn.Buffer[i] == '\r' && conn.netPackage.Header != HEADER) ||
				(conn.Buffer[i] != '\r' && len(conn.netPackage.Header) == len(HEADER)) {
				err = fmt.Errorf("parse failed, status ParseHeader, index %d", i)
				log.Logger.Errorf(err.Error())
				break
			} else if conn.Buffer[i] == '\r' && conn.netPackage.Header == HEADER {
				conn.status = ParseHeaderLF
			} else {
				conn.netPackage.Header += string(conn.Buffer[i])
			}
		case ParseHeaderLF:
			if conn.Buffer[i] != '\n' {
				err = fmt.Errorf("parse failed, status ParseHeaderLF, index %d", i)
				log.Logger.Errorf(err.Error())
				break
			}
			conn.status = ParseType
		case ParseType:
			if conn.Buffer[i] == '\r' {
				_, ok := dbmodule.DBCallbackMap[types.DBType(conn.netPackage.DBType)]
				if !ok {
					err = fmt.Errorf("parse failed, can't find dbtype, status ParseType, index %d", i)
					log.Logger.Errorf(err.Error())
					break
				}
				conn.status = ParseTypeLF
			} else if conn.Buffer[i] != '\r' && len(conn.netPackage.DBType) > MaxDBTypeLength {
				err = fmt.Errorf("parse failed, len(DBType) > MaxDBtypeLen, status ParseType, index %d", i)
				log.Logger.Errorf(err.Error())
				break
			} else {
				conn.netPackage.DBType += string(conn.Buffer[i])
			}
		case ParseTypeLF:
			if conn.Buffer[i] != '\n' {
				err = fmt.Errorf("parse failed, status ParseTypeLF, index %d", i)
				log.Logger.Errorf(err.Error())
				break
			}
			conn.status = ParseLength
		case ParseLength:
			if conn.Buffer[i] == '\r' {
				conn.status = ParseLengthLF
			} else {
				num, err := strconv.Atoi(string(conn.Buffer[i]))
				if err != nil {
					log.Logger.Errorf("parse failed, err:%s", err.Error())
					break
				}
				// int overflow?
				conn.netPackage.BodyLength = conn.netPackage.BodyLength*10 + num
				if conn.netPackage.BodyLength > MaxBodyLength {
					err = fmt.Errorf("parse failed, bodylength > MaxBodyLength, status ParseLength, index %d", i)
					log.Logger.Errorf(err.Error())
					break
				}
			}
		case ParseLengthLF:
			if conn.Buffer[i] != '\n' {
				err = fmt.Errorf("parse failed, status ParseLengthLF, index %d", i)
				log.Logger.Errorf(err.Error())
				break
			}
			conn.status = ParseBody
		case ParseBody:
			conn.netPackage.Body = append(conn.netPackage.Body, conn.Buffer[i])
			if len(conn.netPackage.Body) == conn.netPackage.BodyLength {
				err = conn.processPackage()
				if err != nil {
					log.Logger.Errorf("process net package failed. err:%s", err.Error())
					break
				}

				// unpack success
				// replay ok
				log.Logger.Infof("process net package success. Type:%s, Body:%s",
					conn.netPackage.DBType, conn.netPackage.Body)
				n, err := conn.NetConnection.Write([]byte("OK"))
				if err != nil {
					log.Logger.Error("write failed. agent ip:", conn.Ip, " port:", conn.Port)
					return err
				}
				if n != len("OK") {
					err = fmt.Errorf(
						"repoter GMConf length not equal, buf size:%d,real send buf size:%d", len("OK"), n)
					log.Logger.Errorf(err.Error())
					return err
				}
				conn.resetPackage()
				conn.status = Idle
			}
		}
		if err != nil {
			conn.resetPackage()
		}
	}
	return nil
}

func (conn *AgentConnection) resetPackage() {
	conn.netPackage.Header = ""
	conn.netPackage.DBType = ""
	conn.netPackage.BodyLength = 0
	conn.netPackage.Body = []byte{}
	conn.status = Idle
}

// processPackage 将一个完整的包处理并传给gdm
func (conn *AgentConnection) processPackage() error {
	var err error
	cb, ok := dbmodule.DBCallbackMap[types.DBType(conn.netPackage.DBType)]
	if !ok {
		err = fmt.Errorf("can't find %s instance callback", conn.netPackage.DBType)
		log.Logger.Errorf(err.Error())
		return err
	}
	retDB, err := cb.DeserializeCallback(conn.netPackage.Body, conn.Conf)
	if err != nil {
		log.Logger.Errorf("deserialize failed. err:%s", err.Error())
		return err
	}
	conn.GDMChan <- DoubleCheckInstanceInfo{
		AgentIp:      conn.Ip,
		AgentPort:    conn.Port,
		db:           retDB,
		ReceivedTime: time.Now(),
		ConfirmTime:  time.Now(),
	}
	return nil
}
