package client

import (
	"dbm-services/common/dbha/ha-module/log"
	"fmt"
	"net"
	"time"
)

// NcClient TODO
type NcClient struct {
	timeout    int
	addr       string
	connection net.Conn
	init       bool
}

// DoConn TODO
func (nc *NcClient) DoConn(addr string, timeout int) error {
	conn, err := net.DialTimeout("tcp", addr, time.Duration(timeout)*time.Second)
	if err != nil {
		log.Logger.Errorf("ncclient dial addr{%s} failed,timeout=%d,err:%s",
			addr, timeout, err.Error())
		return err
	}

	nc.timeout = timeout
	nc.addr = addr
	nc.connection = conn
	nc.init = true
	return nil
}

// WriteText TODO
func (nc *NcClient) WriteText(text string) error {
	if !nc.init {
		ncErr := fmt.Errorf("Connection uninit while Write Text")
		return ncErr
	}

	n, err := nc.connection.Write([]byte(text))
	if err != nil {
		ncErr := fmt.Errorf("connection write failed,err:%s", err.Error())
		return ncErr
	}

	if n != len(text) {
		ncErr := fmt.Errorf("connection write part,sendLen:%d,dataLen:%d",
			n, len(text))
		return ncErr
	}
	return nil
}

// Read 用于常见IO
func (nc *NcClient) Read(buf []byte) (int, error) {
	if !nc.init {
		ncErr := fmt.Errorf("Connection uninit while Read")
		return 0, ncErr
	}

	n, err := nc.connection.Read(buf)
	if err != nil {
		log.Logger.Errorf("Connection read failed,err:%s", err.Error())
		return 0, err
	}
	return n, nil
}

// Close TODO
func (nc *NcClient) Close() error {
	if !nc.init {
		ncErr := fmt.Errorf("Connection uninit while close")
		return ncErr
	}

	err := nc.connection.Close()
	if err != nil {
		log.Logger.Errorf("Connection close err:%s", err.Error())
		return err
	}
	return nil
}
