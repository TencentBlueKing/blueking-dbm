package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/gorilla/websocket"
)

type WSBaseRequest struct {
	RequestType string          `json:"request-type"`
	Body        json.RawMessage `json:"body"`
}

type WSConnectRequest struct {
	Address  string `json:"address"`
	Charset  string `json:"charset"`
	Timezone string `json:"timezone"`
	Timeout  int    `json:"timeout"`
}

type WSCommandRequest struct {
	Command string `json:"command"`
	Timeout int    `json:"timeout"`
}

func main() {
	header := make(http.Header)
	header.Set("token", "123456")
	u := url.URL{
		Scheme: "ws",
		Host:   os.Args[1],
		Path:   "/v2/ws/mysql",
	}
	conn, resp, err := websocket.DefaultDialer.Dial(u.String(), nil)
	if err != nil {
		log.Fatal("dial:", err, resp)
		return
	}
	defer func() {
		_ = conn.Close()
	}()

	interrupt := make(chan os.Signal, 1)
	signal.Notify(interrupt, os.Interrupt, syscall.SIGTERM, syscall.SIGKILL, syscall.SIGINT)

	responseChan := make(chan string, 8)
	defer close(responseChan)

	go func(responseChan chan string) {
		for {
			_, message, err := conn.ReadMessage()
			if err != nil {
				responseChan <- err.Error()
				return
			}
			responseChan <- string(message)
		}
	}(responseChan)

	wcr := WSConnectRequest{
		Address: os.Args[2],
		Charset: "utf8mb4",
		//Timezone: "",
		Timeout: 30,
	}
	b, err := json.Marshal(wcr)
	if err != nil {
		panic(err)
	}

	wbr := WSBaseRequest{
		RequestType: "connect",
		Body:        json.RawMessage(b),
	}
	bb, err := json.Marshal(wbr)
	if err != nil {
		panic(err)
	}

	err = conn.WriteMessage(websocket.TextMessage, bb)
	if err != nil {
		panic(err)
	}
	connResp := <-responseChan
	fmt.Println(connResp)

	for {
		select {
		case <-interrupt:
			log.Println("interrupt")
			err := conn.WriteMessage(
				websocket.CloseMessage,
				websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""),
			)
			if err != nil {
				log.Println("write:", err)
			}
			<-responseChan
			return
		default:
			in := bufio.NewReader(os.Stdin)
			input, err := in.ReadString('\n')
			if err != nil {
				log.Println("read:", err)
				return
			}
			if len(input) == 0 {
				continue
			}
			switch strings.TrimSpace(input) {
			case "exit":
				log.Println("exit")
				err := conn.WriteMessage(
					websocket.CloseMessage,
					websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""),
				)
				if err != nil {
					log.Println("write:", err)
					return
				}
				return
			default:
				wcmr := WSCommandRequest{
					Command: strings.TrimSpace(input),
					Timeout: 30,
				}
				b, err := json.Marshal(wcmr)
				if err != nil {
					panic(err)
				}
				wbr := WSBaseRequest{
					RequestType: "command",
					Body:        json.RawMessage(b),
				}
				bb, err := json.Marshal(wbr)
				if err != nil {
					panic(err)
				}
				err = conn.WriteMessage(websocket.TextMessage, bb)
				if err != nil {
					log.Println("write:", err)
					continue
				}
				resp := <-responseChan
				fmt.Println(resp)
			}
		}
	}
}
